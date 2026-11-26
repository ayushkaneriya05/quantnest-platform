"""Read-only discovery. Instrument data is shared; workspace records are owner-scoped."""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from instruments.models import Instrument
from strategies.models import Strategy
from trading.models import Watchlist
from backtesting.models import BacktestRun
from .context import selected_instruments

PAGE_SIZE = 25  # Pagination is a transport size, never a total research allowance.


def find_resources(run, arguments):
    kind, query = arguments['kind'], arguments.get('query', '').strip()
    page = arguments.get('page', 1)
    start = (page - 1) * PAGE_SIZE
    if kind == 'instruments':
        rows = Instrument.objects.all()
        if not arguments.get('include_expired', False):
            rows = rows.filter(is_active=True)
        if query:
            rows = rows.filter(Q(sym_ticker__icontains=query) | Q(name__icontains=query) | Q(symbol__icontains=query))
        if arguments.get('exchange'):
            rows = rows.filter(exchange=arguments['exchange'])
        if arguments.get('instrument_type'):
            rows = rows.filter(instrument_type=arguments['instrument_type'])
        exact = rows.filter(Q(sym_ticker__iexact=query) | Q(symbol__iexact=query) | Q(name__iexact=query)) if query else rows.none()
        if exact.exists():
            rows = exact
        identities = list(rows.order_by('sym_ticker').values_list('pk', flat=True)[start:start + PAGE_SIZE + 1])
        items = selected_instruments(identities[:PAGE_SIZE])
    else:
        if kind == 'strategies':
            rows = Strategy.objects.filter(user_id=run.user_id)
            if query:
                rows = rows.filter(Q(name__icontains=query) | Q(description__icontains=query))
            values = rows.order_by('-updated_at', '-pk').values('id', 'name', 'status', 'updated_at')
        elif kind == 'backtests':
            rows = BacktestRun.objects.filter(user_id=run.user_id)
            if query:
                rows = rows.filter(name__icontains=query)
            values = rows.order_by('-pk').values('id', 'name', 'strategy_id', 'status', 'start_date', 'end_date')
        elif kind == 'watchlists':
            rows = Watchlist.objects.filter(user_id=run.user_id, name__icontains=query).annotate(instrument_count=Count('instruments'))
            values = rows.order_by('name', 'pk').values('id', 'name', 'instrument_count')
        else:
            raise ValidationError('Choose instruments, strategies, backtests or watchlists.')
        found = list(values[start:start + PAGE_SIZE + 1])
        items, identities = found[:PAGE_SIZE], found
    return {'data': {'kind': kind, 'query': query, 'items': items, 'page': page,
                     'next_page': page + 1 if len(identities) > PAGE_SIZE else None}}


def market_instruments(run, arguments):
    """Explicit IDs or an owned watchlist; names are resolved by find_resources."""
    if arguments.get('watchlist_id'):
        watchlist = get_object_or_404(Watchlist, pk=arguments['watchlist_id'], user_id=run.user_id)
        ids = list(watchlist.instruments.order_by('pk').values_list('pk', flat=True))
    else:
        ids = arguments.get('instrument_ids', run.request.get('instrument_ids', []))
    if not ids:
        raise ValidationError('Find instruments or choose an owned watchlist before requesting market calculations.')
    selected_instruments(ids)
    return list(dict.fromkeys(ids))
