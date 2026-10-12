"""Read the funds, risk and runtime projections used by execution."""
from typing import Any, Dict

from .shared_state_store import shared_state_store


class CacheView:
    def __init__(self):
        self._cache = shared_state_store

    def get_funds(self, credential_id: int) -> Dict[str, Any]:
        return self._cache.get_funds(credential_id)

    def get_session_funds(self, scope: str, session_id: str) -> Dict[str, Any]:
        return self._cache.get_session_funds(scope, str(session_id))

    def get_runtime_state(self, scope: str, session_id: str, instrument_id: int) -> Dict[str, Any]:
        return self._cache.get_runtime_state(scope, session_id, instrument_id)

    def get_risk_metrics(self, scope: str, session_id: str) -> Dict[str, Any]:
        return self._cache.get_risk_metrics(scope, session_id)


cache_view = CacheView()
