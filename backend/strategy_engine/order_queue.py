"""Durable, scope-isolated order transport backed by Redis Streams."""
import json
import logging
import os
import socket
import time
import uuid

from django.conf import settings

logger = logging.getLogger(__name__)

GROUP = "execution"
BLOCK_MS = 1000
CLAIM_IDLE_MS = 30_000


def _redis():
    import redis
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def stream_key(scope):
    return f"quantnest:orders:{str(scope).lower()}"


def pending_key(scope, session_id, instrument_id):
    return f"quantnest:pending-order:{str(scope).lower()}:{session_id}:{int(instrument_id)}"


def entry_is_allowed(session_status, intent):
    """Reject delayed entries after pause/stop while allowing queued exits."""
    return str(intent or "ENTRY").upper() != "ENTRY" or str(session_status).upper() == "RUNNING"


def publish_order(request):
    """Persist an order request before returning it to the strategy worker."""
    payload = request.to_dict() if hasattr(request, "to_dict") else dict(request)
    payload.setdefault("request_id", str(uuid.uuid4()))
    client = _redis()
    serialized = json.dumps(payload, separators=(",", ":"))
    enqueue_once = """
    local pending = redis.call('GET', KEYS[2])
    if pending then
      return cjson.decode(pending).request_id
    end
    redis.call('XADD', KEYS[1], '*', 'request', ARGV[1])
    redis.call('SET', KEYS[2], ARGV[1])
    return ARGV[2]
    """
    return client.eval(
        enqueue_once,
        2,
        stream_key(payload["scope"]),
        pending_key(payload["scope"], payload["session_id"], payload["instrument_id"]),
        serialized,
        payload["request_id"],
    )


def get_pending_request(scope, session_id, instrument_id):
    raw = _redis().get(pending_key(scope, session_id, instrument_id))
    return json.loads(raw) if raw else None


def _clear_pending_request(client, payload):
    clear_if_same = """
    local raw = redis.call('GET', KEYS[1])
    if not raw then return 0 end
    if cjson.decode(raw).request_id == ARGV[1] then
      return redis.call('DEL', KEYS[1])
    end
    return 0
    """
    return client.eval(
        clear_if_same,
        1,
        pending_key(payload["scope"], payload["session_id"], payload["instrument_id"]),
        payload["request_id"],
    )


def consume_orders(scope, handler, stop_event=None, after_durable=None):
    """Read and reclaim requests; ack only after the handler durably records outcome."""
    client = _redis()
    key = stream_key(scope)
    consumer = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    try:
        client.xgroup_create(key, GROUP, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise

    last_claim = 0.0
    while not (stop_event and stop_event.is_set()):
        now = time.monotonic()
        if now - last_claim >= 5:
            last_claim = now
            try:
                claim = client.xautoclaim(key, GROUP, consumer, CLAIM_IDLE_MS, "0-0", count=20)
                entries = claim[1] if claim else []
                if entries:
                    _handle_entries(client, key, entries, handler, after_durable)
            except Exception:
                logger.exception("Could not reclaim pending %s order requests", scope)

        try:
            batches = client.xreadgroup(GROUP, consumer, {key: ">"}, count=20, block=BLOCK_MS)
            for _, entries in batches:
                _handle_entries(client, key, entries, handler, after_durable)
        except Exception:
            logger.exception("Redis order stream read failed for %s; retrying", scope)
            time.sleep(1)


def _handle_entries(client, key, entries, handler, after_durable=None):
    from django.db import close_old_connections
    for message_id, fields in entries:
        try:
            close_old_connections()
            payload = json.loads(fields["request"])
            handler(payload)
            _clear_pending_request(client, payload)
            if after_durable:
                after_durable(payload)
        except Exception:
            logger.exception("Order request %s failed; leaving it pending for recovery", message_id)
            continue
        finally:
            close_old_connections()
        client.xack(key, GROUP, message_id)
