import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from datetime import timezone as py_timezone
from decimal import Decimal
from math import ceil

import pandas as pd
import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from instruments.models import Instrument

from .models import Candle
from .utils import get_active_fyers_access_token, ist

logger = logging.getLogger(__name__)


class MarketStatusService:
    """
    Service to check if the market is currently open using Fyers API.
    """
    CACHE_KEY = "market_status:nse_equity"
    CACHE_TIMEOUT = 120  # 2 minutes

    @classmethod
    def is_market_open(cls):
        # 1. Check Cache
        cached_status = cache.get(cls.CACHE_KEY)
        if cached_status is not None:
            return cached_status

        # 2. Local Time Fallback (Basic Check)
        now_ist = datetime.now(ist)
        # NSE Hours: Mon-Fri, 09:15 - 15:30
        is_weekday = now_ist.weekday() < 5
        market_start = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # If outside basic hours, we can skip the API call for optimization
        if not is_weekday or now_ist < market_start or now_ist > market_end:
            cache.set(cls.CACHE_KEY, False, timeout=cls.CACHE_TIMEOUT)
            return False

        # 3. Call Fyers API for real-time status (Holidays/Special session check)
        try:
            from fyers_apiv3 import fyersModel
            access_token = get_active_fyers_access_token()
            if not access_token:
                # If no token, rely on local time. We've already verified
                # above that the local time is within market hours.
                cache.set(cls.CACHE_KEY, True, timeout=cls.CACHE_TIMEOUT)
                return True

            fyers = fyersModel.FyersModel(client_id=settings.FYERS_CLIENT_ID, token=access_token)
            response = fyers.market_status()

            if response.get("s") == "ok" and "marketStatus" in response:
                # Find NSE Equity
                # Response structure is usually a list of dicts in marketStatus
                for item in response["marketStatus"]:
                    if item.get("exchange") == "NSE" and item.get("segment") == "EQUITY":
                        is_open = item.get("status") == "OPEN"
                        cache.set(cls.CACHE_KEY, is_open, timeout=cls.CACHE_TIMEOUT)
                        return is_open
        except Exception as e:
            logger.warning(f"Failed to fetch market status from Fyers: {e}")

        # Fallback to True if we are within hours but API fails
        cache.set(cls.CACHE_KEY, True, timeout=cls.CACHE_TIMEOUT)
        return True


TIMEFRAME_CONFIG = {
    "1m": {"unit": "minute", "bin_size": 1},
    "3m": {"unit": "minute", "bin_size": 3},
    "5m": {"unit": "minute", "bin_size": 5},
    "15m": {"unit": "minute", "bin_size": 15},
    "30m": {"unit": "minute", "bin_size": 30},
    "1H": {"unit": "hour", "bin_size": 1},
    "4H": {"unit": "hour", "bin_size": 4},
    "1D": {"unit": "day", "bin_size": 1},
    "1W": {"unit": "week", "bin_size": 1},
}



@dataclass
class CandleState:
    symbol: str
    timeframe: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


class CandleRepository:
    @staticmethod
    def get_instrument(symbol):
        normalized = MarketDataService.normalize_symbol(symbol)
        return Instrument.objects.filter(sym_ticker=normalized).first()

    @classmethod
    def upsert_candles(cls, symbol, timeframe, candles):
        if not candles:
            return 0

        instrument = cls.get_instrument(symbol)
        normalized = MarketDataService.normalize_symbol(symbol)
        timeframe = MarketDataService.normalize_timeframe(timeframe)
        if timeframe not in ("1m", "1D"):
            logger.warning(
                "Skipping %s %s candle(s) for %s; canonical candle storage is 1m and 1D only",
                len(candles),
                timeframe,
                normalized,
            )
            return 0
        unique_rows = {}

        for candle in candles:
            candle_time = candle["time"]
            if timezone.is_naive(candle_time):
                candle_time = timezone.make_aware(candle_time, py_timezone.utc)
            
            key = (normalized, timeframe, candle_time)
            unique_rows[key] = Candle(
                instrument=instrument,
                symbol=normalized,
                timeframe=timeframe,
                time=candle_time,
                open=Decimal(str(candle["open"])),
                high=Decimal(str(candle["high"])),
                low=Decimal(str(candle["low"])),
                close=Decimal(str(candle["close"])),
                volume=int(candle.get("volume", 0) or 0),
            )
            
        rows = list(unique_rows.values())

        with transaction.atomic():
            Candle.objects.bulk_create(
                rows,
                update_conflicts=True,
                unique_fields=["symbol", "timeframe", "time"],
                update_fields=["open", "high", "low", "close", "volume", "instrument", "updated_at"],
            )
        return len(rows)

    @classmethod
    def list_candles(cls, symbol, timeframe="1m", limit=200, start_dt=None, end_dt=None):
        normalized = MarketDataService.normalize_symbol(symbol)
        timeframe = MarketDataService.normalize_timeframe(timeframe)
        queryset = Candle.objects.filter(symbol=normalized, timeframe=timeframe)
        if start_dt is not None:
            queryset = queryset.filter(time__gte=start_dt)
        if end_dt is not None:
            queryset = queryset.filter(time__lte=end_dt)
        if limit is None:
            candles = list(queryset.order_by("time"))
        else:
            candles = list(queryset.order_by("-time")[: int(limit or 200)])
            candles.reverse()
        return candles

    @classmethod
    def latest_candle(cls, symbol, timeframe="1m"):
        normalized = MarketDataService.normalize_symbol(symbol)
        timeframe = MarketDataService.normalize_timeframe(timeframe)
        return (
            Candle.objects.filter(symbol=normalized, timeframe=timeframe)
            .order_by("-time")
            .first()
        )

class MarketDataService:
    RESOLUTION_TO_FYERS = {
        "1m": "1",
        "3m": "3",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1H": "60",
        "4H": "240",
        "1D": "D",
        "1W": "W",
    }
    # Reduced from 6 hours to 10 seconds to prevent massive Redis
    # memory leaks from storing millions of quotes for inactive symbols.
    QUOTE_CACHE_TIMEOUT_SECONDS = 60


    @classmethod
    def normalize_symbol(cls, symbol):
        if not symbol:
            return symbol
        value = str(symbol).strip()
        if not value:
            return value
        if ":" in value:
            return value.upper()

        # Try to resolve from Instrument master to get correct segment/series
        try:
            from instruments.models import Instrument
            # 1. Prioritize NSE Equity
            instrument = Instrument.objects.filter(symbol=value.upper(), exchange="NSE", segment=10).first()
            
            # 2. Fallback to any generic match if specific equity isn't found
            if not instrument:
                instrument = Instrument.objects.filter(symbol=value.upper()).first()
                
            if instrument and instrument.sym_ticker:
                return instrument.sym_ticker
        except Exception:
            pass

        # Fallback to standard NSE Equity if not found in database
        return f"NSE:{value.upper()}-EQ"

    @classmethod
    def normalize_timeframe(cls, timeframe):
        value = str(timeframe or "1m").strip()
        aliases = {
            "1": "1m",
            "3": "3m",
            "5": "5m",
            "15": "15m",
            "30": "30m",
            "60": "1H",
            "240": "4H",
            "D": "1D",
            "1d": "1D",
            "W": "1W",
            "1w": "1W",
            "1h": "1H",
            "1H": "1H",
            "4h": "4H",
            "4H": "4H",
        }
        normalized = aliases.get(value, value)
        if normalized not in TIMEFRAME_CONFIG:
            raise ValueError(f"Unsupported timeframe '{timeframe}'")
        return normalized

    @classmethod
    def quote_cache_key(cls, symbol):
        return f"marketdata:quote:{cls.normalize_symbol(symbol)}"

    @classmethod
    def get_cached_quote(cls, symbol):
        return cache.get(cls.quote_cache_key(symbol))

    @classmethod
    def cache_quote(cls, symbol, quote):
        normalized = cls.normalize_symbol(symbol)
        payload = {
            **quote,
            "symbol": normalized,
            "updated_at": timezone.now().isoformat(),
        }
        cache.set(cls.quote_cache_key(normalized), payload, timeout=cls.QUOTE_CACHE_TIMEOUT_SECONDS)
        return payload

    @classmethod
    def _candle_list_cache_key(cls, symbol, timeframe):
        return f"marketdata:candles:{cls.normalize_symbol(symbol)}:{cls.normalize_timeframe(timeframe)}"


    @classmethod
    def serialize_candle(cls, candle):
        return {
            "time": int(candle.time.timestamp()),
            "open": float(candle.open),
            "high": float(candle.high),
            "low": float(candle.low),
            "close": float(candle.close),
            "volume": int(candle.volume or 0),
        }

    @classmethod
    def get_timescale_interval(cls, timeframe):
        mapping = {
            "3m": "3 minutes",
            "5m": "5 minutes",
            "15m": "15 minutes",
            "30m": "30 minutes",
            "1H": "1 hour",
            "4H": "4 hours",
            "1W": "1 week",
        }
        return mapping.get(timeframe, "1 minute")

    @classmethod
    def list_candles(cls, symbol, timeframe="1m", limit=200, start_dt=None, end_dt=None):
        normalized = cls.normalize_symbol(symbol)
        timeframe = cls.normalize_timeframe(timeframe)

        if timeframe in ("1m", "1D"):
            candles = CandleRepository.list_candles(
                symbol=normalized,
                timeframe=timeframe,
                limit=limit,
                start_dt=start_dt,
                end_dt=end_dt,
            )
            return [cls.serialize_candle(candle) for candle in candles]

        # Use TimescaleDB continuous aggregate on-the-fly
        from django.db import connection
        db_timeframe = "1D" if timeframe == "1W" else "1m"
        bucket_interval = cls.get_timescale_interval(timeframe)

        query = """
            SELECT 
                time_bucket(%s, "time") AS bucket_time,
                FIRST(open, "time") AS open,
                MAX(high) AS high,
                MIN(low) AS low,
                LAST(close, "time") AS close,
                SUM(volume) AS volume
            FROM marketdata_candle
            WHERE symbol = %s AND timeframe = %s
        """
        params = [bucket_interval, normalized, db_timeframe]

        if start_dt is not None:
            query += ' AND "time" >= %s'
            params.append(start_dt)
        if end_dt is not None:
            query += ' AND "time" <= %s'
            params.append(end_dt)

        query += " GROUP BY bucket_time ORDER BY bucket_time DESC"

        if limit is not None:
            query += " LIMIT %s"
            params.append(int(limit))

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        candles = []
        for row in reversed(rows):
            candles.append({
                "time": int(row[0].timestamp()),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": int(row[5] or 0),
            })
        return candles

    @classmethod
    def serialize_candle_state(cls, candle):
        return {
            "time": int(candle.time.timestamp()),
            "open": float(candle.open),
            "high": float(candle.high),
            "low": float(candle.low),
            "close": float(candle.close),
            "volume": int(candle.volume or 0),
        }

    @classmethod
    def aggregate_candles(cls, candles, timeframe):
        config = TIMEFRAME_CONFIG[cls.normalize_timeframe(timeframe)]
        bucketed = {}

        for candle in sorted(candles or [], key=lambda item: item.time):
            bucket_time = cls.align_time(candle.time, config["unit"], config["bin_size"])
            bucket_key = bucket_time.isoformat()
            if bucket_key not in bucketed:
                bucketed[bucket_key] = CandleState(
                    symbol=candle.symbol,
                    timeframe=timeframe,
                    time=bucket_time,
                    open=float(candle.open),
                    high=float(candle.high),
                    low=float(candle.low),
                    close=float(candle.close),
                    volume=int(candle.volume or 0),
                )
                continue

            current = bucketed[bucket_key]
            current.high = max(current.high, float(candle.high))
            current.low = min(current.low, float(candle.low))
            current.close = float(candle.close)
            current.volume += int(candle.volume or 0)

        return [bucketed[key] for key in sorted(bucketed.keys())]

    @staticmethod
    def align_time(timestamp, unit, bin_size):
        if timezone.is_naive(timestamp):
            timestamp = timezone.make_aware(timestamp, py_timezone.utc)
        if unit == "minute":
            aligned_minute = (timestamp.minute // bin_size) * bin_size
            return timestamp.replace(minute=aligned_minute, second=0, microsecond=0)
        if unit == "hour":
            aligned_hour = (timestamp.hour // bin_size) * bin_size
            return timestamp.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
        if unit == "day":
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        if unit == "week":
            start_of_day = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            return start_of_day - timedelta(days=start_of_day.weekday())
        raise ValueError(f"Unsupported unit '{unit}'")

    @classmethod
    def latest_quote_from_storage(cls, symbol, timeframe="1m"):
        latest_candle = CandleRepository.latest_candle(symbol, timeframe=timeframe)
        if latest_candle is None:
            return None
            
        change = 0.0
        change_percent = 0.0
        
        try:
            daily_candles = cls.list_candles(symbol, timeframe="1D", limit=2)
            if len(daily_candles) >= 2:
                prev_close = float(daily_candles[-2]["close"])
                current_price = float(latest_candle.close)
                if prev_close > 0:
                    change = round(current_price - prev_close, 2)
                    change_percent = round((change / prev_close) * 100, 2)
        except Exception as e:
            logger.debug(f"Could not calculate historical daily change for {symbol}: {e}")

        return cls.cache_quote(
            symbol,
            {
                "price": float(latest_candle.close),
                "open": float(latest_candle.open),
                "high": float(latest_candle.high),
                "low": float(latest_candle.low),
                "close": float(latest_candle.close),
                "volume": int(latest_candle.volume or 0),
                "timestamp": latest_candle.time.isoformat(),
                "resolution": timeframe,
                "change": change,
                "change_percent": change_percent,
            },
        )

    @classmethod
    def get_live_quote_from_fyers(cls, symbol):
        access_token = get_active_fyers_access_token()
        if not access_token:
            return None
        
        try:
            from fyers_apiv3 import fyersModel
            fyers = fyersModel.FyersModel(client_id=settings.FYERS_CLIENT_ID, is_async=False, token=access_token)
            
            normalized = cls.normalize_symbol(symbol)
            data = {"symbols": normalized}
            response = fyers.quotes(data=data)
            
            if response.get("s") == "ok" and "d" in response and response["d"]:
                quote_data = response["d"][0].get("v", {})
                if quote_data:
                    # Fyers timestamp is typically in epoch seconds
                    tt_val = quote_data.get("tt", 0)
                    if not tt_val:
                        tt_val = int(timezone.now().timestamp())
                    dt = datetime.fromtimestamp(int(tt_val), tz=py_timezone.utc)
                    return cls.cache_quote(
                        normalized,
                        {
                            "price": float(quote_data.get("lp", 0)),
                            
                            # Backward compatibility keys
                            "open": float(quote_data.get("open_price", 0)),
                            "high": float(quote_data.get("high_price", 0)),
                            "low": float(quote_data.get("low_price", 0)),
                            "close": float(quote_data.get("prev_close_price", 0)),
                            
                            # New, perfectly accurate daily keys
                            "day_open": float(quote_data.get("open_price", 0)),
                            "day_high": float(quote_data.get("high_price", 0)),
                            "day_low": float(quote_data.get("low_price", 0)),
                            "prev_close": float(quote_data.get("prev_close_price", 0)),
                            "volume": int(quote_data.get("volume", 0)),
                            "timestamp": dt.isoformat(),
                            "resolution": "1m",
                            "change": float(quote_data.get("ch", 0)),
                            "change_percent": float(quote_data.get("chp", 0)),
                        },
                    )
        except Exception as e:
            logger.error(f"Error fetching live quote from Fyers for {symbol}: {e}")
        return None


class FyersHistoricalDataService:
    @classmethod
    def fetch_candles(cls, symbol, timeframe, date_from, date_to):
        access_token = get_active_fyers_access_token()
        if not access_token:
            logger.error("No active Fyers access token found")
            return None

        client_id = settings.FYERS_CLIENT_ID
        auth_header = f"{client_id}:{access_token}"
        resolution = MarketDataService.normalize_timeframe(timeframe)
        api_resolution = MarketDataService.RESOLUTION_TO_FYERS.get(resolution, resolution)

        def _to_epoch(val):
            if isinstance(val, (int, float)):
                return str(int(val))
            val_str = str(val)
            if "T" in val_str or ":" in val_str:
                dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
                return str(int(dt.timestamp()))
            if "-" in val_str:
                dt = datetime.strptime(val_str, "%Y-%m-%d")
                return str(int(dt.replace(tzinfo=py_timezone.utc).timestamp()))
            return val_str

        params = {
            "symbol": MarketDataService.normalize_symbol(symbol),
            "resolution": api_resolution,
            "date_format": "0",
            "range_from": _to_epoch(date_from),
            "range_to": _to_epoch(date_to),
            "cont_flag": "0",
        }

        try:
            from fyers_apiv3 import fyersModel
            fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token)
            data = fyers.history(data=params)
        except Exception as exc:
            logger.exception("Exception while fetching candles for %s: %s", symbol, exc)
            return None

        if data.get("s") == "no_data":
            # Expected behavior when fetching data during off-hours or gaps
            return []

        if data.get("s") != "ok":
            logger.error("Fyers API Error for %s: %s", symbol, data)
            return None

        candles = []
        for item in data.get("candles", []):
            candles.append(
                {
                    "time": datetime.fromtimestamp(int(item[0]), tz=py_timezone.utc),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": int(item[5]),
                }
            )
        return candles

    @classmethod
    def fetch_and_store(cls, symbol, date_from, date_to, timeframe="1m"):
        # Canonical storage is 1m and 1D. Higher timeframes are derived at read time.
        candles = cls.fetch_candles(symbol, timeframe, date_from, date_to)
        if candles:
            CandleRepository.upsert_candles(symbol, timeframe, candles)
        return candles


class HistoricalCandleService:
    MAX_LIMIT = 1000
    DEFAULT_LIMIT = 240
    MAX_SYNC_FETCH_DAYS = 120
    FETCH_LOCK_TTL_SECONDS = 1
    TRADING_MINUTES_PER_DAY = 375
    TIMEFRAME_MINUTES = {
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1H": 60,
        "4H": 240,
        "1D": TRADING_MINUTES_PER_DAY,
        "1W": TRADING_MINUTES_PER_DAY * 5,
    }

    @classmethod
    def list_candles(cls, symbol, resolution="1m", limit=200, start_dt=None, end_dt=None):
        return MarketDataService.list_candles(
            symbol=symbol,
            timeframe=resolution,
            limit=limit,
            start_dt=start_dt,
            end_dt=end_dt,
        )

    @classmethod
    def chart_window(cls, symbol, resolution="1m", limit=DEFAULT_LIMIT, before=None):
        normalized = MarketDataService.normalize_symbol(symbol)
        timeframe = MarketDataService.normalize_timeframe(resolution)
        limit = cls._normalize_limit(limit)
        end_dt = cls._coerce_before(before)
        start_dt = end_dt - timedelta(days=cls._lookback_days(timeframe, limit))

        candles = cls.list_candles(
            symbol=normalized,
            resolution=timeframe,
            limit=limit,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        fetched_count = 0
        fetch_attempted = False

        if cls._should_fetch(candles, limit, end_dt):
            fetch_attempted = True
            fetched_count = cls._fetch_missing_window(normalized, timeframe, start_dt, end_dt)
            if fetched_count:
                candles = cls.list_candles(
                    symbol=normalized,
                    resolution=timeframe,
                    limit=limit,
                    start_dt=start_dt,
                    end_dt=end_dt,
                )
            
            # Fallback: if we still don't have enough candles (e.g. broker API failed or gap),
            # just query the DB without start_dt to get the latest available data before end_dt.
            if not candles:
                candles = cls.list_candles(
                    symbol=normalized,
                    resolution=timeframe,
                    limit=limit,
                    start_dt=None,
                    end_dt=end_dt,
                )

        earliest_time = candles[0]["time"] if candles else None

        return {
            "symbol": normalized,
            "interval": timeframe,
            "candles": candles,
            "window": {
                "start": int(start_dt.timestamp()),
                "end": int(end_dt.timestamp()),
                "before": int(end_dt.timestamp()),
            },
            "pagination": {
                "has_more": len(candles) >= int(limit),
                "next_before": earliest_time - 1 if earliest_time else None,
            },
            "source": {
                "database_count": len(candles),
                "fetched_count": fetched_count,
                "fetch_attempted": fetch_attempted,
            },
            "backfill_requested": fetch_attempted,
        }

    @classmethod
    def _normalize_limit(cls, limit):
        try:
            value = int(limit or cls.DEFAULT_LIMIT)
        except (TypeError, ValueError):
            value = cls.DEFAULT_LIMIT
        return max(50, min(cls.MAX_LIMIT, value))

    @staticmethod
    def _coerce_before(before):
        if before in (None, "", "latest"):
            return timezone.now()
        try:
            timestamp = float(before)
            return datetime.fromtimestamp(timestamp, tz=py_timezone.utc) - timedelta(seconds=1)
        except (TypeError, ValueError):
            parsed = datetime.fromisoformat(str(before).replace("Z", "+00:00"))
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, py_timezone.utc)
            return parsed - timedelta(seconds=1)

    @classmethod
    def _lookback_days(cls, timeframe, limit):
        if timeframe == "1D":
            return max(90, int(limit * 2.2))
        if timeframe == "1W":
            return max(365, int(limit * 10))
        minutes = cls.TIMEFRAME_MINUTES.get(timeframe, 1) * int(limit)
        trading_days = ceil(minutes / cls.TRADING_MINUTES_PER_DAY)
        return max(4, int(trading_days * 2.2) + 2)

    @staticmethod
    def _should_fetch(candles, limit, end_dt=None):
        if not candles:
            return True
        if len(candles) < min(int(limit), 120):
            return True
            
        if end_dt:
            latest_time = max(c["time"] for c in candles)
            if (end_dt.timestamp() - latest_time) > 1:  # 1 second tolerance
                return True
                
        return False

    @classmethod
    def _fetch_missing_window(cls, symbol, timeframe, start_dt, end_dt):
        timeframe = MarketDataService.normalize_timeframe(timeframe)
        db_timeframe = "1D" if timeframe in {"1D", "1W"} else "1m"
        normalized = MarketDataService.normalize_symbol(symbol)
        
        lock_key = (
            "marketdata:chart_fetch:"
            f"{normalized}:"
            f"{db_timeframe}:{start_dt.date().isoformat()}:{end_dt.date().isoformat()}"
        )
        if cache.get(lock_key):
            return 0

        cache.set(lock_key, True, timeout=cls.FETCH_LOCK_TTL_SECONDS)
        fetched_total = 0
        chunk_start = start_dt.date()
        end_date = end_dt.date()
        lookback_days = max(1, (end_date - chunk_start).days + 1)
        chunk_days = 90

        if lookback_days > cls.MAX_SYNC_FETCH_DAYS:
            try:
                from .tasks import backfill_missing_candles

                backfill_missing_candles.delay(
                    MarketDataService.normalize_symbol(symbol),
                    lookback_days=lookback_days,
                    timeframe=db_timeframe,
                )
            except Exception as exc:
                logger.debug("Could not enqueue chart backfill for %s: %s", symbol, exc)
            chunk_start = max(chunk_start, end_date - timedelta(days=chunk_days - 1))

        api_failed = False
        while chunk_start <= end_date:
            chunk_end = min(chunk_start + timedelta(days=chunk_days), end_date)
            fetched = FyersHistoricalDataService.fetch_and_store(
                symbol=symbol,
                date_from=chunk_start.isoformat(),
                date_to=chunk_end.isoformat(),
                timeframe=db_timeframe,
            )
            if fetched is None:
                api_failed = True
                break
                
            fetched_total += len(fetched)
            chunk_start = chunk_end + timedelta(days=1)

        if api_failed:
            cache.delete(lock_key)
            return 0

        return fetched_total


class FyersDataService:
    """
    Backward-compatible facade used by existing strategy/backtesting modules.
    """

    @classmethod
    def get_backtest_candles(
        cls,
        symbol,
        resolution,
        start_dt,
        end_dt,
        fetch_missing=True,
        clean=True,
        persist=True,
    ):
        timeframe = MarketDataService.normalize_timeframe(resolution)
        start_dt = cls._coerce_datetime(start_dt, start_of_day=True)
        end_dt = cls._coerce_datetime(end_dt, start_of_day=False)
        db_timeframe = "1D" if timeframe in {"1D", "1W"} else "1m"

        candles = CandleRepository.list_candles(
            symbol=symbol,
            timeframe=db_timeframe,
            limit=None,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        needs_fetch = False
        if fetch_missing:
            if not candles:
                needs_fetch = True
            else:
                first_candle_dt = candles[0].time.date()
                last_candle_dt = candles[-1].time.date()
                # If there's a > 4 day gap (to account for long weekends/holidays) at start or end, fetch data
                if (first_candle_dt - start_dt.date()).days > 4 or (end_dt.date() - last_candle_dt).days > 4:
                    needs_fetch = True

        if needs_fetch:
            chunk_start = start_dt.date()
            end_date_limit = end_dt.date()
            fetched_any = False
            
            while chunk_start <= end_date_limit:
                chunk_end = min(chunk_start + timedelta(days=90), end_date_limit)
                fetched = FyersHistoricalDataService.fetch_and_store(
                    symbol=symbol,
                    date_from=chunk_start.isoformat(),
                    date_to=chunk_end.isoformat(),
                    timeframe=db_timeframe,
                )
                if fetched:
                    fetched_any = True
                chunk_start = chunk_end + timedelta(days=1)
                
            if fetched_any:
                candles = CandleRepository.list_candles(
                    symbol=symbol,
                    timeframe=db_timeframe,
                    limit=None,
                    start_dt=start_dt,
                    end_dt=end_dt,
                )

        if timeframe not in ("1m", "1D"):
            candles = MarketDataService.aggregate_candles(candles, timeframe)

        records = [
            {
                "timestamp": candle.time,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in candles
        ]
        df = pd.DataFrame(records)
        if df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        if clean:
            return cls.normalize_candles_df(df)
        return df

    @classmethod
    def normalize_candles_df(cls, df):
        if df is None or df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        normalized = df.copy()
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"])
        normalized = normalized.sort_values("timestamp")
        normalized = normalized.drop_duplicates(subset=["timestamp"], keep="last")
        normalized = normalized.set_index("timestamp")
        normalized.index.name = "timestamp"
        return normalized[["open", "high", "low", "close", "volume"]]

    @staticmethod
    def _coerce_datetime(value, start_of_day):
        if isinstance(value, datetime):
            if timezone.is_naive(value):
                return timezone.make_aware(value, py_timezone.utc)
            return value
        if isinstance(value, date):
            base = datetime.combine(value, time.min if start_of_day else time.max)
            return timezone.make_aware(base, py_timezone.utc)
        raise TypeError(f"Unsupported date value: {value!r}")

