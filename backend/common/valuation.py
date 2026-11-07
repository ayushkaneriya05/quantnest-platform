"""Full-scope display valuation. Never used by execution's tick path."""
from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from redis.exceptions import RedisError
from common.enums import Side
from marketdata.quotes import read_quotes


def position_totals(queryset, *, include_history=False):
    """One snapshot plus compact inputs for browser valuation across every page.

    Only ledger changes require another snapshot. Quote changes are calculated
    in the browser; they never write positions or refetch paginated tables.
    """
    model = queryset.model._meta.model_name
    terminal = model == 'position'
    account_field = 'allocation_id' if model == 'liveposition' else 'account_id'
    average_field = 'average_price' if terminal else 'avg_price'
    time_field = 'created_at' if terminal else 'last_updated'
    rows = list(queryset.exclude(quantity=0).order_by().values(
        'id', account_field, average_field, time_field, 'instrument__sym_ticker',
        'instrument__qty_multiplier', 'quantity', 'settled_pnl',
        *([] if terminal else ['current_price', 'side'])))
    try:
        quotes = read_quotes([row['instrument__sym_ticker'] for row in rows], include_history=include_history) if rows else {}
    except (RedisError, OSError):
        quotes = {}  # Keep persisted display marks while the quote cache recovers.
    totals = {'count': 0, 'unrealized_pnl': Decimal(0), 'current_value': Decimal(0), 'invested': Decimal(0), 'profitable': 0, 'losing': 0}
    accounts, inputs, quote_times = {}, [], []
    missing = 0
    for row in rows:
        symbol = row['instrument__sym_ticker']
        quote = quotes.get(symbol, {})
        observed = parse_datetime(quote.get('timestamp') or '')
        # Match the visible-row contract: an older quote must not replace a
        # newer persisted mark. This is ordering, not an elapsed-age limit.
        use_quote = bool(quote.get('available') and observed is not None and observed >= row[time_field])
        average = row[average_field]
        price = Decimal(str(quote['price'])) if use_quote else row.get('current_price') or average
        quantity = abs(row['quantity'])
        side = (Side.SELL if row['quantity'] < 0 else Side.BUY) if terminal else row['side']
        units = quantity * row['instrument__qty_multiplier']
        pnl = (price - average) * units * (-1 if side == Side.SELL else 1) - row['settled_pnl']
        values = {'count': 1, 'unrealized_pnl': pnl, 'current_value': price * units,
                  'invested': average * units, 'profitable': int(pnl > 0), 'losing': int(pnl < 0)}
        key = str(row[account_field])
        group = accounts.setdefault(key, {field: 0 for field in totals})
        for field, value in values.items():
            totals[field] += value
            group[field] += value
        if use_quote:
            quote_times.append(observed)
        else:
            missing += 1
        inputs.append({
            'id': row['id'], 'account_id': row[account_field], 'instrument_symbol': symbol,
            'quantity': quantity, 'qty_multiplier': row['instrument__qty_multiplier'],
            'side': side, 'avg_price': average, 'current_price': price,
            'settled_pnl': row['settled_pnl'], 'mark_at': observed if use_quote else row[time_field],
            'is_priced': use_quote,
        })
    return {**totals, 'by_account': accounts, 'valuation_positions': inputs,
            'unpriced_positions': missing, 'oldest_quote_at': min(quote_times) if quote_times else None,
            'as_of': timezone.now()}
