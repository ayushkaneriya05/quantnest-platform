"""Publish execution funds and risk projections; financial records remain in PostgreSQL."""
import logging
from typing import Any, Dict

from .shared_state_store import shared_state_store

logger = logging.getLogger(__name__)


class CacheApi:
    def __init__(self):
        self._cache = shared_state_store

    def update_funds(self, credential_id: int, funds: Dict[str, Any]) -> bool:
        try:
            self._cache.set_funds(credential_id, funds)
            return True
        except Exception:
            logger.exception("Funds publication failed credential=%s", credential_id)
            return False

    def update_session_funds(self, scope: str, session_id: str, funds: Dict[str, Any]) -> bool:
        try:
            self._cache.set_session_funds(scope, str(session_id), funds)
            return True
        except Exception:
            logger.exception("Funds publication failed session=%s:%s", scope, session_id)
            return False

    def update_risk_metrics(self, scope: str, session_id: str, metrics: Dict[str, Any]) -> bool:
        try:
            self._cache.update_risk_metrics(scope, session_id, metrics)
            return True
        except Exception:
            logger.exception("Risk publication failed session=%s:%s", scope, session_id)
            return False

    def mutate_risk_metrics(self, scope: str, session_id: str, transform) -> Dict[str, Any]:
        """Keep counter mutations serialized and propagate failures."""
        return self._cache.mutate_risk_metrics(scope, session_id, transform)

    def clear_session(self, scope: str, session_id: str) -> bool:
        try:
            self._cache.clear_session(scope, session_id)
            return True
        except Exception:
            logger.exception("Session projection cleanup failed session=%s:%s", scope, session_id)
            return False


cache_api = CacheApi()
