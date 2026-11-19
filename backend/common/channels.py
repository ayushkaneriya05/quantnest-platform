"""JSON-safe Channels payloads and committed browser updates."""

import asyncio
import logging
import os
from queue import Full, Queue
from threading import Thread

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from rest_framework.utils.encoders import JSONEncoder

_encoder = JSONEncoder()
logger = logging.getLogger(__name__)
_delivery_queues = {}


def json_safe_channel_data(data):
    """Match REST JSON encoding before publishing data through a channel layer."""
    if isinstance(data, dict):
        return {str(key): json_safe_channel_data(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [json_safe_channel_data(value) for value in data]
    if data is None or isinstance(data, (str, int, float, bool)):
        return data
    return _encoder.default(data)


async def _send(group, message):
    layer = get_channel_layer()
    if layer is not None:
        await asyncio.wait_for(layer.group_send(group, message), timeout=2)


def _delivery_queue(pid):
    """One ordered, bounded display queue per process, including after a fork."""
    if pid in _delivery_queues:
        return _delivery_queues[pid]
    pending = Queue(maxsize=256)
    # setdefault chooses one queue even when two request threads publish first.
    current = _delivery_queues.setdefault(pid, pending)
    if current is not pending:
        return current

    def deliver():
        while True:
            group, message = pending.get()
            try:
                async_to_sync(_send)(group, message)
            except Exception:
                logger.exception("Could not publish browser update to %s", group)
            finally:
                pending.task_done()

    # These are display hints: shutdown must not wait for a slow Redis socket.
    # REST snapshots and stored notifications remain the recovery authority.
    Thread(target=deliver, name="browser-updates", daemon=True).start()
    return pending


def publish_channel_message(group: str, message: dict):
    """Commit first; browser delivery must never hold up a financial acknowledgement."""
    try:
        payload = json_safe_channel_data(message)  # Freeze before callers mutate their models.
    except (TypeError, ValueError):
        logger.exception("Could not encode browser update for %s", group)
        return

    def enqueue_after_commit():
        try:
            _delivery_queue(os.getpid()).put_nowait((group, payload))
        except Full:
            logger.warning("Browser update queue full; recover %s from its REST snapshot", group)

    transaction.on_commit(enqueue_after_commit, robust=True)


def publish_trading_update(group: str, event_type: str, data: dict):
    """Browser updates are best effort; publish only after the ledger commits."""
    publish_channel_message(group, {"type": "trading.update", "message": {
        "event_type": event_type, "data": data}})
