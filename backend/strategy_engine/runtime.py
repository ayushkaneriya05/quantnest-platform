"""
Strategy Runtime State — shared low-latency state for live/paper execution.

Key design decisions:
- Uses the Redis-backed unified state store for process-independent access
- Updates are protected by shared-state locks
- State is rebuilt from the database only when the shared projection is missing
- Only intra-session mutable fields (trailing stop, peak price, phase) stored here
- Avoids hot DB writes during tick evaluation
"""
import logging
from django.utils import timezone

from common.enums import TradePhase
from rules_engine.utils import compute_sl_distance_from_config, derive_protection_levels
from core.cache_api import cache_api

logger = logging.getLogger(__name__)


class StrategyRuntimeState:
    """
    In-memory runtime state for strategy execution using unified cache.

    Redis is the shared execution projection; the database remains the durable
    source of truth and startup recovery source.
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
        from django.db import transaction
        transaction.on_commit(
            lambda: cache_api.update_runtime_state(scope, session_id, instrument_id, updates)
        )

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
    def reconcile_trade_state(cls, scope, session_id, instrument_id, config=None, failed_reason=None):
        """Rebuild one trade phase from durable active orders and positions."""
        from common.enums import OrderStatus

        session_id = str(session_id)
        active_statuses = (OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL, "UNKNOWN")
        if scope == "live":
            from live_trading.models import LiveOrder, LivePosition, TradingSession

            session = TradingSession.objects.select_related("allocation").get(pk=session_id)
            order_scope = LiveOrder.objects.filter(session=session)
            position_scope = LivePosition.objects.filter(allocation=session.allocation, quantity__gt=0)
        else:
            from paper_trading.models import PaperOrder, PaperPosition, PaperTradingSession

            session = PaperTradingSession.objects.select_related("account").get(pk=session_id)
            order_scope = PaperOrder.objects.filter(account=session.account, strategy=session.strategy)
            position_scope = PaperPosition.objects.filter(account=session.account, strategy=session.strategy, quantity__gt=0)

        active_orders = list(order_scope.filter(instrument_id=instrument_id, status__in=active_statuses))
        positions = list(position_scope.filter(instrument_id=instrument_id).select_related("instrument"))
        if active_orders:
            position_sides = {position.side for position in positions}
            has_exit = any(order.side not in position_sides for order in active_orders) and bool(position_sides)
            has_partial_fill = any(int(order.filled_quantity or 0) > 0 for order in active_orders)
            phase = cls.PARTIAL_EXIT_PENDING if has_exit and has_partial_fill else (cls.EXIT_PENDING if has_exit else cls.ENTRY_PENDING)
            state_updates = {
                "phase": phase,
                "side": positions[0].side if positions else active_orders[0].side,
            }
            cls.update_trade_state(scope, session_id, instrument_id, state_updates)
            return phase

        # A queued request may outlive the worker that published it but not yet
        # have a durable order row. Preserve its pending phase during recovery.
        from strategy_engine.order_queue import get_pending_request
        pending_request = get_pending_request(scope, session_id, instrument_id)
        if pending_request:
            position_sides = {position.side for position in positions}
            request_side = pending_request.get("side")
            is_exit = bool(position_sides) and request_side not in position_sides
            phase = cls.EXIT_PENDING if is_exit else cls.ENTRY_PENDING
            cls.update_trade_state(
                scope,
                session_id,
                instrument_id,
                {"phase": phase, "side": positions[0].side if positions else request_side},
            )
            return phase

        if positions:
            position = max(positions, key=lambda item: item.last_updated)
            same_side_positions = [item for item in positions if item.side == position.side]
            quantity = sum(int(item.quantity) for item in same_side_positions)
            avg_price = sum(float(item.avg_price) * int(item.quantity) for item in same_side_positions) / quantity
            execution_id = position.instrument_id
            if scope == "live":
                deployed = getattr(getattr(session, "allocation", None), "deployed_version", None)
            else:
                deployed = getattr(getattr(getattr(session, "account", None), "allocation", None), "deployed_version", None)
            config = config or (deployed.config_snapshot if deployed else {})
            cls.mark_open(scope, session_id, instrument_id, position.side, quantity, avg_price, config=config, opened_at=position.opened_at, execution_instrument_id=execution_id)
            cls._clear_failed_partial_exit(scope, session_id, instrument_id, failed_reason)
            return cls.OPEN

        cls.mark_closed(scope, session_id, instrument_id)
        cls._clear_failed_partial_exit(scope, session_id, instrument_id, failed_reason)
        return cls.CLOSED

    @classmethod
    def _clear_failed_partial_exit(cls, scope, session_id, instrument_id, failed_reason):
        if not failed_reason:
            return
        reason = str(failed_reason).strip()
        if not reason.lower().startswith("partial exit"):
            return
        if ":" in reason:
            reason = reason.split(":", 1)[1].strip()
        if reason:
            cls.update_trade_state(scope, session_id, instrument_id, {f"partial_exit_{reason}": False})

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
        Resolves all critical fields from runtime_state first (shared state),
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
                session = TradingSession.objects.select_related("allocation__deployed_version").get(id=session_id)
                positions = LivePosition.objects.filter(
                    allocation=session.allocation,
                    quantity__gt=0
                ).select_related('instrument', 'allocation__deployed_version')
            else:
                from paper_trading.models import PaperPosition, PaperTradingSession
                session = PaperTradingSession.objects.select_related("account", "allocation__deployed_version").get(id=session_id)
                positions = PaperPosition.objects.filter(
                    account=session.account,
                    strategy=session.strategy,
                    quantity__gt=0
                ).select_related('instrument', 'account__allocation__deployed_version')
            
            instrument_ids = {position.instrument_id for position in positions}
            recovered_count = 0
            for instrument_id in instrument_ids:
                try:
                    cls.reconcile_trade_state(scope, session_id, instrument_id)
                    recovered_count += 1
                except Exception as e:
                    logger.error("Failed to rebuild runtime state for %s session %s instrument %s: %s", scope, session_id, instrument_id, e)

            logger.info(f"Rebuilt runtime state for {recovered_count} positions in {scope} session {session_id}")
            return recovered_count
            
        except Exception as e:
            logger.error(f"Failed to rebuild runtime state for {scope} session {session_id}: {e}")
            return 0

    @classmethod
    def rebuild_pending_order_state(cls, scope, session_id):
        """Recreate pending entry/exit phases after a worker restart."""
        from common.enums import OrderStatus, Side

        active_statuses = [OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL, "UNKNOWN"]
        if scope == "live":
            from live_trading.models import LiveOrder, LivePosition, TradingSession

            session = TradingSession.objects.get(id=session_id)
            orders = LiveOrder.objects.filter(session=session, status__in=active_statuses)
            position_query = LivePosition.objects.filter(allocation=session.allocation, quantity__gt=0)
        else:
            from paper_trading.models import PaperOrder, PaperPosition, PaperTradingSession

            session = PaperTradingSession.objects.get(id=session_id)
            orders = PaperOrder.objects.filter(account=session.account, strategy=session.strategy, status__in=active_statuses)
            position_query = PaperPosition.objects.filter(account=session.account, strategy=session.strategy, quantity__gt=0)

        positions = {(position.instrument_id, position.side): position for position in position_query}

        recovered = 0
        for order in orders.select_related("instrument"):
            matching_position = positions.get((order.instrument_id, order.side))
            opposite_side = Side.SELL if order.side == Side.BUY else Side.BUY
            opposite_position = positions.get((order.instrument_id, opposite_side))
            if opposite_position:
                phase = cls.PARTIAL_EXIT_PENDING if order.filled_quantity else cls.EXIT_PENDING
            elif matching_position:
                phase = cls.ENTRY_PENDING
            else:
                phase = cls.ENTRY_PENDING
            cls.update_trade_state(scope, str(session_id), order.instrument_id, {"phase": phase, "side": order.side})
            recovered += 1
        return recovered

    @classmethod
    def _rebuild_risk_metrics(cls, scope, session_id, current=None):
        """Recovery only: replay recorded closes in order using the deployed timezone."""
        from risk_management.metrics import empty_metrics, record_close, normalize_periods, RECENT_TRADE_LIMIT

        if scope == "live":
            from live_trading.models import LiveTrade, TradingSession
            session = TradingSession.objects.select_related("allocation__deployed_version").get(pk=session_id)
            trades = LiveTrade.objects.filter(allocation=session.allocation)
            pnl_field = "realized_pnl"
            capital = float(session.allocation.allocated_capital)
        else:
            from paper_trading.models import PaperTrade, PaperTradingSession
            session = PaperTradingSession.objects.select_related("account", "allocation__deployed_version").get(pk=session_id)
            trades = PaperTrade.objects.filter(account=session.account, strategy=session.strategy)
            pnl_field = "net_pnl"
            capital = float(session.account.initial_balance)

        from risk_management.auto_disable import AutoDisableGate
        config = AutoDisableGate.configuration(session)
        timezone_name = config["time_rule"].get("timezone", "Asia/Kolkata")
        now = timezone.now()
        rows = list(trades.filter(exit_time__isnull=False).order_by("exit_time", "pk").values(
            "id", pnl_field, "entry_time", "exit_time"))
        metrics = empty_metrics(capital, now, timezone_name)
        for row in rows:
            metrics = record_close(metrics, row[pnl_field] or 0, row["exit_time"], capital, timezone_name)
        metrics = normalize_periods(metrics, now, timezone_name)
        entry_times = [row["entry_time"] for row in rows if row["entry_time"]]
        previous_entry = (current or {}).get("last_entry_time")
        if isinstance(previous_entry, str):
            from datetime import datetime
            previous_entry = datetime.fromisoformat(previous_entry)
        if previous_entry:
            entry_times.append(previous_entry)
        metrics["last_entry_time"] = max(entry_times).isoformat() if entry_times else None
        metrics["recent_trade_ids"] = sorted(row["id"] for row in rows)[-RECENT_TRADE_LIMIT:]
        metrics["last_close_trade_id"] = rows[-1]["id"] if rows else None
        state = session.auto_disable_state
        metrics["auto_disable_release"] = state.get("release", {}) if state.get("version_id") == session.allocation.deployed_version_id else {}
        return metrics

    @classmethod
    def ensure_risk_metrics(cls, scope, session_id):
        """Initialize missing/incomplete projections outside tick evaluation."""
        from core.cache_view import cache_view
        from risk_management.metrics import metrics_complete

        session_id = str(session_id)
        if metrics_complete(cache_view.get_risk_metrics(scope, session_id)):
            return False
        rebuilt = False

        def restore(current):
            nonlocal rebuilt
            if metrics_complete(current):
                return None
            rebuilt = True
            return cls._rebuild_risk_metrics(scope, session_id, current)

        cache_api.mutate_risk_metrics(scope, session_id, restore)
        return rebuilt

    @classmethod
    def record_risk_close(cls, scope, session_id, trade_id, pnl, timestamp, capital, config):
        """After commit: update fresh counters once, serialized per execution session."""
        from datetime import datetime
        from risk_management.metrics import metrics_complete, record_close, RECENT_TRADE_LIMIT

        def update(current):
            # Recovery includes the newly committed trade. Do not increment it again.
            if not metrics_complete(current):
                return cls._rebuild_risk_metrics(scope, session_id, current)
            if trade_id in current.get("recent_trade_ids", []):
                return None
            previous_exit = current.get("last_exit_time")
            if isinstance(previous_exit, str):
                previous_exit = datetime.fromisoformat(previous_exit)
            previous_id = current.get("last_close_trade_id") or 0
            if previous_exit and (timestamp, trade_id) < (previous_exit, previous_id):
                # Reconciliation can deliver old closes after newer ones; replay
                # makes streaks and the realized-equity peak follow recorded time.
                return cls._rebuild_risk_metrics(scope, session_id, current)
            metrics = record_close(current, pnl, timestamp, capital, config["time_rule"].get("timezone", "Asia/Kolkata"))
            metrics["recent_trade_ids"] = (current.get("recent_trade_ids", []) + [trade_id])[-RECENT_TRADE_LIMIT:]
            metrics["last_close_trade_id"] = trade_id
            return metrics

        return cache_api.mutate_risk_metrics(scope, str(session_id), update)

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
