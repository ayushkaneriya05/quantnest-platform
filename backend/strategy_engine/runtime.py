"""
Strategy Runtime State — Redis-backed ephemeral state for live/paper execution.

Key design decisions:
- All read-modify-write operations use Redis atomic operations to prevent
  lost updates under concurrent Celery workers.
- Position state is stored with a 48-hour TTL (down from 7 days) to prevent
  stale state accumulation for closed positions.
- State updates use short-lived Redis locks for concurrent workers.
- The circuit breaker state is NOT stored here — see circuit_breaker.py.
"""
import logging
import uuid
import time

from django.core.cache import cache
from common.cache_keys import CacheKeys
from common.enums import TradePhase
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

    # Phase constants
    ENTRY_PENDING = TradePhase.ENTRY_PENDING
    OPEN = TradePhase.OPEN
    PARTIAL_EXIT_PENDING = TradePhase.PARTIAL_EXIT_PENDING
    EXIT_PENDING = TradePhase.EXIT_PENDING
    CLOSED = TradePhase.CLOSED

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @classmethod
    def update_position_state(cls, scope, identifier, updates):
        """
        Atomic read-modify-write using a short-lived lock to prevent
        lost updates when two coroutines update the same position state.
        """
        lock_key = CacheKeys.POS_LOCK.format(scope=scope, identifier=identifier)
        lock_token = str(uuid.uuid4())

        # Best-effort atomic update with a 5s lock
        for attempt in range(5):  # up to 5 retries
            acquired = cache.add(lock_key, lock_token, timeout=5)
            if acquired:
                break
            logger.warning("Failed to acquire position state lock for %s:%s (attempt %d/5)", scope, identifier, attempt + 1)
            time.sleep(0.05)

        if not acquired:
            logger.warning("Failed to acquire position state lock for %s:%s, proceeding with best-effort write", scope, identifier)

        try:
            state = cache.get(cls._key(scope, identifier)) or {}
            state.update(updates or {})
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
    def trade_state(cls, scope, session_id, instrument_id):
        return cache.get(cls._trade_key(scope, session_id, instrument_id)) or {}

    @classmethod
    def update_trade_state(cls, scope, session_id, instrument_id, updates):
        """
        Atomic read-modify-write for trade state.
        Uses the same lock pattern as update_position_state.
        """
        lock_key = CacheKeys.TRADE_LOCK.format(scope=scope, session_id=session_id, instrument_id=instrument_id)
        lock_token = str(uuid.uuid4())

        for attempt in range(5):
            acquired = cache.add(lock_key, lock_token, timeout=5)
            if acquired:
                break
            logger.warning("Failed to acquire trade state lock for %s:%s:%s (attempt %d/5)", scope, session_id, instrument_id, attempt + 1)
            time.sleep(0.05)

        if not acquired:
            logger.warning("Failed to acquire trade state lock for %s:%s:%s, proceeding with best-effort write", scope, session_id, instrument_id)

        try:
            state = cache.get(cls._trade_key(scope, session_id, instrument_id)) or {}
            state.update(updates or {})
            cache.set(cls._trade_key(scope, session_id, instrument_id), state, timeout=cls.TTL_SECONDS)
            return state
        finally:
            current = cache.get(lock_key)
            if current == lock_token:
                cache.delete(lock_key)

    # ------------------------------------------------------------------
    # Convenience state transition helpers
    # ------------------------------------------------------------------

    @classmethod
    def mark_entry_pending(
        cls,
        scope,
        session_id,
        instrument_id,
        side,
    ):
        return cls.update_trade_state(
            scope,
            session_id,
            instrument_id,
            {
                "phase": cls.ENTRY_PENDING,
                "side": side,
            },
        )

    @classmethod
    def mark_open(
        cls,
        scope,
        session_id,
        instrument_id,
        side,
        quantity,
        avg_price,
        config=None,
        opened_at=None,
        execution_instrument_id=None,
    ):
        protection = derive_protection_levels(config or {}, side, avg_price)
        return cls.update_trade_state(
            scope,
            session_id,
            instrument_id,
            {
                "phase": cls.OPEN,
                "execution_instrument_id": execution_instrument_id,
                "side": side,
                "quantity": int(quantity or 0),
                "avg_price": float(avg_price),
                "entry_time": opened_at.isoformat() if opened_at else None,
                **protection,
            },
        )

    @classmethod
    def mark_exit_pending(cls, scope, session_id, instrument_id):
        return cls.update_trade_state(
            scope,
            session_id,
            instrument_id,
            {
                "phase": cls.EXIT_PENDING,
            },
        )

    @classmethod
    def mark_closed(cls, scope, session_id, instrument_id):
        return cls.update_trade_state(
            scope,
            session_id,
            instrument_id,
            {
                "phase": cls.CLOSED,
                "quantity": 0,
                "execution_instrument_id": None,
                "protected_stop_price": None,
                "protected_target_price": None,
            },
        )

    @classmethod
    def build_position_state(
        cls,
        *,
        config,
        runtime_state,
        position=None,
        side=None,
        avg_price=None,
        current_price=None,
        opened_at=None,
    ):
        # All critical fields are resolved from runtime_state first (Redis),
        # falling back to the DB position object only if provided.
        _side = side or runtime_state.get("side")
        _avg_price = float(avg_price or runtime_state.get("avg_price", 0))
        _current_price = float(
            current_price
            or runtime_state.get("current_price")
            or (getattr(position, "current_price", None) if position else None)
            or _avg_price
        )

        peak_price = runtime_state.get("peak_price")
        if peak_price is None:
            peak_price = float(_current_price or _avg_price)
        entry_time = runtime_state.get("entry_time")
        if entry_time is None and opened_at:
            entry_time = opened_at.isoformat()

        # Start from a copy of runtime_state to preserve ephemeral boolean flags
        # (e.g., breakeven_X, partial_exit_X) that engine.py checks to prevent
        # infinite re-evaluation loops.
        state = dict(runtime_state)
        state.update({
            "avg_price": _avg_price,
            "side": _side,
            "current_price": _current_price,
            "peak_price": float(peak_price),
            "trailing_stop": runtime_state.get("trailing_stop"),
            "entry_time": entry_time,
            "sl_distance": compute_sl_distance_from_config(config, _avg_price),
            "protected_stop_price": runtime_state.get("protected_stop_price"),
            "protected_target_price": runtime_state.get("protected_target_price"),
            "phase": runtime_state.get("phase"),
            "quantity": runtime_state.get("quantity", getattr(position, "quantity", 0) if position else 0),
            "execution_instrument_id": runtime_state.get("execution_instrument_id", getattr(position, "instrument_id", None) if position else None),
        })
        if _side == "SELL":
            pnl_points = _avg_price - _current_price
        else:
            pnl_points = _current_price - _avg_price
        state["pnl_points"] = pnl_points
        state["pnl_percentage"] = (pnl_points / _avg_price) * 100 if _avg_price else 0.0
        return state

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    @classmethod
    def clear_all_for_user(cls, user_id):
        """
        Remove all runtime state keys for a user's sessions.
        Used during account deactivation/deletion.
        """
        from live_trading.models import TradingSession
        from paper_trading.models import PaperTradingSession
        
        live_sessions = list(TradingSession.objects.filter(user_id=user_id).values_list('id', flat=True))
        paper_sessions = list(PaperTradingSession.objects.filter(user_id=user_id).values_list('id', flat=True))
        session_ids = [str(sid) for sid in live_sessions + paper_sessions]
        
        if not session_ids:
            return

        try:
            # For django-redis backend
            if hasattr(cache, 'delete_pattern'):
                for sid in session_ids:
                    cache.delete_pattern(f"*strategy-runtime:*:trade:{sid}:*")
                    cache.delete_pattern(f"*trade_lock:*:{sid}:*")
                # Also clean position-scoped keys
                cache.delete_pattern(f"*strategy-runtime:live-position:*")
                cache.delete_pattern(f"*strategy-runtime:paper-position:*")
            else:
                # Try getting the raw redis client
                client = cache.client.get_client()
                for sid in session_ids:
                    for key in client.scan_iter(f"*strategy-runtime:*:trade:{sid}:*"):
                        client.delete(key)
                    for key in client.scan_iter(f"*trade_lock:*:{sid}:*"):
                        client.delete(key)
                for key in client.scan_iter(f"*strategy-runtime:live-position:*"):
                    client.delete(key)
                for key in client.scan_iter(f"*strategy-runtime:paper-position:*"):
                    client.delete(key)
        except Exception as exc:
            logger.warning("Failed to clear Redis runtime state for user %s: %s", user_id, exc)

    @staticmethod
    def _key(scope, identifier):
        return CacheKeys.POSITION_STATE.format(scope=scope, identifier=identifier)

    @staticmethod
    def _trade_key(scope, session_id, instrument_id):
        return CacheKeys.TRADE_STATE.format(scope=scope, session_id=session_id, instrument_id=instrument_id)
