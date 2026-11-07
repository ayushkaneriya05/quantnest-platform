"""Historical contract discovery, outside live execution and numerical replay.

FYERS owns the historical symbols/prices. Where it omits economic terms, replay
may use a current contract from the same underlying/family, explicitly recorded
as an assumption. History-only identities never become live trading candidates.
"""
from bisect import bisect_right
from datetime import timedelta
from hashlib import sha256

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from common.enums import ExpirySelection, FyersSegment, InstrumentType
from marketdata.providers import provider
from .models import Instrument
from .selection import Candidate, PreparedSelector


def _discovery(adapter, operation, *arguments):
    """Share immutable expired listings across previews, users and worker runs."""
    digest = sha256(repr((adapter.name, operation, arguments)).encode()).hexdigest()
    key = f'instruments:historical:{digest}'
    result = cache.get(key)
    if result is None:
        result = getattr(adapter, operation)(*arguments)
        cache.set(key, result, 86400 * 7)
    return result


def historical_selector(underlying, policy, start, end):
    """Load every relevant expiry, including the next one/two beyond range end.

    Relative strikes use the complete provider grid. No fixed-strike fallback,
    calendar-based invented expiry, or today's nearest expiry is substituted.
    Listing times are unavailable: this is a retrospective per-expiry universe.
    """
    adapter = provider()
    if not underlying.fy_token or underlying.fy_token == '0':
        raise ValueError(f'{underlying.name}: sync the underlying provider identity before historical selection.')
    # Underlyings usually live in CM while their contracts live in FO. The
    # linked token plus exchange/family identifies contracts without name guesses.
    family = Instrument.objects.filter(exchange=underlying.exchange, segment=FyersSegment.EQUITY_DERIVATIVES,
        underlying_fy_token=underlying.fy_token, instrument_type=policy.instrument_type)
    if policy.instrument_type == InstrumentType.OPTION:
        family = family.filter(option_type=policy.option_type)
    template = family.filter(is_active=True, is_tradeable=True).order_by('expiry_date', 'pk').first()
    if template is None:
        template = family.filter(fy_token__isnull=False).order_by('-last_sync_date', '-pk').first()
    if template is None:
        raise ValueError(f'{underlying.name}: sync the current contract family before preparing historical terms.')
    today = timezone.localdate()
    first, last = start.date(), min(end.date() + timedelta(days=366), today - timedelta(days=1))
    expiries = {value for value in family.filter(expiry_date__gte=first).values_list('expiry_date', flat=True) if value}
    cursor = first
    while cursor <= last:
        right = min(cursor + timedelta(days=365), last)
        listing = _discovery(adapter, 'expiry_dates', underlying.sym_ticker, cursor, right)
        expiries.update(listing['expiries'][policy.instrument_type])
        cursor = right + timedelta(days=1)
    dates = sorted(expiries)
    if policy.expiry == ExpirySelection.FIXED:
        dates = [day for day in dates if day == policy.expiry_date]
    else:
        # Excluding expiry day can require the following expiry on the last day;
        # NEXT needs one more. Dates come from discovery, never weekday rules.
        tail = 2 if policy.expiry == ExpirySelection.NEXT else 1
        dates = dates[:bisect_right(dates, end.date()) + tail]
    if not dates:
        raise ValueError(f'{underlying.name}: FYERS returned no expiries covering this backtest.')
    discovered = []
    for expiry in dates:
        if expiry >= today:
            continue  # Still-listed contracts use their current master and regular history API.
        listing = _discovery(adapter, 'expired_contracts', underlying.sym_ticker, expiry)
        discovered.extend(row for row in adapter.expired_contract_terms(listing)
            if row['instrument_type'] == policy.instrument_type and
            (policy.instrument_type != InstrumentType.OPTION or row['option_type'] == policy.option_type))
    # Only identities missing from the master are inserted. An archived ticker
    # has no known FYERS/exchange token; NULL is honest and is safe for uniqueness.
    existing = {item.sym_ticker: item for item in Instrument.objects.filter(
        sym_ticker__in=[row['sym_ticker'] for row in discovered])}
    additions = []
    for row in discovered:
        previous = existing.get(row['sym_ticker'])
        if previous is not None:
            if any(getattr(previous, name) != row[name] for name in
                   ('instrument_type', 'option_type', 'expiry_date', 'strike_price')):
                raise ValueError(f'{row["sym_ticker"]}: provider identity conflicts with the archived catalog.')
            continue
        additions.append(Instrument(**row, fy_token=None, exchange=template.exchange,
            segment=template.segment, ex_inst_type=template.ex_inst_type,
            symbol=template.underlying_symbol or underlying.symbol, name=row['sym_ticker'].split(':', 1)[1],
            underlying_fy_token=underlying.fy_token, underlying_symbol=template.underlying_symbol,
            lot_size=template.lot_size, tick_size=template.tick_size,
            qty_multiplier=template.qty_multiplier, qty_freeze=template.qty_freeze,
            currency_code=template.currency_code, is_active=False, is_tradeable=False,
            description=f'History-only FYERS discovery; assumed economic terms from {template.sym_ticker}'))
    if additions:
        with transaction.atomic():
            Instrument.objects.bulk_create(additions, ignore_conflicts=True, batch_size=1000)
    rows = {item.pk: item for item in family.filter(expiry_date__in=dates)}
    selector = PreparedSelector(policy, tuple(Candidate(item.pk, item.expiry_date, item.strike_price)
        for item in rows.values()))
    if not selector.expiries:
        raise ValueError(f'{underlying.name}: no discovered contracts match this selection policy.')
    return selector, rows, template
