import re

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

from .services import MarketDataService


class MarketDataStreamer:
    @classmethod
    def _group_name(cls, symbol):
        return re.sub(r"[^a-zA-Z0-9\-_.]", "_", symbol)

    @classmethod
    def _cache_key(cls, symbol):
        return MarketDataService.quote_cache_key(symbol)

    @classmethod
    def normalize_symbol(cls, symbol):
        return MarketDataService.normalize_symbol(symbol)

    @classmethod
    def update_quote(cls, symbol, quote):
        symbol = cls.normalize_symbol(symbol)
        payload = MarketDataService.cache_quote(symbol, quote)
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return payload
        async_to_sync(channel_layer.group_send)(
            cls._group_name(symbol),
            {
                "type": "marketdata.message",
                "message": {
                    "type": "tick",
                    "symbol": symbol,
                    "data": payload,
                },
            },
        )
        return payload

    @classmethod
    def publish_candle_update(cls, symbol, candle, event_type="candle.update"):
        symbol = cls.normalize_symbol(symbol)
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return None
        message = {
            "type": event_type,
            "symbol": symbol,
            "candle": {
                "time": int(candle.time.timestamp()),
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close),
                "volume": int(candle.volume or 0),
            },
        }
        async_to_sync(channel_layer.group_send)(
            cls._group_name(symbol),
            {
                "type": "marketdata.message",
                "message": message,
            },
        )
        return message

    @classmethod
    def get_cached_quote(cls, symbol):
        symbol = cls.normalize_symbol(symbol)
        return cache.get(cls._cache_key(symbol))

    @classmethod
    def poll_latest_candle_quote(cls, symbol, resolution="1m"):
        return MarketDataService.latest_quote_from_storage(symbol, timeframe=resolution)
