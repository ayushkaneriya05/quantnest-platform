from datetime import datetime, timezone as dt_timezone

from django.core.cache import cache


class QuoteStore:
    """Process-independent store for the latest live quote per symbol."""

    CACHE_KEY_PREFIX = "marketdata:quote:"
    TTL_SECONDS = 60

    @classmethod
    def _key(cls, symbol):
        from .services import MarketDataService
        return f"{cls.CACHE_KEY_PREFIX}{MarketDataService.normalize_symbol(symbol)}"


    @classmethod
    def set_latest(cls, symbol, quote):
        from .services import MarketDataService

        normalized = MarketDataService.normalize_symbol(symbol)
        payload = {
            **(quote or {}),
            "symbol": normalized,
            "updated_at": datetime.now(dt_timezone.utc).isoformat(),
        }
        cache.set(cls._key(normalized), payload, timeout=cls.TTL_SECONDS)
        return payload


    @classmethod
    def get_latest(cls, symbol, max_age_seconds=None):
        payload = cache.get(cls._key(symbol))
        if not payload or max_age_seconds is None:
            return payload

        updated_at = payload.get("updated_at")
        if not updated_at:
            return None
        try:
            timestamp = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=dt_timezone.utc)
            age = (datetime.now(dt_timezone.utc) - timestamp).total_seconds()
        except (TypeError, ValueError):
            return None
        return payload if age <= max_age_seconds else None


    @classmethod
    def delete(cls, symbol):
        cache.delete(cls._key(symbol))
