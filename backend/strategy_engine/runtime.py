"""
Strategy Runtime State — Redis-backed ephemeral state for live/paper execution.

Key design decisions:
- All read-modify-write operations use Redis atomic operations to prevent
  lost updates under concurrent Celery workers.
- Position state is stored with a 48-hour TTL (down from 7 days) to prevent
  stale state accumulation for closed positions.
- Distributed lock helpers are provided for critical sections (entry/exit).
- The circuit breaker state is NOT stored here — see circuit_breaker.py.
"""
import logging
import uuid
from contextlib import contextmanager

from django.core.cache import cache

from rules_engine.utils import compute_sl_distance_from_config, derive_protection_levels

logger = logging.getLogger(__name__)


class StrategyRuntimeState:
    """
    Redis-backed runtime state for strategy execution.

    All state is ephemeral — it is rebuilt from the database on restart.
    Only intra-session mutable fields (trailing stop, peak price, phase)
    that are updated on every tick are stored here to avoid hot DB writes.
    """

    # Reduce from 7 days → 48 hours.  Closed positions' state expires
    # naturally, preventing unbounded Redis memory growth.
    TTL_SECONDS = 60 * 60 * 48

    # Distributed lock TTL: maximum time a single tick is allowed to hold
    # the entry/exit lock before Redis auto-expires it (safety net).
    LOCK_TTL_SECONDS = 10

    # Phase constants
    FLAT = "FLAT"
    ENTRY_PENDING = "ENTRY_PENDING"
    OPEN = "OPEN"
    EXIT_PENDING = "EXIT_PENDING"
    CLOSED = "CLOSED"

    # ------------------------------------------------------------------
    # Distributed Locking
    # ------------------------------------------------------------------

    @classmethod
    @contextmanager
    def execution_lock(cls, scope: str, strategy_id, instrument_id, blocking_timeout: float = 2.0):
        """
        Acquire a Redis-backed distributed lock for (scope, strategy, instrument).

        This prevents two concurrent Celery workers from both entering / exiting
        the same position simultaneously (race condition fix).

        Usage::

            with StrategyRuntimeState.execution_lock("paper", strategy_id, instrument_id):
                # safe to read-modify-write trade state here
                trade_state = StrategyRuntimeState.trade_state(...)
                ...

        Raises ``RuntimeError`` if the lock cannot be acquired within
        ``blocking_timeout`` seconds (tick is skipped rather than double-executing).
        """
        lock_key = f"exec_lock:{scope}:{strategy_id}:{instrument_id}"
        # Use a random token so only the lock owner can release it
        lock_token = str(uuid.uuid4())

        # SETNX + EXPIRE is atomic via cache.add
        acquired = cache.add(lock_key, lock_token, timeout=cls.LOCK_TTL_SECONDS)
        
        if not acquired:
            # Try once more after a short wait (covers transient contention)
            import time
            time.sleep(0.05)
            acquired = cache.add(lock_key, lock_token, timeout=cls.LOCK_TTL_SECONDS)

        if not acquired:
            raise RuntimeError(
                f"Could not acquire execution lock for {scope}:{strategy_id}:{instrument_id} "
                f"within {blocking_timeout}s. Skipping tick to prevent duplicate execution."
            )

        try:
            yield
        finally:
            # Only delete if we still own the lock (compare-and-delete)
            current = cache.get(lock_key)
            if current == lock_token:
                cache.delete(lock_key)

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @classmethod
    def position_state(cls, scope, identifier):
        return cache.get(cls._key(scope, identifier)) or {}

    @classmethod
    def update_position_state(cls, scope, identifier, updates):
        """
        Atomic read-modify-write using a short-lived lock to prevent
        lost updates when two coroutines update the same position state.
        """
        lock_key = f"pos_lock:{scope}:{identifier}"
        lock_token = str(uuid.uuid4())

        # Best-effort atomic update with a 5s lock
        for _ in range(3):  # up to 3 retries
            acquired = cache.add(lock_key, lock_token, timeout=5)
            if acquired:
                break
            import time
            time.sleep(0.02)

        try:
            state = cache.get(cls._key(scope, identifier)) or {}
            state.update({k: v for k, v in (updates or {}).items() if v is not None})
            cache.set(cls._key(scope, identifier), state, timeout=cls.TTL_SECONDS)
            return state
        finally:
            current = cache.get(lock_key)
            if current == lock_token:
                cache.delete(lock_key)

    @classmethod
    def clear_position_state(cls, scope, identifier):
        cache.delete(cls._key(scope, identifier))

    @classmethod
    def trade_state(cls, scope, strategy_id, instrument_id):
        return cache.get(cls._trade_key(scope, strategy_id, instrument_id)) or {}

    @classmethod
    def update_trade_state(cls, scope, strategy_id, instrument_id, updates):
        """
        Atomic read-modify-write for trade state.
        Uses the same lock pattern as update_position_state.
        """
        lock_key = f"trade_lock:{scope}:{strategy_id}:{instrument_id}"
        lock_token = str(uuid.uuid4())

        for _ in range(3):
            acquired = cache.add(lock_key, lock_token, timeout=5)
            if acquired:
                break
            import time
            time.sleep(0.02)

        try:
            state = cache.get(cls._trade_key(scope, strategy_id, instrument_id)) or {}
            state.update({k: v for k, v in (updates or {}).items() if v is not None})
            cache.set(cls._trade_key(scope, strategy_id, instrument_id), state, timeout=cls.TTL_SECONDS)
            return state
        finally:
            current = cache.get(lock_key)
            if current == lock_token:
                cache.delete(lock_key)

    @classmethod
    def clear_trade_state(cls, scope, strategy_id, instrument_id):
        cache.delete(cls._trade_key(scope, strategy_id, instrument_id))

    # ------------------------------------------------------------------
    # Convenience state transition helpers
    # ------------------------------------------------------------------

    @classmethod
    def mark_entry_pending(
        cls,
        scope,
        strategy_id,
        instrument_id,
        *,
        side,
        order_id=None,
        order_type=None,
        requested_price=None,
        trigger_price=None,
    ):
        return cls.update_trade_state(
            scope,
            strategy_id,
            instrument_id,
            {
                "phase": cls.ENTRY_PENDING,
                "side": side,
                "entry_order_id": order_id,
                "entry_order_type": order_type,
                "requested_entry_price": requested_price,
                "entry_trigger_price": trigger_price,
                "exit_order_id": None,
                "last_exit_reason": None,
            },
        )

    @classmethod
    def mark_open(
        cls,
        scope,
        strategy_id,
        instrument_id,
        *,
        position_id=None,
        side,
        quantity,
        avg_price,
        config=None,
        opened_at=None,
    ):
        protection = derive_protection_levels(config or {}, side, avg_price)
        return cls.update_trade_state(
            scope,
            strategy_id,
            instrument_id,
            {
                "phase": cls.OPEN,
                "position_id": position_id,
                "side": side,
                "quantity": int(quantity or 0),
                "avg_price": float(avg_price),
                "entry_time": opened_at.isoformat() if opened_at else None,
                **protection,
                "exit_order_id": None,
            },
        )

    @classmethod
    def mark_exit_pending(cls, scope, strategy_id, instrument_id, *, order_id=None, reason=None):
        return cls.update_trade_state(
            scope,
            strategy_id,
            instrument_id,
            {
                "phase": cls.EXIT_PENDING,
                "exit_order_id": order_id,
                "last_exit_reason": reason,
            },
        )

    @classmethod
    def mark_closed(cls, scope, strategy_id, instrument_id, *, reason=None):
        return cls.update_trade_state(
            scope,
            strategy_id,
            instrument_id,
            {
                "phase": cls.CLOSED,
                "quantity": 0,
                "position_id": None,
                "exit_order_id": None,
                "protected_stop_price": None,
                "protected_target_price": None,
                "last_exit_reason": reason,
            },
        )

    @classmethod
    def build_position_state(
        cls,
        *,
        config,
        position,
        side,
        avg_price,
        current_price=None,
        opened_at=None,
        identifier=None,
        scope="position",
    ):
        runtime_state = cls.position_state(scope, identifier) if identifier is not None else {}
        peak_price = runtime_state.get("peak_price")
        if peak_price is None:
            peak_price = float(current_price or avg_price)
        entry_time = runtime_state.get("entry_time")
        if entry_time is None and opened_at:
            entry_time = opened_at.isoformat()

        return {
            "avg_price": float(avg_price),
            "side": side,
            "peak_price": float(peak_price),
            "trailing_stop": runtime_state.get("trailing_stop"),
            "entry_time": entry_time,
            "sl_distance": compute_sl_distance_from_config(config, avg_price),
            "protected_stop_price": runtime_state.get("protected_stop_price"),
            "protected_target_price": runtime_state.get("protected_target_price"),
            "trade_phase": runtime_state.get("phase"),
        }

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    @classmethod
    def clear_all_for_user(cls, user_id):
        """
        Remove all runtime state keys for a user's strategies.
        Used during account deactivation/deletion.
        """
        from strategies.models import Strategy
        strategy_ids = Strategy.objects.filter(user_id=user_id).values_list('id', flat=True)
        if not strategy_ids:
            return

        try:
            # For django-redis backend
            if hasattr(cache, 'delete_pattern'):
                for sid in strategy_ids:
                    cache.delete_pattern(f"*strategy-runtime:*:{sid}:*")
                    cache.delete_pattern(f"*exec_lock:*:{sid}:*")
            else:
                # Try getting the raw redis client
                client = cache.client.get_client()
                for sid in strategy_ids:
                    for key in client.scan_iter(f"*strategy-runtime:*:{sid}:*"):
                        client.delete(key)
                    for key in client.scan_iter(f"*exec_lock:*:{sid}:*"):
                        client.delete(key)
        except Exception as exc:
            logger.warning("Failed to clear Redis runtime state for user %s: %s", user_id, exc)

    @staticmethod
    def _key(scope, identifier):
        return f"strategy-runtime:{scope}:{identifier}"

    @staticmethod
    def _trade_key(scope, strategy_id, instrument_id):
        return f"strategy-runtime:{scope}:trade:{strategy_id}:{instrument_id}"
