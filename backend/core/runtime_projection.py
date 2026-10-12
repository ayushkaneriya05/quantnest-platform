"""Atomic JSON state publication and per-session ordered lifecycle streams."""
import json
from core.redis import runtime_redis


def state_key(scope, session, instrument):
    return f"quantnest:runtime:{scope}:{session}:{instrument}"


def stream_key(scope, session):
    return f"quantnest:lifecycle:{scope}:{session}"


_UPDATE = """
local raw = redis.call('GET', KEYS[1])
local state = raw and cjson.decode(raw) or {}
local updates = cjson.decode(ARGV[1])
local committed = tonumber(ARGV[2])
if committed > 0 and committed <= tonumber(state._commit_revision or 0) then
  return cjson.encode(state)
end
if updates.entry_time and updates.entry_time ~= state.entry_time then
  state = {_version = state._version, _commit_revision = state._commit_revision}
end
if updates.entry_time and updates.entry_time == state.entry_time and state.protected_stop_price
   and state.protected_stop_price ~= cjson.null and updates.protected_stop_price
   and updates.protected_stop_price ~= cjson.null then
  local before = tonumber(state.protected_stop_price)
  local after = tonumber(updates.protected_stop_price)
  updates.protected_stop_price = state.side == 'BUY' and math.max(before, after) or math.min(before, after)
end
for key, value in pairs(updates) do state[key] = value end
state._version = redis.call('INCR', KEYS[4])
if committed > 0 then state._commit_revision = committed end
local encoded = cjson.encode(state)
redis.call('SET', KEYS[1], encoded)
redis.call('SADD', KEYS[3], ARGV[3])
redis.call('XADD', KEYS[2], '*', 'instrument_id', ARGV[3], 'state', encoded)
return encoded
"""


def update(scope, session, instrument, updates, committed_revision=0):
    client = runtime_redis()
    key = state_key(scope, session, instrument)
    value = client.eval(_UPDATE, 4, key, stream_key(scope, session),
                        f"quantnest:runtime-index:{scope}:{session}", f"{key}:revision",
                        json.dumps(updates, default=str), int(committed_revision), str(instrument))
    return json.loads(value)


def get(scope, session, instrument):
    raw = runtime_redis().get(state_key(scope, session, instrument))
    return json.loads(raw) if raw else {}


def checkpoint(scope, session, instrument, state, owner_key, owner_token):
    """Checkpoint hot state without allowing a late writer to replace a new trade."""
    fields = {key: value for key, value in state.items() if key in (
        "current_price", "peak_price", "trailing_stop", "protected_stop_price",
    ) or key.startswith(("breakeven_", "partial_exit_"))}
    runtime_redis().eval("""
    if redis.call('GET', KEYS[2]) ~= ARGV[1] then return 0 end
    local raw = redis.call('GET', KEYS[1])
    if not raw then return 0 end
    local state = cjson.decode(raw)
    local expected = cjson.decode(ARGV[2])
    if state.entry_time ~= expected.entry_time then return 0 end
    if tonumber(state.quantity or 0) <= 0 then return 0 end
    for key, value in pairs(expected.updates) do state[key] = value end
    redis.call('SET', KEYS[1], cjson.encode(state))
    return 1
    """, 2, state_key(scope, session, instrument), owner_key, owner_token,
        json.dumps({"entry_time": state.get("entry_time"), "updates": fields}, default=str))


def reset(scope, session):
    client = runtime_redis()
    index = f"quantnest:runtime-index:{scope}:{session}"
    instruments = client.smembers(index)
    keys = [state_key(scope, session, value) for value in instruments]
    if keys:
        client.delete(*keys)
    client.delete(index)


def snapshot(scope, session):
    client = runtime_redis()
    ids = client.smembers(f"quantnest:runtime-index:{scope}:{session}")
    if not ids:
        return {}
    return {int(key): json.loads(value) for key, value in
            zip(ids, client.mget([state_key(scope, session, value) for value in ids])) if value}
