"""Freeze a replay's catalog, assumed economics and bounded history windows.

This is the cold preparation boundary. Provider calls and ORM queries finish
before Replay starts; the numerical clock only reads prepared in-memory values.
"""
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from threading import Event

from common.enums import InstrumentType, QuantityType, QuantityUnit
from execution.compiler import source_windows
from execution.preparation import compile_markets, contract_from_instrument, historical_contract
from execution.snapshots import encode, decode
from instruments.models import Instrument
from instruments.selection import Candidate, PreparedSelector, SelectionPolicy
from instruments.services import InstrumentResolver
from marketdata.calendar import MarketSessionCalendar
from marketdata.candles import prepare_frames
from marketdata.contracts import source_timeframe


def acquire_plan(compiled, plan, *, report, check_cancelled):
    """Overlap four independent history reads; leave replay single-clock and pure.

    A bounded batch avoids thousands of queued jobs/connections. Progress and
    cancellation stay on the owning task thread, never in concurrent callbacks.
    Every HTTP call still passes the shared provider request budget.
    """
    from django.db import close_old_connections
    from marketdata.history import ensure_history
    from marketdata.contracts import HistoryRequest
    stopped = Event()

    def fetch(row):
        try:
            instrument = compiled.instruments[row['instrument_id']]
            calendar = compiled.calendars[instrument.pk]
            for source, bounds in row['windows'].items():
                if stopped.is_set():
                    return
                request = HistoryRequest(instrument, source,
                    *(datetime.fromisoformat(value) for value in bounds), calendar)
                result = ensure_history(request)
                if result.error and not result.retryable:
                    raise ValueError(f'{instrument.sym_ticker}: {result.error}')
        finally:
            close_old_connections()

    done, rows = 0, plan['rows']
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix='backtest-history') as pool:
        try:
            for offset in range(0, len(rows), 4):
                pending = {pool.submit(fetch, row): row for row in rows[offset:offset+4]}
                while pending:
                    check_cancelled()
                    ready, _ = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                    for future in ready:
                        row = pending.pop(future)
                        future.result()
                        done += 1
                        symbol = compiled.instruments[row['instrument_id']].sym_ticker
                        report(1 + int(14 * done / len(rows)), f'Checked history {done}/{len(rows)}: {symbol}')
        finally:
            stopped.set()


def prepare_history(instrument, timeframes, windows, calendar, *, on_progress=None):
    """Retry one transient read failure; confirmed ranges are reused on retry.

    Backtests have no running feed loop to retry later. Authorization, invalid
    symbols and successful empty data never trigger another provider request.
    """
    result = prepare_frames(instrument, timeframes, windows, calendar, on_progress=on_progress)
    if any(row.get('retryable') for row in result[1]['timeframes'].values()):
        result = prepare_frames(instrument, timeframes, windows, calendar, on_progress=on_progress)
    return result


def _contract(instrument, start, end, template):
    """Prefer dated terms; otherwise freeze the authorized current-term assumption."""
    if instrument.instrument_type not in (InstrumentType.FUTURE, InstrumentType.OPTION):
        return replace(contract_from_instrument(instrument), tradeable=True, lower_band=None, upper_band=None), None
    spec = instrument.specifications.filter(effective_at__lte=start).order_by('-effective_at').first()
    changed = instrument.specifications.filter(effective_at__gt=start, effective_at__lte=end).exists()
    if spec is not None and not changed:
        return historical_contract(instrument, start, end), None
    source = template or instrument
    if instrument.expiry_date is None or (instrument.instrument_type == InstrumentType.OPTION and
            (instrument.strike_price is None or instrument.strike_price <= 0)):
        raise ValueError(f'{instrument.name}: the historical contract needs its actual expiry and option strike.')
    contract = replace(contract_from_instrument(source), instrument_id=instrument.pk,
        symbol=instrument.sym_ticker, name=instrument.name, expiry=instrument.expiry_date,
        strike_price=instrument.strike_price, option_type=instrument.option_type,
        tradeable=True, lower_band=None, upper_band=None)
    return contract, source.sym_ticker


def build_plan(config, start, end, *, maximum=None, on_progress=None):
    """Discover expiries, select against historical OHLC, then price only used markets.

    The complete strike grid decides ATM/ITM/OTM. The OHLC prepass determines
    which exact contracts can occur in this candle replay; it does not evaluate
    entry rules or look ahead inside the execution engine.
    """
    InstrumentResolver.validate_execution_snapshot(config, historical=True)
    base = config['time_rule']['candle_timeframe']
    selections, templates, first_selected, reference_frames = {}, {}, {}, {}
    serialized, selection_notes = [], []
    ids = {row['instrument_id'] for row in config['watchlist_instruments']}
    originals = Instrument.objects.in_bulk(ids)
    for watch in config['watchlist_instruments']:
        if 'contract_selection' not in watch:
            continue
        from instruments.history import historical_selector
        underlying = originals[watch['instrument_id']]
        calendar = MarketSessionCalendar.for_instrument(underlying)
        calendar.load_holidays(start.astimezone(calendar.zone).date(), end.astimezone(calendar.zone).date())
        if maximum is not None and calendar.source_count(source_timeframe(base), start, end) > maximum:
            raise ValueError('The underlying history alone exceeds this plan’s backtest candle allowance. Choose a shorter range.')
        policy = SelectionPolicy.parse(watch['contract_selection'])
        if on_progress:
            on_progress(0, f'Discovering historical contracts for {underlying.sym_ticker}...')
        selector, universe, template = historical_selector(underlying, policy,
            start.astimezone(calendar.zone), end.astimezone(calendar.zone))
        if underlying.pk not in reference_frames:
            frames, quality = prepare_history(underlying, frozenset({base}),
                {source_timeframe(base): (start, end)}, calendar, on_progress=on_progress)
            if not quality['complete'] or frames[base].empty:
                raise ValueError(f'{underlying.sym_ticker}: confirmed underlying history is required for contract selection.')
            reference_frames[underlying.pk] = frames[base]
        used, seen, previous_close, unavailable_days = {}, set(), None, set()
        for bar in reference_frames[underlying.pk].itertuples():
            opening = bar.Index.to_pydatetime()
            closing = calendar.candle_close(opening, base)
            span = closing - opening
            # Include both extremes regardless of entry side. Actual replay can
            # visit them in either declared OHLC ordering, using no future quote.
            values = (bar.open, bar.low, bar.high, bar.close) + ((previous_close,) if previous_close is not None else ())
            for index in range(4):
                at = opening + span * (index / 3)
                day = at.astimezone(calendar.zone).date()
                for value in values:
                    key = day, Decimal(str(value))
                    if key in seen:
                        continue
                    seen.add(key)
                    try:
                        selected = selector.select(key[1], day)
                    except ValueError:
                        unavailable_days.add(day)
                        continue  # An exact strike/expiry can legitimately be unavailable on some dates.
                    used[selected.instrument_id] = min(used.get(selected.instrument_id, at), at)
            previous_close = bar.close
        if not used:
            raise ValueError(f'{underlying.name}: the configured expiry/strike policy selects no contracts in this range.')
        if unavailable_days:
            selection_notes.append(f'{underlying.sym_ticker}: this exact selection policy has no eligible contract on {len(unavailable_days)} replay date(s); entries wait rather than substitute a different expiry/strike.')
        route = watch['route_id'], watch['leg_id']
        selections[route] = selector, {key: universe[key] for key in used}
        for key, at in used.items():
            templates[key] = template
            first_selected[key] = min(first_selected.get(key, at), at)
        serialized.append({'route_id': route[0], 'leg_id': route[1], 'policy': watch['contract_selection'],
            'grid': [[row.instrument_id, row.expiry.isoformat(), str(row.strike) if row.strike is not None else None]
                     for group in selector.contracts.values() for row in group.values()], 'candidates': sorted(used)})
    compiled = compile_markets(config, 0, as_of=start, selections=selections)
    rows, warnings, total, assumptions = [], selection_notes, 0, {}
    trade_ids = compiled.trade_ids
    for instrument in compiled.instruments.values():
        calendar = compiled.calendars[instrument.pk]
        financial = instrument.pk in trade_ids
        contract, assumed_from = _contract(instrument, start, end, templates.get(instrument.pk)) if financial else (None, None)
        if contract and contract.expiry and contract.expiry < start.astimezone(calendar.zone).date():
            raise ValueError(f'{instrument.name}: the requested range starts after contract expiry.')
        if assumed_from:
            terms = assumed_from, contract.lot_size, str(contract.tick_size), str(contract.multiplier), contract.quantity_freeze
            assumptions[terms] = assumptions.get(terms, 0) + 1
        for watch in config['watchlist_instruments']:
            if contract is None or watch['instrument_id'] != instrument.pk or 'contract_selection' in watch:
                continue
            sizing = InstrumentResolver.sizing_for(watch, config['position_sizing_rule'])
            if (sizing['sizing_method'] == QuantityType.FIXED and sizing.get('quantity_unit') == QuantityUnit.UNITS
                    and int(sizing['fixed_quantity']) % contract.lot_size):
                raise ValueError(f'{instrument.name}: fixed units must be a multiple of lot size {contract.lot_size}.')
        counts, depths = {}, {}
        for projection in compiled.inputs[instrument.pk]:
            for target, source in ((counts, projection.counts), (depths, projection.sources)):
                for tf, count in source.items():
                    target[tf] = max(target.get(tf, 0), count)
        active = first_selected.get(instrument.pk, start)
        # Start candidate preparation at a session opening, retaining the full
        # warmup before its first possible selection and prices through expiry.
        if instrument.pk in first_selected:
            active = max(start, calendar.session_open(active.astimezone(calendar.zone).date()))
        stop = min(end, calendar.session_close(contract.expiry)) if contract and contract.expiry else end
        windows = source_windows(frozenset(counts), depths, calendar, active, stop)
        warmup = min(left for left, _ in windows.values())
        calendar.load_holidays(warmup.astimezone(calendar.zone).date(), stop.astimezone(calendar.zone).date())
        count = sum(calendar.source_count(tf, left, right) for tf, (left, right) in windows.items())
        total += count
        rows.append({'instrument_id': instrument.pk, 'source_candles': count,
            'warmup_start': warmup.isoformat(), 'active_from': active.isoformat(), 'counts': counts,
            'windows': {tf: [left.isoformat(), right.isoformat()] for tf, (left, right) in windows.items()},
            'contract': encode(contract), 'assumed_from': assumed_from,
            'contract_specification_id': contract.specification_id if contract else None})
    if serialized:
        warnings.insert(0, 'Automatic selection uses retrospective provider strike grids for each expiry; historical listing timestamps are unavailable.')
    for (source, lot, tick, multiplier, freeze), count in assumptions.items():
        warnings.append(f'{count} derivative contract(s) use current/last-observed details from {source}: lot {lot}, tick {tick}, multiplier {multiplier}, freeze quantity {freeze or "unspecified"}. Prices, expiry and strike remain specific to each historical contract.')
    return {'schema_version': 1, 'rows': rows, 'selections': serialized,
        'instrument_candles': total, 'warnings': warnings,
        'selection_policy': 'Retrospective FYERS expiry grids; select using each historical underlying observation. Listing timestamps are not available.'}


def restore_plan(config, version, plan, start):
    """Use the reviewed immutable grids/economics, without rediscovery or repricing."""
    ids = {row['instrument_id'] for row in plan['rows']}
    instruments = Instrument.objects.in_bulk(ids)
    if set(instruments) != ids:
        raise ValueError('A reviewed historical instrument was removed. Prepare a new backtest.')
    selections = {}
    for item in plan['selections']:
        selector = PreparedSelector(SelectionPolicy.parse(item['policy']), tuple(
            Candidate(key, date.fromisoformat(expiry), Decimal(strike) if strike is not None else None)
            for key, expiry, strike in item['grid']))
        selections[item['route_id'], item['leg_id']] = selector, {key: instruments[key] for key in item['candidates']}
    compiled = compile_markets(config, version, as_of=start, selections=selections)
    contracts = {row['instrument_id']: decode(row['contract']) for row in plan['rows'] if row['contract'] is not None}
    return compiled, contracts
