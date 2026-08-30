from decimal import Decimal
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from strategy_engine.runtime import StrategyRuntimeState

logger = logging.getLogger(__name__)

class SessionContext(ABC):
    """
    Abstract interface for execution contexts (Live vs Paper).
    Provides identical access to position states, capital, and risk stats
    regardless of whether the underlying data comes from a DB or a Broker.

    CRITICAL: All methods called during tick evaluation (get_position,
    get_risk_stats, get_runtime_state, update_runtime_state) MUST be
    DB-free.  They read/write exclusively from Redis.
    """
    def __init__(self, session_id: str, strategy_id: str, scope: str):
        self.session_id = session_id
        self.strategy_id = strategy_id
        self.scope = scope
        self.user_id = self._fetch_user_id()

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
        """Gets the ephemeral runtime state (peak price, trailing stop)."""
        return StrategyRuntimeState.trade_state(self.scope, self.session_id, instrument_id)
        
    def update_runtime_state(self, instrument_id: int, updates: Dict[str, Any]):
        """Updates the ephemeral runtime state."""
        StrategyRuntimeState.update_trade_state(self.scope, self.session_id, instrument_id, updates)

    def get_position(self, instrument_id: int, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Returns the current open position state, or None if flat.

        DB-free: Reads exclusively from the Redis runtime state written by
        mark_open() during order fills.  When ``config`` is provided (slow
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
        from marketdata.l1_cache import tick_cache
        from live_trading.cache import LiveBrokerStateCache
        from live_trading.services import LiveExecutionService
        try:
            allocation = tick_cache.get_live_allocation(self.session_id)
            if not allocation:
                return 0.0
            funds_state = LiveBrokerStateCache.get_funds_state(allocation.user_id, allocation.broker_credential_id)
            funds_payload = (funds_state or {}).get("payload") or {}
            broker_margin = Decimal(
                funds_payload.get("available_margin") or funds_payload.get("cash_balance")
            )
            broker_margin = float(broker_margin) if broker_margin is not None else float("inf")
            alloc_available = float(allocation.available_capital or 0.0)
            return min(alloc_available, broker_margin)
        except Exception as e:
            logger.error(f"Error fetching live capital: {e}")
            return 0.0

    def get_risk_stats(self) -> Dict[str, Any]:
        from risk_management.cache import RiskCache
        return RiskCache.get_stats("LIVE", self.user_id, self.session_id)


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
        from marketdata.l1_cache import tick_cache
        try:
            account = tick_cache.get_paper_account(self.session_id)
            if account:
                return float(account.current_balance or 0.0)
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching paper capital: {e}")
            return 0.0

    def get_risk_stats(self) -> Dict[str, Any]:
        from risk_management.cache import RiskCache
        return RiskCache.get_stats("PAPER", self.user_id, self.session_id)
