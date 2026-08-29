import re

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .services import MarketDataService
from .quote_store import QuoteStore


class MarketDataStreamer:
    @classmethod
    def _group_name(cls, symbol):
        return re.sub(r"[^a-zA-Z0-9\-_.]", "_", symbol)

    @classmethod
    def normalize_symbol(cls, symbol):
        return MarketDataService.normalize_symbol(symbol)

    @classmethod
    def publish_tick(cls, symbol, quote):
        symbol = cls.normalize_symbol(symbol)
        payload = QuoteStore.set_latest(symbol, quote)
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

