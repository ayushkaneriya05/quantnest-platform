from django.core.cache import cache
from django.utils import timezone


class LiveBrokerStateCache:
    TTL_SECONDS = 60 * 60 * 24

    @staticmethod
    def _funds_key(user_id, broker_credential_id):
        return f"funds:{user_id}:{broker_credential_id}"

    @staticmethod
    def _positions_key(user_id, broker_credential_id):
        return f"positions:{user_id}:{broker_credential_id}"

    @staticmethod
    def _orders_key(user_id, broker_credential_id):
        return f"active_orders:{user_id}:{broker_credential_id}"

    @staticmethod
    def _wallet_key(strategy_id, broker_credential_id):
        return f"strategy_wallet:{strategy_id}:{broker_credential_id}"

    @staticmethod
    def _wrap(payload):
        return {
            "updated_at": timezone.now().isoformat(),
            "payload": payload,
        }

    @staticmethod
    def set_funds_state(user_id, broker_credential_id, payload):
        cache.set(
            LiveBrokerStateCache._funds_key(user_id, broker_credential_id),
            LiveBrokerStateCache._wrap(payload),
            timeout=LiveBrokerStateCache.TTL_SECONDS,
        )

    @staticmethod
    def get_funds_state(user_id, broker_credential_id):
        return cache.get(LiveBrokerStateCache._funds_key(user_id, broker_credential_id)) or {}

    @staticmethod
    def set_positions_state(user_id, broker_credential_id, payload):
        cache.set(
            LiveBrokerStateCache._positions_key(user_id, broker_credential_id),
            LiveBrokerStateCache._wrap(payload),
            timeout=LiveBrokerStateCache.TTL_SECONDS,
        )

    @staticmethod
    def get_positions_state(user_id, broker_credential_id):
        return cache.get(LiveBrokerStateCache._positions_key(user_id, broker_credential_id)) or {}

    @staticmethod
    def set_orders_state(user_id, broker_credential_id, payload):
        cache.set(
            LiveBrokerStateCache._orders_key(user_id, broker_credential_id),
            LiveBrokerStateCache._wrap(payload),
            timeout=LiveBrokerStateCache.TTL_SECONDS,
        )

    @staticmethod
    def get_orders_state(user_id, broker_credential_id):
        return cache.get(LiveBrokerStateCache._orders_key(user_id, broker_credential_id)) or {}

    @staticmethod
    def set_strategy_wallet(strategy_id, broker_credential_id, payload):
        cache.set(
            LiveBrokerStateCache._wallet_key(strategy_id, broker_credential_id),
            LiveBrokerStateCache._wrap(payload),
            timeout=LiveBrokerStateCache.TTL_SECONDS,
        )

    @staticmethod
    def get_strategy_wallet(strategy_id, broker_credential_id):
        return cache.get(LiveBrokerStateCache._wallet_key(strategy_id, broker_credential_id)) or {}


class LiveRoutingCache:
    TTL_SECONDS = 60 * 60 * 24 * 7

    @classmethod
    def _key(cls, symbol):
        return f"live_routing:{symbol}"

    @classmethod
    def add_session(cls, symbol, session_id):
        key = cls._key(symbol)
        sessions = set(cache.get(key, []) or [])
        sessions.add(str(session_id))
        cache.set(key, list(sessions), timeout=cls.TTL_SECONDS)

    @classmethod
    def remove_session(cls, symbol, session_id):
        key = cls._key(symbol)
        sessions = set(cache.get(key, []) or [])
        if str(session_id) in sessions:
            sessions.remove(str(session_id))
            cache.set(key, list(sessions), timeout=cls.TTL_SECONDS)

    @classmethod
    def get_sessions(cls, symbol):
        key = cls._key(symbol)
        return cache.get(key, []) or []
