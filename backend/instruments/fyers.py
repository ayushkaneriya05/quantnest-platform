"""FYERS public Symbol Master JSON contract and instrument mapping."""
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import requests

from common.enums import Exchange, FyersSegment, ExchangeInstrumentType, InstrumentType, Timezone


class FyersInstrumentMaster:
    SOURCES = {
        "NSE_CM": "https://public.fyers.in/sym_details/NSE_CM_sym_master.json",
        "NSE_FO": "https://public.fyers.in/sym_details/NSE_FO_sym_master.json",
        "NSE_CD": "https://public.fyers.in/sym_details/NSE_CD_sym_master.json",
        "NSE_COM": "https://public.fyers.in/sym_details/NSE_COM_sym_master.json",
        "BSE_CM": "https://public.fyers.in/sym_details/BSE_CM_sym_master.json",
        "BSE_FO": "https://public.fyers.in/sym_details/BSE_FO_sym_master.json",
        "MCX_COM": "https://public.fyers.in/sym_details/MCX_COM_sym_master.json",
    }
    
    SOURCE_FILTERS = {
        "NSE_CM": {"exchange": Exchange.NSE, "segment": FyersSegment.CAPITAL_MARKET},
        "NSE_FO": {"exchange": Exchange.NSE, "segment": FyersSegment.EQUITY_DERIVATIVES},
        "NSE_CD": {"exchange": Exchange.NSE, "segment": FyersSegment.CURRENCY_DERIVATIVES},
        "NSE_COM": {"exchange": Exchange.NSE, "segment": FyersSegment.COMMODITY_DERIVATIVES},
        "BSE_CM": {"exchange": Exchange.BSE, "segment": FyersSegment.CAPITAL_MARKET},
        "BSE_FO": {"exchange": Exchange.BSE, "segment": FyersSegment.EQUITY_DERIVATIVES},
        "MCX_COM": {"exchange": Exchange.MCX, "segment": FyersSegment.COMMODITY_DERIVATIVES},
    }
    
    EXCHANGE_MAP = {10: Exchange.NSE, 11: Exchange.MCX, 12: Exchange.BSE}
    
    INST_TYPE_MAP = {
        ExchangeInstrumentType.EQ: InstrumentType.STOCK,
        ExchangeInstrumentType.PREFSHARES: InstrumentType.STOCK,
        ExchangeInstrumentType.DEBENTURES: InstrumentType.BOND,
        ExchangeInstrumentType.WARRANTS: InstrumentType.STOCK,
        ExchangeInstrumentType.MISC_NSE: InstrumentType.STOCK,
        ExchangeInstrumentType.SGB: InstrumentType.BOND,
        ExchangeInstrumentType.G_SECS: InstrumentType.BOND,
        ExchangeInstrumentType.T_BILLS: InstrumentType.BOND,
        ExchangeInstrumentType.MF: InstrumentType.MF,
        ExchangeInstrumentType.ETF: InstrumentType.ETF,
        ExchangeInstrumentType.INDEX: InstrumentType.INDEX,
        ExchangeInstrumentType.MISC_BSE: InstrumentType.STOCK,
        ExchangeInstrumentType.FUTIDX: InstrumentType.FUTURE,
        ExchangeInstrumentType.FUTIVX: InstrumentType.FUTURE,
        ExchangeInstrumentType.FUTSTK: InstrumentType.FUTURE,
        ExchangeInstrumentType.OPTIDX: InstrumentType.OPTION,
        ExchangeInstrumentType.OPTSTK: InstrumentType.OPTION,       
        ExchangeInstrumentType.FUTCUR: InstrumentType.FUTURE,
        ExchangeInstrumentType.FUTIRT: InstrumentType.FUTURE,
        ExchangeInstrumentType.FUTIRC: InstrumentType.FUTURE,
        ExchangeInstrumentType.OPTCUR: InstrumentType.OPTION,
        ExchangeInstrumentType.UNDCUR: InstrumentType.CURRENCY,
        ExchangeInstrumentType.UNDIRC: InstrumentType.CURRENCY,
        ExchangeInstrumentType.UNDIRT: InstrumentType.CURRENCY,
        ExchangeInstrumentType.UNDIRD: InstrumentType.CURRENCY,
        ExchangeInstrumentType.INDEX_CD: InstrumentType.INDEX,
        ExchangeInstrumentType.FUTIRD: InstrumentType.FUTURE,
        ExchangeInstrumentType.FUTCOM: InstrumentType.FUTURE,
        ExchangeInstrumentType.OPTFUT: InstrumentType.OPTION,
        ExchangeInstrumentType.OPTCOM: InstrumentType.OPTION,
        ExchangeInstrumentType.FUTBAS: InstrumentType.FUTURE,
        ExchangeInstrumentType.FUTBLN: InstrumentType.FUTURE,
        ExchangeInstrumentType.FUTENR: InstrumentType.FUTURE,
        ExchangeInstrumentType.OPTBLN: InstrumentType.OPTION,
        ExchangeInstrumentType.OPTFUT_NCOM: InstrumentType.OPTION,
    }

    @classmethod
    def download(cls, source: str) -> dict:
        response = requests.get(cls.SOURCES[source], timeout=60)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _decimal(value):
        return None if value is None or value == "" else Decimal(str(value))

    @staticmethod
    def _expiry(value: str):
        value = value.strip()
        return datetime.fromtimestamp(int(value), ZoneInfo(Timezone.ASIA_KOLKATA)).date() if value else None

    @classmethod
    def map_entry(cls, sym_ticker: str, row: dict) -> dict:
        strike = row["strikePrice"]
        qty_freeze = row["qtyFreeze"].strip()
        # The public master uses the literal string "None" for unknown update dates.
        last_update = row["lastUpdate"].strip()
        return {
            "fy_token": row["fyToken"], "exchange_token": row["exToken"],
            "symbol": row["exSymbol"], "name": row["exSymName"][:255], "sym_ticker": sym_ticker,
            # Presentation fields are present in the current public JSON file.
            "short_name": row.get("short_name", "")[:50],
            "display_name": row.get("display_format_mob", "")[:100],
            "description": row["symbolDesc"][:255], "isin": row.get("isin", "")[:20],
            "exchange": cls.EXCHANGE_MAP[row["exchange"]], "segment": row["segment"],
            "series": row["exSeries"][:10], "ex_inst_type": row["exInstType"],
            "instrument_type": cls.INST_TYPE_MAP[row["exInstType"]], "option_type": row["optType"],
            "currency_code": row["currencyCode"], "strike_price": cls._decimal(strike) if strike >= 0 else None,
            "expiry_date": cls._expiry(row["expiryDate"]), "underlying_symbol": row["underSym"][:50],
            "underlying_fy_token": row["underFyTok"], "lot_size": row["minLotSize"],
            "tick_size": cls._decimal(row["tickSize"]),
            "qty_freeze": int(qty_freeze) if qty_freeze else None,
            "qty_multiplier": cls._decimal(row["qtyMultiplier"]), "face_value": cls._decimal(row["faceValue"]),
            "circuit_limit_upper": cls._decimal(row["upperPrice"]),
            "circuit_limit_lower": cls._decimal(row["lowerPrice"]),
            "trading_session": row["tradingSession"][:100],
            "previous_close": cls._decimal(row["previousClose"]), "previous_oi": cls._decimal(row["previousOi"]),
            "is_mtf_tradable": row.get("is_mtf_tradable", 0) == 1,
            "mtf_margin": cls._decimal(row.get("mtf_margin")), "asm_gsm_flag": row["asmGsmVal"][:100],
            "has_options": row.get("has_options", False), "has_futures": row.get("has_futures", False),
            "stream": row["stream"][:20], "is_tradeable": row["tradeStatus"] == 1, "is_active": True,
            "last_sync_date": datetime.strptime(last_update, "%Y-%m-%d").date()
                              if last_update not in {"", "None"} else None,
        }
