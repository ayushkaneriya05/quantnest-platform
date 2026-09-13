"""
marketdata/services.py

Low-level market-data helpers.

Higher-level consumers (Chart, Backtest, Strategy) should call
``MarketDataRepository.get_candles()`` for end-to-end correctness.
This file provides:
  - MarketStatusService  — live market open/closed check via Fyers API.
  - MarketDataService    — symbol/timeframe normalisation, DB queries, upsert,
                           broker fetch, and backfill helpers.
  - ChartDataService     — chart window builder used by the frontend.
"""
import logging
from datetime import datetime, timedelta
from datetime import timezone as py_timezone
from decimal import Decimal
from math import ceil

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from common.cache_keys import CacheKeys

from instruments.models import Instrument

from .models import CANONICAL_TIMEFRAMES, Candle
from .utils import get_active_fyers_access_token, ist

logger = logging.getLogger(__name__)

SUPPORTED_TIMEFRAMES = ("1m", "3m", "5m", "15m", "30m", "1H", "4H", "1D", "1W")


class AmbiguousSymbolError(ValueError):
    """Raised when symbol resolution would silently pick the wrong instrument."""


class MarketStatusService:
    """Live market open/closed check via the Fyers API."""

    CACHE_KEY = CacheKeys.MARKET_STATUS
    CACHE_TIMEOUT = 120  # seconds

    @classmethod
    def is_market_open(cls) -> bool:
        cached = cache.get(cls.CACHE_KEY)
        if cached is not None:
            return cached

        now_ist = datetime.now(ist)
        is_weekday = now_ist.weekday() < 5
        market_start = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)

        if not is_weekday or now_ist < market_start or now_ist > market_end:
            cache.set(cls.CACHE_KEY, False, timeout=cls.CACHE_TIMEOUT)
            return False

        try:
            from fyers_apiv3 import fyersModel
            access_token = get_active_fyers_access_token()
            if not access_token:
                cache.set(cls.CACHE_KEY, True, timeout=cls.CACHE_TIMEOUT)
                return True

            fyers = fyersModel.FyersModel(client_id=settings.FYERS_CLIENT_ID, token=access_token)
            response = fyers.market_status()
            if response.get("s") == "ok" and "marketStatus" in response:
                for item in response["marketStatus"]:
                    if item.get("exchange") == "NSE" and item.get("segment") == "EQUITY":
                        is_open = item.get("status") == "OPEN"
                        cache.set(cls.CACHE_KEY, is_open, timeout=cls.CACHE_TIMEOUT)
                        return is_open
        except Exception as exc:
            logger.warning("Failed to fetch market status from Fyers: %s", exc)

        cache.set(cls.CACHE_KEY, True, timeout=cls.CACHE_TIMEOUT)
        return True


class MarketDataService:
    """Symbol/timeframe normalisation, raw DB access, broker fetch, and upsert."""

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

    # TimescaleDB time_bucket intervals for derived timeframes.
    _TIMESCALE_INTERVAL = {
        "3m": "3 minutes",
        "5m": "5 minutes",
        "15m": "15 minutes",
        "30m": "30 minutes",
        "1H": "1 hour",
        "4H": "4 hours",
        "1W": "1 week",
    }

    @classmethod
    def normalize_symbol(cls, symbol: str, *, strict: bool = False) -> str:
        """
        Return the canonical Fyers ticker for *symbol*.

        If *symbol* already contains a colon it is already a full Fyers ticker
        and is returned upper-cased.

        Otherwise the Instrument master is queried:
          1. NSE equity (segment=10) preferred.
          2. Any single unique match accepted.

        When no match is found:
          - strict=False (default) — falls back to ``NSE:<SYMBOL>-EQ`` with
            a warning logged.  This may be incorrect for non-equity instruments.
          - strict=True — raises ``AmbiguousSymbolError``.

        Always pass strict=True when the caller knows the instrument is not
        an NSE equity (e.g. indices, futures, options).
        """
        if not symbol:
            return symbol
        value = str(symbol).strip()
        if not value:
            return value
        if ":" in value:
            return value.upper()

        upper = value.upper()
        try:
            # Prefer NSE equity
            instrument = Instrument.objects.filter(symbol=upper, exchange="NSE", segment=10).first()
            if instrument:
                return instrument.sym_ticker

            # Fall back to any unique match
            candidates = list(
                Instrument.objects.filter(symbol=upper)
                .values("sym_ticker", "exchange", "instrument_type")
            )
            if len(candidates) == 1:
                return candidates[0]["sym_ticker"]
            if len(candidates) > 1:
                if strict:
                    raise AmbiguousSymbolError(
                        f"Symbol {upper!r} maps to multiple instruments: "
                        + ", ".join(c["sym_ticker"] for c in candidates)
                    )
                logger.warning(
                    "Ambiguous symbol %r (%d matches). Using %s. "
                    "Pass instrument_id for precision.",
                    upper, len(candidates), candidates[0]["sym_ticker"],
                )
                return candidates[0]["sym_ticker"]
        except AmbiguousSymbolError:
            raise
        except Exception:
            pass

        fallback = f"NSE:{upper}-EQ"
        if strict:
            raise AmbiguousSymbolError(
                f"Symbol {upper!r} not found in Instrument master; "
                f"cannot safely infer ticker (would guess {fallback})."
            )
        logger.warning(
            "Symbol %r not found in Instrument master; falling back to %s. "
            "May be incorrect for non-equity instruments.",
            upper, fallback,
        )
        return fallback

    @classmethod
    def normalize_timeframe(cls, timeframe: str) -> str:
        value = str(timeframe or "1m").strip()
        aliases = {
            "1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
            "60": "1H", "240": "4H",
            "D": "1D", "1d": "1D",
            "W": "1W", "1w": "1W",
            "1h": "1H", "4h": "4H",
        }
        normalized = aliases.get(value, value)
        if normalized not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe '{timeframe}'")
        return normalized

    @classmethod
    def serialize_candle(cls, candle) -> dict:
        return {
            "time": int(candle.time.timestamp()),
            "open": float(candle.open),
            "high": float(candle.high),
            "low": float(candle.low),
            "close": float(candle.close),
            "volume": int(candle.volume or 0),
        }

    @classmethod
    def list_candles(cls, symbol, timeframe="1m", limit=200, start_dt=None, end_dt=None):
        """
        Return serialised candle dicts from the DB.

        Canonical timeframes (1m, 1D) are read directly.
        Derived timeframes use TimescaleDB time_bucket aggregation:
          1W  → buckets over 1D rows
          all other intraday derived → buckets over 1m rows
        """
        normalized = cls.normalize_symbol(symbol)
        timeframe = cls.normalize_timeframe(timeframe)

        if timeframe in CANONICAL_TIMEFRAMES:
            candles = cls.list_raw_candles(
                symbol=normalized, timeframe=timeframe,
                limit=limit, start_dt=start_dt, end_dt=end_dt,
            )
            return [cls.serialize_candle(c) for c in candles]

       
        db_timeframe = "1D" if timeframe == "1W" else "1m"
        bucket_interval = cls._TIMESCALE_INTERVAL[timeframe]

        from django.db import connection

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

        return [
            {
                "time": int(row[0].timestamp()),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": int(row[5] or 0),
            }
            for row in reversed(rows)
        ]

    @classmethod
    def latest_quote_from_storage(cls, symbol, timeframe="1m"):
        latest_candle = cls.latest_candle(symbol, timeframe=timeframe)
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
        except Exception as exc:
            logger.debug("Could not calculate daily change for %s: %s", symbol, exc)

        return {
            "symbol": cls.normalize_symbol(symbol),
            "price": float(latest_candle.close),
            "open": float(latest_candle.open),
            "high": float(latest_candle.high),
            "low": float(latest_candle.low),
            "close": float(latest_candle.close),
            "volume": int(latest_candle.volume or 0),
            "timestamp": latest_candle.time.isoformat(),
            "updated_at": latest_candle.time.isoformat(),
            "resolution": timeframe,
            "change": change,
            "change_percent": change_percent,
        }

    @classmethod
    def get_live_quote_from_fyers(cls, symbol):
        access_token = get_active_fyers_access_token()
        if not access_token:
            return None

        try:
            from fyers_apiv3 import fyersModel
            fyers = fyersModel.FyersModel(
                client_id=settings.FYERS_CLIENT_ID, is_async=False, token=access_token
            )
            normalized = cls.normalize_symbol(symbol)
            response = fyers.quotes(data={"symbols": normalized})

            if response.get("s") == "ok" and response.get("d"):
                quote_data = response["d"][0].get("v", {})
                if quote_data:
                    tt_val = quote_data.get("tt") or int(timezone.now().timestamp())
                    dt = datetime.fromtimestamp(int(tt_val), tz=py_timezone.utc)
                    return {
                        "symbol": normalized,
                        "price": float(quote_data.get("lp", 0)),
                        "open": float(quote_data.get("open_price", 0)),
                        "high": float(quote_data.get("high_price", 0)),
                        "low": float(quote_data.get("low_price", 0)),
                        "close": float(quote_data.get("prev_close_price", 0)),
                        "day_open": float(quote_data.get("open_price", 0)),
                        "day_high": float(quote_data.get("high_price", 0)),
                        "day_low": float(quote_data.get("low_price", 0)),
                        "prev_close": float(quote_data.get("prev_close_price", 0)),
                        "volume": int(quote_data.get("volume", 0)),
                        "timestamp": dt.isoformat(),
                        "resolution": "1m",
                        "change": float(quote_data.get("ch", 0)),
                        "change_percent": float(quote_data.get("chp", 0)),
                        "updated_at": dt.isoformat(),
                    }
        except Exception as exc:
            logger.error("Error fetching live quote from Fyers for %s: %s", symbol, exc)
        return None

    @staticmethod
    def get_instrument(symbol):
        normalized = MarketDataService.normalize_symbol(symbol)
        return Instrument.objects.filter(sym_ticker=normalized).first()

    @classmethod
    def upsert_candles(cls, symbol, timeframe, candles) -> int:
        """
        Upsert candles into the canonical store (1m or 1D only).
        Non-canonical timeframes are rejected — they must be derived, not stored.
        Returns the number of rows written.
        """
        if not candles:
            return 0

        instrument = cls.get_instrument(symbol)
        normalized = cls.normalize_symbol(symbol)
        timeframe = cls.normalize_timeframe(timeframe)

        if timeframe not in CANONICAL_TIMEFRAMES:
            logger.warning(
                "Refusing to upsert %d %s candle(s) for %s: "
                "only 1m and 1D are canonical. Derived timeframes must not be stored.",
                len(candles), timeframe, normalized,
            )
            return 0

        unique_rows: dict = {}
        for candle in candles:
            candle_time = candle["time"]
            if isinstance(candle_time, (int, float)):
                candle_time = datetime.fromtimestamp(int(candle_time), tz=py_timezone.utc)
            elif timezone.is_naive(candle_time):
                candle_time = candle_time.replace(tzinfo=py_timezone.utc)
            else:
                candle_time = candle_time.astimezone(py_timezone.utc)

            unique_rows[(normalized, timeframe, candle_time)] = Candle(
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
    def list_raw_candles(cls, symbol, timeframe="1m", limit=200, start_dt=None, end_dt=None):
        normalized = cls.normalize_symbol(symbol)
        timeframe = cls.normalize_timeframe(timeframe)
        qs = Candle.objects.filter(symbol=normalized, timeframe=timeframe)
        if start_dt is not None:
            qs = qs.filter(time__gte=start_dt)
        if end_dt is not None:
            qs = qs.filter(time__lte=end_dt)
        if limit is None:
            return list(qs.order_by("time"))
        candles = list(qs.order_by("-time")[: int(limit)])
        candles.reverse()
        return candles

    @classmethod
    def latest_candle(cls, symbol, timeframe="1m"):
        normalized = cls.normalize_symbol(symbol)
        timeframe = cls.normalize_timeframe(timeframe)
        return (
            Candle.objects.filter(symbol=normalized, timeframe=timeframe)
            .order_by("-time")
            .first()
        )

    @classmethod
    def fetch_candles_from_broker(cls, symbol, timeframe, date_from, date_to):
        """
        Fetch candles from FYERS for a canonical timeframe (1m or 1D).

        Returns:
          list of dicts  — candles returned (may be empty on non-trading days)
          []             — FYERS confirmed no_data (valid empty — holiday/weekend)
          None           — FYERS API error (auth/network failure)
        """
        access_token = get_active_fyers_access_token()
        if not access_token:
            logger.error("No active Fyers access token found")
            return None

        resolution = cls.normalize_timeframe(timeframe)
        if resolution not in CANONICAL_TIMEFRAMES:
            logger.error(
                "fetch_candles_from_broker called with non-canonical timeframe %r. "
                "Use 1m or 1D only.",
                resolution,
            )
            return None

        api_resolution = cls.RESOLUTION_TO_FYERS[resolution]

        def _to_epoch(val) -> int:
            if isinstance(val, (int, float)):
                return int(val)
            val_str = str(val)
            if "T" in val_str or " " in val_str:
                dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
                return int(dt.timestamp())
            if "-" in val_str:
                # Explicit UTC — never rely on local timezone
                dt = datetime.fromisoformat(val_str[:10]).replace(tzinfo=py_timezone.utc)
                return int(dt.timestamp())
            return int(val_str)

        params = {
            "symbol": cls.normalize_symbol(symbol),
            "resolution": api_resolution,
            "date_format": "0",
            "range_from": str(_to_epoch(date_from)),
            "range_to": str(_to_epoch(date_to)),
            "cont_flag": "0",
        }

        try:
            from fyers_apiv3 import fyersModel
            fyers = fyersModel.FyersModel(
                client_id=settings.FYERS_CLIENT_ID, is_async=False, token=access_token
            )
            data = fyers.history(data=params)
        except Exception as exc:
            logger.exception("Exception fetching candles for %s: %s", symbol, exc)
            return None

        status = data.get("s")
        if status == "no_data":
            return []
        if status != "ok":
            logger.error("Fyers API error for %s (status=%s): %s", symbol, status, data)
            return None

        return [
            {
                "time": datetime.fromtimestamp(int(item[0]), tz=py_timezone.utc),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": int(item[5]),
            }
            for item in data.get("candles", [])
        ]

    @classmethod
    def backfill_candles_from_broker(cls, symbol, date_from, date_to, timeframe="1m"):
        """
        Fetch from broker and upsert canonical candles.

        Returns the fetched list (possibly empty), or None on broker error.
        Never treats a broker error as valid empty data.
        """
        candles = cls.fetch_candles_from_broker(symbol, timeframe, date_from, date_to)
        if candles is None:
            return None  # broker error — do not upsert
        if candles:
            cls.upsert_candles(symbol, timeframe, candles)
        return candles


class ChartDataService:
    """Chart window builder — used by the market-data views for the frontend."""

    MAX_LIMIT = 1000
    DEFAULT_LIMIT = 240
    MAX_SYNC_FETCH_DAYS = 120
    FETCH_LOCK_TTL_SECONDS = 10
    TRADING_MINUTES_PER_DAY = 375

    _TIMEFRAME_MINUTES = {
        "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
        "1H": 60, "4H": 240,
        "1D": 375, "1W": 375 * 5,
    }

    @classmethod
    def list_candles(cls, symbol, resolution="1m", limit=200, start_dt=None, end_dt=None):
        return MarketDataService.list_candles(
            symbol=symbol, timeframe=resolution,
            limit=limit, start_dt=start_dt, end_dt=end_dt,
        )

    @classmethod
    def chart_window(cls, symbol, resolution="1m", limit=DEFAULT_LIMIT, before=None):
        normalized = MarketDataService.normalize_symbol(symbol)
        timeframe = MarketDataService.normalize_timeframe(resolution)
        limit = cls._normalize_limit(limit)
        end_dt = cls._coerce_before(before)
        start_dt = end_dt - timedelta(days=cls._lookback_days(timeframe, limit))

        candles = cls.list_candles(
            symbol=normalized, resolution=timeframe,
            limit=limit, start_dt=start_dt, end_dt=end_dt,
        )
        fetched_count = 0
        fetch_attempted = False

        if cls._should_fetch(candles, limit, end_dt):
            fetch_attempted = True
            fetched_count = cls._fetch_missing_window(normalized, timeframe, start_dt, end_dt)
            if fetched_count:
                candles = cls.list_candles(
                    symbol=normalized, resolution=timeframe,
                    limit=limit, start_dt=start_dt, end_dt=end_dt,
                )
            if not candles:
                candles = cls.list_candles(
                    symbol=normalized, resolution=timeframe,
                    limit=limit, start_dt=None, end_dt=end_dt,
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
    def _normalize_limit(cls, limit) -> int:
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
            return datetime.fromtimestamp(float(before), tz=py_timezone.utc) - timedelta(seconds=1)
        except (TypeError, ValueError):
            parsed = datetime.fromisoformat(str(before).replace("Z", "+00:00"))
            if timezone.is_naive(parsed):
                parsed = parsed.replace(tzinfo=py_timezone.utc)
            return parsed - timedelta(seconds=1)

    @classmethod
    def _lookback_days(cls, timeframe, limit) -> int:
        if timeframe == "1D":
            return max(90, int(limit * 2.2))
        if timeframe == "1W":
            return max(365, int(limit * 10))
        minutes = cls._TIMEFRAME_MINUTES.get(timeframe, 1) * int(limit)
        trading_days = ceil(minutes / cls.TRADING_MINUTES_PER_DAY)
        return max(4, int(trading_days * 2.2) + 2)

    @staticmethod
    def _should_fetch(candles, limit, end_dt=None) -> bool:
        if not candles:
            return True
        if len(candles) < min(int(limit), 120):
            return True
        if end_dt:
            latest_time = max(c["time"] for c in candles)
            if (end_dt.timestamp() - latest_time) > 10:  # 10-second tolerance
                return True
        return False

    @classmethod
    def _fetch_missing_window(cls, symbol, timeframe, start_dt, end_dt) -> int:
        """
        Fetch the canonical backing data for *timeframe* in [start_dt, end_dt].

        Canonical backing rules:
          1W  → fetch 1D from broker
          all other derived intraday → fetch 1m from broker
          canonical 1m / 1D → fetch as-is

        The db_timeframe variable is NEVER re-normalised back to the derived
        timeframe string — that was the original 1W→1W bug.
        """
        timeframe = MarketDataService.normalize_timeframe(timeframe)

        if timeframe in CANONICAL_TIMEFRAMES:
            db_timeframe = timeframe
        elif timeframe == "1W":
            db_timeframe = "1D"
        else:
            db_timeframe = "1m"

        normalized = MarketDataService.normalize_symbol(symbol)
        lock_key = CacheKeys.CHART_FETCH_LOCK.format(
            symbol=normalized,
            timeframe=db_timeframe,
            start=start_dt.date().isoformat(),
            end=end_dt.date().isoformat(),
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
                backfill_missing_candles.delay(normalized, lookback_days=lookback_days, timeframe=db_timeframe)
            except Exception as exc:
                logger.debug("Could not enqueue chart backfill for %s: %s", symbol, exc)
            chunk_start = max(chunk_start, end_date - timedelta(days=chunk_days - 1))

        api_failed = False
        while chunk_start <= end_date:
            chunk_end = min(chunk_start + timedelta(days=chunk_days), end_date)
            fetched = MarketDataService.backfill_candles_from_broker(
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
