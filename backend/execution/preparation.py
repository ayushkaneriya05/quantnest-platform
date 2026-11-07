"""Convert persisted configuration and market history into kernel inputs.

These functions run during admission, warmup or history repair. They are never
called by numerical evaluation, matching or financial transition functions.
"""
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING

from common.enums import ExchangeInstrumentType
from marketdata.calendar import MarketSessionCalendar

from .types import Candle, Contract
from .settlements import SettlementPrice

if TYPE_CHECKING:
    from instruments.models import Instrument


def contract_from_instrument(instrument: 'Instrument') -> Contract:
    return Contract(instrument.pk, instrument.sym_ticker, instrument.name,
        instrument.instrument_type, instrument.exchange, instrument.segment,
        Decimal(str(instrument.tick_size)), instrument.lot_size, Decimal(str(instrument.qty_multiplier)),
        instrument.expiry_date, instrument.qty_freeze or 0,
        Decimal(str(instrument.circuit_limit_lower)) if instrument.circuit_limit_lower is not None else None,
        Decimal(str(instrument.circuit_limit_upper)) if instrument.circuit_limit_upper is not None else None,
        instrument.is_active and instrument.is_tradeable
        and instrument.ex_inst_type != ExchangeInstrumentType.UNDCUR,
        Decimal(str(instrument.strike_price)) if instrument.strike_price is not None else None,
        option_type=instrument.option_type)


def historical_contract(instrument: 'Instrument', start, end) -> Contract:
    """Prepare dated terms; today's activity flags/bands are not historical facts."""
    from instruments.services import InstrumentResolver
    from instruments.specifications import historical_specification
    InstrumentResolver.validate_execution_instrument(instrument, historical=True)
    spec = historical_specification(instrument, start, end)
    if spec is None:
        return replace(contract_from_instrument(instrument), tradeable=True, lower_band=None, upper_band=None)
    # Construct from dated economics directly. An archived current master may
    # contain zero/changed lot sizes and must not invalidate known past terms.
    return Contract(instrument.pk, instrument.sym_ticker, instrument.name,
        instrument.instrument_type, instrument.exchange, instrument.segment,
        spec.tick_size, spec.lot_size, spec.qty_multiplier, spec.expiry_date,
        spec.qty_freeze, strike_price=spec.strike_price, specification_id=spec.pk,
        option_type=instrument.option_type)


def candles_from_frame(frame, timeframe: str, calendar: MarketSessionCalendar) -> list[Candle]:
    """A data frame is indexed by candle OPEN; completion is exchange-calendar time."""
    return [Candle(row.Index.to_pydatetime(), calendar.candle_close(row.Index, timeframe),
                   row.open, row.high, row.low, row.close, row.volume)
            for row in frame.itertuples()]


@dataclass(frozen=True, slots=True)
class PreparedMarket:
    """A price source may be an index with no tradable financial terms."""
    instrument_id: int
    symbol: str
    calendar: MarketSessionCalendar
    candles: dict[str, list[Candle]]
    contract: Contract | None = None
    settlements: tuple[SettlementPrice, ...] = ()


@dataclass(frozen=True, slots=True)
class CompiledMarkets:
    instruments: dict
    calendars: dict
    programs: dict
    bindings: dict
    inputs: dict

    @property
    def trade_ids(self):
        return {identity for program in self.programs.values()
                for identity in (program.candidates if program.selection is not None else (program.binding[1],))}


def compile_markets(config: dict, version: int, *, as_of=None, retained=None, selections=None) -> CompiledMarkets:
    """Resolve fixed bindings or candidate catalogs and compile projections once.

    History, runtime demand and replay use this same binding map. A signal-only
    index gets a data graph, never an order book or a financial position.
    """
    from instruments.models import Instrument
    from instruments.services import InstrumentResolver
    from .compiler import compile_strategy
    watches = config['watchlist_instruments']
    bindings = {(watch['route_id'], watch['leg_id']): InstrumentResolver.input_bindings(watch) for watch in watches}
    ids = {identity for binding in bindings.values() for identity in binding.values()}
    instruments = Instrument.objects.in_bulk(ids)
    if not ids or set(instruments) != ids:
        raise ValueError('The strategy must reference existing signal and traded instruments.')
    prepared_selections = {}
    for watch in watches:
        if 'contract_selection' not in watch:
            continue
        from instruments.selection import SelectionPolicy, prepare_current_selector
        route = watch['route_id'], watch['leg_id']
        owned = (retained or {}).get(route, ())
        if selections is not None:
            selector, candidates = selections[route]
            candidates = dict(candidates)
        else:
            if as_of is not None:
                raise ValueError('Historical automatic routes require a prepared backtest catalog.')
            selector, candidates = prepare_current_selector(instruments[watch['instrument_id']],
                SelectionPolicy.parse(watch['contract_selection']), allow_empty=bool(owned))
        # This is a preparation bound, never a strike fallback. Reject oversize
        # universes explicitly instead of quietly changing the selected strike.
        if as_of is None and len(candidates) > 512:
            raise ValueError('This route exceeds 512 candidate contracts. Choose a specific expiry to reduce its universe.')
        # Retained exposure is not a fresh-entry candidate. It remains prepared
        # for exits/reconciliation even after expiry or removal from the master.
        candidates.update(Instrument.objects.in_bulk(owned))
        if not candidates:
            raise ValueError('No contracts are available for this route.')
        prepared_selections[route] = selector, candidates
        instruments.update(candidates)
        bindings[route]['trade'] = next(iter(candidates))
    calendars = {identity: MarketSessionCalendar.for_instrument(item) for identity, item in instruments.items()}
    programs, inputs = {}, {identity: [] for identity in instruments}
    for watch in watches:
        route = watch['route_id'], watch['leg_id']
        binding = bindings[route]
        identity = binding['trade']
        program = compile_strategy(config, version, calendar=calendars[identity], signal_calendar=calendars[binding['signal']])
        if as_of is None:
            program = program.for_live()
        program = replace(program, binding=(binding['signal'], identity))
        if route in prepared_selections:
            selector, candidates = prepared_selections[route]
            program = replace(program, selection=selector,
                candidates={key: item.sym_ticker for key, item in candidates.items()})
        programs[route] = program
        if program.selection is not None:
            inputs[binding['signal']].append(program.for_source('signal'))
            for source in program.candidates:
                inputs[source].append(program.for_source('trade'))
        elif binding['signal'] == identity:
            inputs[identity].append(program)
        else:
            for role, source in binding.items():
                inputs[source].append(program.for_source(role))
    return CompiledMarkets(instruments, calendars, programs, bindings, inputs)
