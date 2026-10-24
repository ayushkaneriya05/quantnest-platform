"""Convert persisted configuration and market history into kernel inputs.

These functions run during admission, warmup or history repair. They are never
called by numerical evaluation, matching or financial transition functions.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from common.enums import ExchangeInstrumentType
from marketdata.calendar import MarketSessionCalendar

from .types import Candle, Contract

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
        Decimal(str(instrument.strike_price)) if instrument.strike_price is not None else None)


def candles_from_frame(frame, timeframe: str, calendar: MarketSessionCalendar) -> list[Candle]:
    """A data frame is indexed by candle OPEN; completion is exchange-calendar time."""
    return [Candle(row.Index.to_pydatetime(), calendar.candle_close(row.Index, timeframe),
                   row.open, row.high, row.low, row.close, row.volume)
            for row in frame.itertuples()]


@dataclass(frozen=True, slots=True)
class PreparedMarket:
    contract: Contract
    calendar: MarketSessionCalendar
    candles: dict[str, list[Candle]]
