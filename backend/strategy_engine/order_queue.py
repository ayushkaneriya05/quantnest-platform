"""Durable, scope-isolated order transport backed by Redis Streams."""
import json
import logging
import os
import socket
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings

logger = logging.getLogger(__name__)

GROUP = "execution"
CLAIM_IDLE_MS = 30_000


def _redis():
    from core.redis import runtime_redis
    return runtime_redis()


def stream_key(scope, account_key):
    from quantnest_runtime.ownership import partition
    shard = partition(account_key, settings.ORDER_PARTITIONS)
    return f"quantnest:orders:{str(scope).lower()}:{shard}"


def validate_request(data):
    if data.get("expires_at") and data["intent"] == "ENTRY" and time.time() > float(data["expires_at"]):
        raise ValueError("Signal deadline expired")
    if not data.get("owner_key") or _redis().get(data["owner_key"]) != data.get("owner_token"):
        raise ValueError("Execution ownership is no longer valid")



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
    from core.runtime_projection import state_key
    serialized = json.dumps(payload, separators=(",", ":"))
    enqueue_once = """
    local pending = redis.call('GET', KEYS[2])
    if pending then
      return cjson.decode(pending).request_id
    end
    local request = cjson.decode(ARGV[1])
    if redis.call('GET', KEYS[4]) ~= request.owner_token then
      return redis.error_reply('Execution ownership was lost before publication')
    end
    local raw = redis.call('GET', KEYS[3])
    local state = raw and cjson.decode(raw) or {}
    if request.intent == 'EXIT' and state.entry_time ~= request.entry_time then
      return redis.error_reply('Position changed before exit publication')
    end
    for key, value in pairs(request.state_updates or {}) do state[key] = value end
    state.phase = request.intent == 'ENTRY' and 'ENTRY_PENDING' or 'EXIT_PENDING'
    state.pending_request_id = request.request_id
    redis.call('SET', KEYS[3], cjson.encode(state))
    redis.call('XADD', KEYS[1], '*', 'request', ARGV[1])
    redis.call('SET', KEYS[2], ARGV[1])
    return ARGV[2]
    """
    return client.eval(
        enqueue_once,
        4,
        stream_key(payload["scope"], payload["account_key"]),
        pending_key(payload["scope"], payload["session_id"], payload["instrument_id"]),
        state_key(str(payload["scope"]).lower(), payload["session_id"], payload["instrument_id"]),
        payload["owner_key"],
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


def consume_orders(scope, handler, stop_event=None, after_durable=None, worker_index=0):
    """Read and reclaim requests; ack only after the handler durably records outcome."""
    client = _redis()
    from quantnest_runtime.ownership import Lease
    total = settings.ORDER_WORKERS * settings.EXECUTION_NODE_COUNT
    global_index = settings.EXECUTION_NODE_INDEX * settings.ORDER_WORKERS + worker_index
    keys = [f"quantnest:orders:{str(scope).lower()}:{index}" for index in range(settings.ORDER_PARTITIONS) if index % total == global_index]
    leases = [Lease(f"gateway:{scope}:{key.rsplit(':', 1)[-1]}") for key in keys]
    held = []
    for lease in leases:
        if not lease.acquire():
            for previous in held:
                previous.release()
            raise RuntimeError("Order gateway partition is already owned")
        held.append(lease)
    consumer = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    for key in keys:
        try:
            client.xgroup_create(key, GROUP, id="0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise
    ownership_lost = __import__("threading").Event()
    def renew():
        while not (stop_event and stop_event.is_set()) and not ownership_lost.wait(3):
            try:
                if not all(lease.renew() for lease in leases):
                    ownership_lost.set()
            except Exception:
                ownership_lost.set()
    __import__("threading").Thread(target=renew, name=f"gateway-lease-{scope}", daemon=True).start()
    last_claim = 0.0
    claim_cursors = {key: "0-0" for key in keys}
    backlog, queued, active_accounts, futures = deque(), set(), set(), {}
    pool = ThreadPoolExecutor(max_workers=settings.ORDER_CONCURRENCY, thread_name_prefix=f"gateway-{scope}")

    def accept(key, entries):
        for identity, fields in entries:
            item_key = key, identity
            if item_key in queued:
                continue
            if len(backlog) >= 256:
                return  # The unacknowledged stream item remains recoverable.
            payload = json.loads(fields["request"])
            queued.add(item_key)
            backlog.append((key, identity, fields, payload.get("account_key", payload["session_id"])))
    try:
        while not (stop_event and stop_event.is_set()) and not ownership_lost.is_set():
            for future, (account, key, identity, started) in list(futures.items()):
                if time.monotonic() - started > settings.ORDER_TASK_TIMEOUT:
                    raise TimeoutError("Gateway deadline exceeded; supervisor must recover durable outcomes")
                if future.done():
                    future.result()
                    active_accounts.discard(account)
                    queued.discard((key, identity))
                    del futures[future]
            for _ in range(len(backlog)):
                if len(futures) >= settings.ORDER_CONCURRENCY:
                    break
                key, identity, fields, account = backlog.popleft()
                if account in active_accounts:
                    backlog.append((key, identity, fields, account))
                    continue
                active_accounts.add(account)
                future = pool.submit(_handle_entries, client, key, [(identity, fields)], handler, after_durable)
                futures[future] = account, key, identity, time.monotonic()
            now = time.monotonic()
            if now - last_claim >= 5 and len(backlog) < 128:
                last_claim = now
                for key in keys:
                    claim = client.xautoclaim(key, GROUP, consumer, CLAIM_IDLE_MS, claim_cursors[key], count=20)
                    if claim:
                        claim_cursors[key] = claim[0]
                    if claim and claim[1]:
                        accept(key, claim[1])
            if len(backlog) < 128:
                batches = client.xreadgroup(GROUP, consumer, {key: ">" for key in keys}, count=20, block=50)
                for key, entries in batches:
                    accept(key, entries)
            else:
                ownership_lost.wait(0.01)
        if ownership_lost.is_set():
            raise RuntimeError("Order gateway ownership lost")
    finally:
        ownership_lost.set()
        pool.shutdown(wait=False, cancel_futures=True)
        for lease in leases:
            lease.release()


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
        client.xdel(key, message_id)
