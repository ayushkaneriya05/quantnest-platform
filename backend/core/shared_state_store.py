"""Process-independent execution state backed by the configured Django cache."""

import time
import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SharedStateStore:
    """Shared execution projection for all API, worker, and subscriber processes."""

    PREFIX = "quantnest:state:"
    LOCK_TIMEOUT = 5
    LOCK_RETRY_SECONDS = 0.002

    def __init__(self):
        backend = settings.CACHES.get("default", {}).get("BACKEND", "")
        if "redis" not in backend.lower():
            logger.warning(
                "Shared execution state is using %s; configure Redis for multi-process correctness.",
                backend,
            )

    def _key(self, namespace: str, *parts: object) -> str:
        suffix = ":".join(str(part) for part in parts)
        return f"{self.PREFIX}{namespace}:{suffix}"

    def _lock_key(self, namespace: str, *parts: object) -> str:
        return self._key("lock", namespace, *parts)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _with_lock(self, lock_key: str):
        class CacheLock:
            def __init__(self, store, key):
                self.store = store
                self.key = key
                self.token = f"{id(self)}:{time.time_ns()}"

            def __enter__(self):
                deadline = time.monotonic() + self.store.LOCK_TIMEOUT
                while not self.store._add(self.key, self.token, self.store.LOCK_TIMEOUT):
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Timed out acquiring shared-state lock {self.key}")
                    time.sleep(self.store.LOCK_RETRY_SECONDS)
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                if self.store._get(self.key) == self.token:
                    self.store._delete(self.key)

        return CacheLock(self, lock_key)

    @staticmethod
    def _get(key):
        return cache.get(key)

    @staticmethod
    def _set(key, value, timeout=None):
        cache.set(key, value, timeout=timeout)

    @staticmethod
    def _add(key, value, timeout):
        return cache.add(key, value, timeout=timeout)

    @staticmethod
    def _delete(key):
        cache.delete(key)

    def _next_version(self, key: str) -> int:
        version_key = self._key("version", key)
        if cache.add(version_key, 0, timeout=None):
            return 0
        return cache.incr(version_key)

    def _stamp(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        result = deepcopy(value)
        result["_version"] = self._next_version(key)
        result["_updated_at"] = self._now()
        return result

    def get_orders(self, scope: str, session_id: str) -> List[Dict[str, Any]]:
        return deepcopy(self._get(self._key("orders", scope, session_id)) or [])

    def add_order(self, scope: str, session_id: str, order: Dict[str, Any]) -> None:
        key = self._key("orders", scope, session_id)
        with self._with_lock(self._lock_key("orders", scope, session_id)):
            orders = self.get_orders(scope, session_id)
            orders.append(self._stamp(key, order))
            self._set(key, orders, timeout=None)

    def update_order(self, scope: str, session_id: str, order_id: str, updates: Dict[str, Any]) -> bool:
        key = self._key("orders", scope, session_id)
        with self._with_lock(self._lock_key("orders", scope, session_id)):
            orders = self.get_orders(scope, session_id)
            for order in orders:
                if order.get("id") == order_id or order.get("broker_order_id") == order_id:
                    order.update(updates)
                    self._set(key, [self._stamp(key, order) if item is order else item for item in orders], timeout=None)
                    return True
        return False

    def upsert_order(self, scope: str, session_id: str, order: Dict[str, Any]) -> None:
        key = self._key("orders", scope, session_id)
        with self._with_lock(self._lock_key("orders", scope, session_id)):
            orders = self.get_orders(scope, session_id)
            order_id = order.get("id") or order.get("broker_order_id")
            for existing in orders:
                if order_id and (
                    existing.get("id") == order_id
                    or existing.get("broker_order_id") == order_id
                ):
                    existing.update(order)
                    self._set(key, [self._stamp(key, item) if item is existing else item for item in orders], timeout=None)
                    return
            orders.append(self._stamp(key, order))
            self._set(key, orders, timeout=None)

    def remove_order(self, scope: str, session_id: str, order_id: str) -> bool:
        key = self._key("orders", scope, session_id)
        with self._with_lock(self._lock_key("orders", scope, session_id)):
            orders = self.get_orders(scope, session_id)
            remaining = [
                order for order in orders
                if order.get("id") != order_id and order.get("broker_order_id") != order_id
            ]
            if len(remaining) == len(orders):
                return False
            self._set(key, remaining, timeout=None)
            return True

    def get_positions(self, scope: str, session_id: str) -> List[Dict[str, Any]]:
        return deepcopy(self._get(self._key("positions", scope, session_id)) or [])

    def add_position(self, scope: str, session_id: str, position: Dict[str, Any]) -> None:
        key = self._key("positions", scope, session_id)
        with self._with_lock(self._lock_key("positions", scope, session_id)):
            positions = self.get_positions(scope, session_id)
            positions.append(self._stamp(key, position))
            self._set(key, positions, timeout=None)

    def update_position(self, scope: str, session_id: str, position_id: str, updates: Dict[str, Any]) -> bool:
        key = self._key("positions", scope, session_id)
        with self._with_lock(self._lock_key("positions", scope, session_id)):
            positions = self.get_positions(scope, session_id)
            for position in positions:
                if position.get("id") == position_id:
                    position.update(updates)
                    self._set(key, [self._stamp(key, item) if item is position else item for item in positions], timeout=None)
                    return True
        return False

    def upsert_position(self, scope: str, session_id: str, position: Dict[str, Any]) -> None:
        key = self._key("positions", scope, session_id)
        with self._with_lock(self._lock_key("positions", scope, session_id)):
            positions = self.get_positions(scope, session_id)
            position_id = position.get("id")
            for existing in positions:
                if position_id and existing.get("id") == position_id:
                    existing.update(position)
                    self._set(key, [self._stamp(key, item) if item is existing else item for item in positions], timeout=None)
                    return
            positions.append(self._stamp(key, position))
            self._set(key, positions, timeout=None)

    def remove_position(self, scope: str, session_id: str, position_id: str) -> bool:
        key = self._key("positions", scope, session_id)
        with self._with_lock(self._lock_key("positions", scope, session_id)):
            positions = self.get_positions(scope, session_id)
            remaining = [position for position in positions if position.get("id") != position_id]
            if len(remaining) == len(positions):
                return False
            self._set(key, remaining, timeout=None)
            return True

    def get_funds(self, credential_id: int) -> Optional[Dict[str, Any]]:
        return deepcopy(self._get(self._key("funds", "broker", credential_id)) or {})

    def set_funds(self, credential_id: int, funds: Dict[str, Any]) -> None:
        key = self._key("funds", "broker", credential_id)
        self._set(key, self._stamp(key, funds), timeout=None)

    def get_session_funds(self, scope: str, session_id: str) -> Optional[Dict[str, Any]]:
        return deepcopy(self._get(self._key("funds", scope, "session", session_id)) or {})

    def set_session_funds(self, scope: str, session_id: str, funds: Dict[str, Any]) -> None:
        key = self._key("funds", scope, "session", session_id)
        self._set(key, self._stamp(key, funds), timeout=None)

    def get_runtime_state(self, scope: str, session_id: str, instrument_id: int) -> Dict[str, Any]:
        return deepcopy(self._get(self._key("runtime", scope, session_id, instrument_id)) or {})

    def set_runtime_state(self, scope: str, session_id: str, instrument_id: int, state: Dict[str, Any]) -> None:
        key = self._key("runtime", scope, session_id, instrument_id)
        self._set(key, self._stamp(key, state), timeout=None)

    def update_runtime_state(self, scope: str, session_id: str, instrument_id: int, updates: Dict[str, Any]) -> None:
        key = self._key("runtime", scope, session_id, instrument_id)
        with self._with_lock(self._lock_key("runtime", scope, session_id, instrument_id)):
            state = self.get_runtime_state(scope, session_id, instrument_id)
            state.update(updates)
            self._set(key, self._stamp(key, state), timeout=None)
            index_key = self._key("runtime-index", scope, session_id)
            instrument_ids = self._get(index_key) or []
            if instrument_id not in instrument_ids:
                instrument_ids.append(instrument_id)
                self._set(index_key, instrument_ids, timeout=None)

    def clear_runtime_state(self, scope: str, session_id: str, instrument_id: int) -> None:
        self._delete(self._key("runtime", scope, session_id, instrument_id))
        index_key = self._key("runtime-index", scope, session_id)
        self._set(
            index_key,
            [value for value in (self._get(index_key) or []) if value != instrument_id],
            timeout=None,
        )

    def get_risk_metrics(self, scope: str, session_id: str) -> Dict[str, Any]:
        return deepcopy(self._get(self._key("risk", scope, session_id)) or {})

    def set_risk_metrics(self, scope: str, session_id: str, metrics: Dict[str, Any]) -> None:
        key = self._key("risk", scope, session_id)
        self._set(key, self._stamp(key, metrics), timeout=None)

    def update_risk_metrics(self, scope: str, session_id: str, updates: Dict[str, Any]) -> None:
        key = self._key("risk", scope, session_id)
        with self._with_lock(self._lock_key("risk", scope, session_id)):
            metrics = self.get_risk_metrics(scope, session_id)
            metrics.update(updates)
            self._set(key, self._stamp(key, metrics), timeout=None)

    def clear_session(self, scope: str, session_id: str) -> None:
        self._delete(self._key("orders", scope, session_id))
        self._delete(self._key("positions", scope, session_id))
        self._delete(self._key("risk", scope, session_id))
        for instrument_id in self._get(self._key("runtime-index", scope, session_id)) or []:
            self._delete(self._key("runtime", scope, session_id, instrument_id))
        self._delete(self._key("runtime-index", scope, session_id))

    def get_session_version(self, session_id: str) -> int:
        return int(self._get(self._key("version", session_id)) or 0)

    def get_cache_stats(self) -> Dict[str, Any]:
        return {"backend": "shared-cache", "process_local": False}

    def get(self, key: str, default=None):
        return self._get(key) if self._get(key) is not None else default

    def set(self, key: str, value: Any, timeout=None):
        self._set(key, value, timeout=timeout)


shared_state_store = SharedStateStore()
