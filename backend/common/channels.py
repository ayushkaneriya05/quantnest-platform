"""JSON-safe Channels payloads and committed browser updates."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from rest_framework.utils.encoders import JSONEncoder

_encoder = JSONEncoder()
logger = logging.getLogger(__name__)


def json_safe_channel_data(data):
    """Match REST JSON encoding before publishing data through a channel layer."""
    if isinstance(data, dict):
        return {str(key): json_safe_channel_data(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [json_safe_channel_data(value) for value in data]
    if data is None or isinstance(data, (str, int, float, bool)):
        return data
    return _encoder.default(data)


def publish_trading_update(group: str, event_type: str, data: dict):
    """Browser updates are best effort; publish only after the ledger commits."""
    def send_after_commit():
        try:
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                message = json_safe_channel_data({"event_type": event_type, "data": data})
                async_to_sync(channel_layer.group_send)(group, {"type": "trading.update", "message": message})
        except Exception:
            logger.exception("Could not publish %s to %s", event_type, group)

    transaction.on_commit(send_after_commit)
