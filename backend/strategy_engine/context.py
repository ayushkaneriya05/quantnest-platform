import threading
import time
from copy import deepcopy
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from strategy_engine.runtime import StrategyRuntimeState
from core.shared_state_store import shared_state_store

class SessionContext(ABC):
    """
    Abstract interface for execution contexts (Live vs Paper).
    Provides identical access to position states, capital, and risk stats
    regardless of whether the underlying data comes from a DB or a Broker.

    CRITICAL: All methods called during tick evaluation (get_position,
    get_risk_stats, get_runtime_state, update_runtime_state) MUST be
    DB-free. Runtime state uses a worker-local L1 cache for hot reads and
    Redis for lifecycle synchronization.
    """
    _HOT_FIELDS = {
        "current_price",
        "peak_price",
        "trailing_stop",
        "pnl_points",
        "pnl_percentage",
    }
    def __init__(self, session_id: str, strategy_id: str, scope: str):
        self.session_id = session_id
        self.strategy_id = strategy_id
        self.scope = scope
        self.user_id = self._fetch_user_id()
        self.ownership = {}
        self._runtime_l1: Dict[int, Dict[str, Any]] = {}
        self._runtime_l1_lock = threading.RLock()
        self._execution_context_lock = threading.Lock()
        self._cached_capital = 0.0
        self._cached_risk_stats: Dict[str, Any] = {}
        self._execution_context_updated = 0.0

    def refresh_execution_context(self):
        """Refresh slow-changing funds and risk inputs outside signal evaluation."""
        funds = shared_state_store.get_session_funds(self.scope, self.session_id)
        risk = shared_state_store.get_risk_metrics(self.scope, self.session_id) or {}
        from risk_management.metrics import metrics_complete
        if not metrics_complete(risk):
            StrategyRuntimeState.ensure_risk_metrics(self.scope, self.session_id)
            risk = shared_state_store.get_risk_metrics(self.scope, self.session_id)
        capital = 0.0
        if funds:
            available = next((funds[key] for key in ("available_margin", "cash_balance", "net_equity")
                              if funds.get(key) is not None), 0)
            if self.scope == "live":
                allocation = funds.get("allocation_available_capital")
                capital = min(float(allocation or 0), float(available or 0))
            else:
                capital = float(available or 0)
        with self._execution_context_lock:
            self._cached_capital = capital
            self._cached_risk_stats = dict(risk)
            self._execution_context_updated = time.monotonic()

    @abstractmethod
    def _fetch_user_id(self) -> str:
        """Fetch the associated user ID for the session.  Called once at init (DB is OK here)."""
        pass

    def get_available_capital(self) -> float:
        """Read refreshed local capital; stale inputs block new entries."""
        with self._execution_context_lock:
            if time.monotonic() - self._execution_context_updated > 5:
                return 0.0
            return self._cached_capital

    def get_risk_stats(self) -> Dict[str, Any]:
        """Read refreshed local risk inputs without cache or database I/O."""
        with self._execution_context_lock:
            if time.monotonic() - self._execution_context_updated > 5:
                return {}
            return dict(self._cached_risk_stats)

    def get_risk_evaluator(self) -> Any:
        """Returns a RiskEvaluator initialized with the available capital."""
        from risk_management.evaluator import RiskEvaluator
        return RiskEvaluator(self.get_available_capital())

    def get_runtime_state(self, instrument_id: int) -> Dict[str, Any]:
        """Read worker-local state; fetch the Redis projection only on first use."""
        with self._runtime_l1_lock:
            local_state = self._runtime_l1.get(instrument_id)
            if local_state is None:
                shared_state = StrategyRuntimeState.trade_state(self.scope, self.session_id, instrument_id)
                local_state = shared_state or {}
                self._runtime_l1[instrument_id] = local_state

            return deepcopy(local_state or {})

    def update_runtime_state(self, instrument_id: int, updates: Dict[str, Any]):
        """Update worker-local state; background publication owns persistence."""
        with self._runtime_l1_lock:
            state = self._runtime_l1.setdefault(instrument_id, {})
            state.update(updates)

        # The owning actor applies decisions locally. The order publisher and
        # financial outbox publish lifecycle transitions outside evaluation.

    def apply_external_runtime_state(self, instrument_id: int, updates: Dict[str, Any]):
        """Apply a newer event and report whether calculations must be invalidated."""
        with self._runtime_l1_lock:
            state = self._runtime_l1.setdefault(instrument_id, {})
            if updates.get("_version", 0) <= state.get("_version", -1):
                return False
            pending_id = state.get("pending_request_id")
            unsettled = pending_id and updates.get("settled_request_id") != pending_id
            pending = {"phase": state.get("phase"), "pending_request_id": pending_id} if unsettled else {}
            preserved = {key: value for key, value in state.items() if key in self._HOT_FIELDS}
            if updates.get("entry_time") != state.get("entry_time"):
                state.clear()
                preserved = {}
            elif state.get("protected_stop_price") is not None and updates.get("protected_stop_price") is not None:
                before, after = float(state["protected_stop_price"]), float(updates["protected_stop_price"])
                preserved["protected_stop_price"] = max(before, after) if state.get("side") == "BUY" else min(before, after)
            state.update(updates)
            state.update(preserved)
            state.update(pending)
            return True

    def get_position(self, instrument_id: int, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Returns the current open position state, or None if flat.

        DB-free: Reads exclusively from the shared Redis runtime state written
        by mark_open() during order fills.  When ``config`` is provided (slow
        path), build_position_state enriches the state with protection
        levels computed from the config.
        """
        state = self.get_runtime_state(instrument_id)
        if state.get("phase") != StrategyRuntimeState.OPEN or state.get("quantity", 0) <= 0:
            return None

        if config is not None:
            return StrategyRuntimeState.build_position_state(
                config=config,
                runtime_state=state,
            )
        return state


class LiveSessionContext(SessionContext):
    def __init__(self, session_id: str, strategy_id: str):
        super().__init__(session_id, strategy_id, "live")

    def _fetch_user_id(self) -> str:
        from live_trading.models import TradingSession
        session = TradingSession.objects.only("user_id").filter(id=self.session_id).first()
        return session.user_id if session else None

class PaperSessionContext(SessionContext):
    def __init__(self, session_id: str, strategy_id: str):
        super().__init__(session_id, strategy_id, "paper")

    def _fetch_user_id(self) -> str:
        from paper_trading.models import PaperTradingSession
        session = PaperTradingSession.objects.only("account__user_id").select_related("account").filter(id=self.session_id).first()
        return session.account.user_id if session and session.account else None
