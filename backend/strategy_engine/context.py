import logging
import threading
from copy import deepcopy
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from strategy_engine.runtime import StrategyRuntimeState
from core.cache_view import cache_view

logger = logging.getLogger(__name__)

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
    _PENDING_PHASES = {
        StrategyRuntimeState.ENTRY_PENDING,
        StrategyRuntimeState.EXIT_PENDING,
        StrategyRuntimeState.PARTIAL_EXIT_PENDING,
    }

    def __init__(self, session_id: str, strategy_id: str, scope: str):
        self.session_id = session_id
        self.strategy_id = strategy_id
        self.scope = scope
        self.user_id = self._fetch_user_id()
        self._runtime_l1: Dict[int, Dict[str, Any]] = {}
        self._runtime_l1_lock = threading.RLock()

    @abstractmethod
    def _fetch_user_id(self) -> str:
        """Fetch the associated user ID for the session.  Called once at init (DB is OK here)."""
        pass

    @abstractmethod
    def get_strategy_config(self) -> Dict[str, Any]:
        """Returns the strategy config for the session.  Called once at init (DB is OK here)."""
        pass
    
    @abstractmethod
    def get_available_capital(self) -> float:
        """Returns available capital for entry sizing."""
        pass

    @abstractmethod
    def get_risk_stats(self) -> Dict[str, Any]:
        """Returns stats required for risk evaluation (drawdown, daily loss, etc)."""
        pass
        
    def get_risk_evaluator(self) -> Any:
        """Returns a RiskEvaluator initialized with the available capital."""
        from risk_management.evaluator import RiskEvaluator
        return RiskEvaluator(self.get_available_capital())
        
    def get_runtime_state(self, instrument_id: int) -> Dict[str, Any]:
        """Get runtime state, refreshing Redis only for missing/pending state."""
        with self._runtime_l1_lock:
            local_state = self._runtime_l1.get(instrument_id)
            if local_state is None or local_state.get("phase") in self._PENDING_PHASES:
                shared_state = StrategyRuntimeState.trade_state(self.scope, self.session_id, instrument_id)
                if shared_state:
                    if local_state:
                        local_state.update(shared_state)
                    else:
                        local_state = shared_state
                    self._runtime_l1[instrument_id] = local_state

            return deepcopy(local_state or {})
        
    def update_runtime_state(self, instrument_id: int, updates: Dict[str, Any]):
        """Update L1 state and persist only lifecycle/non-hot fields."""
        with self._runtime_l1_lock:
            state = self._runtime_l1.setdefault(instrument_id, {})
            state.update(updates)

            shared_updates = {
                field: value
                for field, value in updates.items()
                if field not in self._HOT_FIELDS and not field.startswith("breakeven_") and not field.startswith("partial_exit_")
            }
        if shared_updates:
            StrategyRuntimeState.update_trade_state(self.scope, self.session_id, instrument_id, shared_updates)

    def apply_external_runtime_state(self, instrument_id: int, updates: Dict[str, Any]):
        """Apply a lifecycle event to this worker's L1 state."""
        with self._runtime_l1_lock:
            state = self._runtime_l1.setdefault(instrument_id, {})
            state.update(updates)

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

    def get_strategy_config(self) -> Dict[str, Any]:
        from live_trading.models import TradingSession
        session = TradingSession.objects.filter(id=self.session_id).select_related(
            'allocation__deployed_version'
        ).first()
        if session and session.allocation and session.allocation.deployed_version:
            config = session.allocation.deployed_version.config_snapshot
            return config
        return {}
    
    def _fetch_user_id(self) -> str:
        from live_trading.models import TradingSession
        session = TradingSession.objects.only("user_id").filter(id=self.session_id).first()
        return session.user_id if session else None

    def get_available_capital(self) -> float:
        try:
            session_funds = cache_view.get_session_funds("live", self.session_id)
            if session_funds:
                broker_margin = float(
                    session_funds.get("available_margin") or session_funds.get("cash_balance") or session_funds.get("net_equity") or 0
                )
                allocation_capital = float(session_funds.get("allocation_available_capital") or 0)
                return min(allocation_capital, broker_margin)

            # Get allocation directly from database
            from live_trading.models import TradingSession
            session = TradingSession.objects.filter(id=self.session_id).select_related('allocation').first()
            if not session or not session.allocation:
                return 0.0
            
            allocation = session.allocation
            # Use unified cache interface for funds
            funds_data = cache_view.get_funds(allocation.broker_credential_id)
            if funds_data:
                broker_margin = float(funds_data.get("available_margin") or funds_data.get("cash_balance") or 0)
            else:
                # Fallback to direct broker API if cache miss
                from brokers.services import BrokerService
                funds_data_api = BrokerService.get_funds(allocation.broker_credential)
                broker_margin = float(funds_data_api.get("available_margin") or funds_data_api.get("cash_balance") or 0)
            broker_margin = float(broker_margin) if broker_margin is not None else float("inf")
            alloc_available = float(allocation.available_capital or 0.0)
            return min(alloc_available, broker_margin)
        except Exception as e:
            logger.error(f"Error fetching live capital: {e}")
            return 0.0

    def get_risk_stats(self) -> Dict[str, Any]:
        return cache_view.get_risk_metrics("live", self.session_id)


class PaperSessionContext(SessionContext):
    def __init__(self, session_id: str, strategy_id: str):
        super().__init__(session_id, strategy_id, "paper")

    def get_strategy_config(self) -> Dict[str, Any]:
        from paper_trading.models import PaperTradingSession
        session = PaperTradingSession.objects.filter(id=self.session_id).select_related('allocation__deployed_version').first()
        if session and session.allocation and session.allocation.deployed_version:
            config = session.allocation.deployed_version.config_snapshot
            return config
        return {}

    def _fetch_user_id(self) -> str:
        from paper_trading.models import PaperTradingSession
        session = PaperTradingSession.objects.only("account__user_id").select_related("account").filter(id=self.session_id).first()
        return session.account.user_id if session and session.account else None

    def get_available_capital(self) -> float:
        try:
            session_funds = cache_view.get_session_funds("paper", self.session_id)
            if session_funds:
                return float(
                    session_funds.get("available_margin") or session_funds.get("cash_balance") or session_funds.get("net_equity") or 0
                )

            from paper_trading.models import PaperTradingSession

            session = PaperTradingSession.objects.filter(id=self.session_id).select_related("account").first()
            if not session or not session.account:
                return 0.0

            # Fallback to database if cache miss (should be rare)
            return float(session.account.current_balance or 0.0)
        except Exception as e:
            logger.error(f"Error fetching paper capital: {e}")
            return 0.0

    def get_risk_stats(self) -> Dict[str, Any]:
        return cache_view.get_risk_metrics("paper", self.session_id)
