import hashlib

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class MarketDataStreamer:
    @classmethod
    def chart_group(cls, symbol, interval):
        return 'chart.' + cls.symbol_group(symbol) + '.' + interval

    @staticmethod
    def publish(group, message):
        """Send JSON-native display data to its subscribed Channels group."""
        layer = get_channel_layer()
        if layer is not None:
            async_to_sync(layer.group_send)(group, {'type': 'marketdata.message', 'message': message})

    @classmethod
    def symbol_group(cls, symbol):
        return 'market.' + hashlib.sha256(symbol.encode()).hexdigest()

