"""Process-independent execution state backed by the configured Django cache."""

import logging
from copy import deepcopy
from typing import Any, Dict

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class SharedStateStore:
    """Shared execution projection for all API, worker, and subscriber processes."""

    PREFIX = "quantnest:state:"
    LOCK_TIMEOUT = 5

    def __init__(self):
        backend = settings.CACHES.get("default", {}).get("BACKEND", "")
        if "redis" not in backend.lower():
            logger.warning("Shared execution state is using %s; configure Redis for multi-process correctness.", backend)

    def _key(self, namespace: str, *parts: object) -> str:
        suffix = ":".join(str(part) for part in parts)
        return f"{self.PREFIX}{namespace}:{suffix}"

    def _lock_key(self, namespace: str, *parts: object) -> str:
        return self._key("lock", namespace, *parts)


    def _with_lock(self, lock_key: str):
        from core.redis import runtime_redis
        return runtime_redis().lock(lock_key, timeout=30, blocking_timeout=self.LOCK_TIMEOUT)

    def get_funds(self, credential_id: int) -> Dict[str, Any]:
        return deepcopy(cache.get(self._key("funds", "broker", credential_id)) or {})

    def update_funds(self, credential_id: int, funds: Dict[str, Any]) -> None:
        key = self._key("funds", "broker", credential_id)
        cache.set(key, deepcopy(funds), timeout=None)

    def get_session_funds(self, scope: str, session_id: str) -> Dict[str, Any]:
        return deepcopy(cache.get(self._key("funds", scope, "session", session_id)) or {})

    def update_session_funds(self, scope: str, session_id: str, funds: Dict[str, Any]) -> None:
        key = self._key("funds", scope, "session", session_id)
        cache.set(key, deepcopy(funds), timeout=None)

    def get_runtime_state(self, scope: str, session_id: str, instrument_id: int) -> Dict[str, Any]:
        from core.runtime_projection import get
        return get(scope, session_id, instrument_id)

    def get_risk_metrics(self, scope: str, session_id: str) -> Dict[str, Any]:
        return deepcopy(cache.get(self._key("risk", scope, session_id)) or {})

    def update_risk_metrics(self, scope: str, session_id: str, updates: Dict[str, Any]) -> None:
        key = self._key("risk", scope, session_id)
        with self._with_lock(self._lock_key("risk", scope, session_id)):
            metrics = self.get_risk_metrics(scope, session_id)
            metrics.update(updates)
            cache.set(key, deepcopy(metrics), timeout=None)

    def mutate_risk_metrics(self, scope: str, session_id: str, transform) -> Dict[str, Any]:
        """Calculate and publish metrics while holding the existing session lock."""
        key = self._key("risk", scope, session_id)
        with self._with_lock(self._lock_key("risk", scope, session_id)):
            current = self.get_risk_metrics(scope, session_id)
            updated = transform(current)
            if updated is None:
                return current
            result = deepcopy(updated)
            cache.set(key, result, timeout=None)
            return deepcopy(result)

    def clear_session(self, scope: str, session_id: str) -> None:
        cache.delete(self._key("funds", scope, "session", session_id))
        cache.delete(self._key("risk", scope, session_id))
        from core.runtime_projection import reset
        reset(scope, session_id)

shared_state_store = SharedStateStore()
