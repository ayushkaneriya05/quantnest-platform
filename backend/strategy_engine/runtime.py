"""
Strategy Runtime State — In-memory ephemeral state for live/paper execution.

Key design decisions:
- Uses QuantNestUnifiedCache for O(1) in-memory access (microsecond latency)
- No distributed locking needed (single worker per session)
- State is ephemeral — rebuilt from database on restart
- Only intra-session mutable fields (trailing stop, peak price, phase) stored here
- Avoids hot DB writes during tick evaluation
"""
import logging

from common.enums import TradePhase
from rules_engine.utils import compute_sl_distance_from_config, derive_protection_levels
from core.cache_api import cache_api

logger = logging.getLogger(__name__)


class StrategyRuntimeState:
    """
    In-memory runtime state for strategy execution using unified cache.

    All state is ephemeral — it is rebuilt from the database on restart.
    Only intra-session mutable fields (trailing stop, peak price, phase)
    that are updated on every tick are stored here to avoid hot DB writes.
    """

    # Phase constants
    ENTRY_PENDING = TradePhase.ENTRY_PENDING
    OPEN = TradePhase.OPEN
    PARTIAL_EXIT_PENDING = TradePhase.PARTIAL_EXIT_PENDING
    EXIT_PENDING = TradePhase.EXIT_PENDING
    CLOSED = TradePhase.CLOSED

    # ------------------------------------------------------------------
    # Trade-scoped state (for session-instrument pairs)
    # ------------------------------------------------------------------

    @classmethod
    def trade_state(cls, scope, session_id, instrument_id):
        """Get trade state for a session-instrument pair."""
        from core.cache_view import cache_view
        return cache_view.get_runtime_state(scope, session_id, instrument_id)

    @classmethod
    def update_trade_state(cls, scope, session_id, instrument_id, updates):
        """Update trade state for a session-instrument pair."""
        cache_api.update_runtime_state(scope, session_id, instrument_id, updates)

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
        """
        Build enriched position state from runtime state and config.
        Resolves all critical fields from runtime_state first (unified cache),
        falling back to DB position object only if provided.
        """
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
    # Runtime state initialization and recovery
    # ------------------------------------------------------------------

    @classmethod
    def rebuild_runtime_state_from_db(cls, scope, session_id):
        """
        Rebuild runtime state from database positions for session recovery.
        
        Args:
            scope: Either "live" or "paper"
            session_id: Session identifier
            
        Returns:
            Number of positions recovered
        """
        try:
            if scope == "live":
                from live_trading.models import LivePosition, TradingSession
                session = TradingSession.objects.get(id=session_id)
                positions = LivePosition.objects.filter(
                    allocation=session.allocation,
                    quantity__gt=0
                ).select_related('instrument', 'allocation__deployed_version')
            else:
                from paper_trading.models import PaperPosition, PaperTradingSession
                session = PaperTradingSession.objects.get(id=session_id)
                positions = PaperPosition.objects.filter(
                    account=session.account,
                    strategy=session.strategy,
                    quantity__gt=0
                ).select_related('instrument', 'account__allocation__deployed_version')
            
            recovered_count = 0
            for position in positions:
                try:
                    # Get strategy config for protection levels
                    config = None
                    if scope == "live":
                        if position.allocation and position.allocation.deployed_version:
                            config = position.allocation.deployed_version.config_snapshot
                    else:
                        if position.account and position.account.allocation and position.account.allocation.deployed_version:
                            config = position.account.allocation.deployed_version.config_snapshot
                    
                    # Mark as open with current position state
                    cls.mark_open(
                        scope=scope,
                        session_id=str(session_id),
                        instrument_id=position.instrument.id,
                        side=position.side,
                        quantity=position.quantity,
                        avg_price=position.avg_price,
                        config=config,
                        opened_at=position.opened_at,
                        execution_instrument_id=position.instrument.id
                    )
                    recovered_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to rebuild runtime state for position {position.id}: {e}")
            
            logger.info(f"Rebuilt runtime state for {recovered_count} positions in {scope} session {session_id}")
            return recovered_count
            
        except Exception as e:
            logger.error(f"Failed to rebuild runtime state for {scope} session {session_id}: {e}")
            return 0

    # ------------------------------------------------------------------
    # User cleanup
    # ------------------------------------------------------------------

    @classmethod
    def clear_all_for_user(cls, user_id):
        """
        Remove all runtime state for a user's sessions.
        Used during account deactivation/deletion.
        """
        from live_trading.models import TradingSession
        from paper_trading.models import PaperTradingSession

        live_sessions = list(TradingSession.objects.filter(user_id=user_id).values_list('id', flat=True))
        paper_sessions = list(PaperTradingSession.objects.filter(user_id=user_id).values_list('id', flat=True))
        session_ids = [str(sid) for sid in live_sessions + paper_sessions]

        if not session_ids:
            return

        # Clear all session data from unified cache
        for session_id in live_sessions:
            cache_api.clear_session("live", str(session_id))
        for session_id in paper_sessions:
            cache_api.clear_session("paper", str(session_id))
