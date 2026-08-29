from django.core.cache import cache
from django.utils import timezone
from common.cache_keys import CacheKeys


class LiveBrokerStateCache:
    TTL_SECONDS = 60
    WALLET_TTL_SECONDS = 300

    @staticmethod
    def _funds_key(user_id, broker_credential_id):
        return CacheKeys.BROKER_FUNDS.format(user_id=user_id, credential_id=broker_credential_id)

    @staticmethod
    def _positions_key(user_id, broker_credential_id):
        return CacheKeys.BROKER_POSITIONS.format(user_id=user_id, credential_id=broker_credential_id)

    @staticmethod
    def _orders_key(user_id, broker_credential_id):
        return CacheKeys.BROKER_ORDERS.format(user_id=user_id, credential_id=broker_credential_id)

    @staticmethod
    def _wallet_key(strategy_id, broker_credential_id):
        return CacheKeys.STRATEGY_WALLET.format(strategy_id=strategy_id, credential_id=broker_credential_id)

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
            timeout=LiveBrokerStateCache.WALLET_TTL_SECONDS,
        )

    @staticmethod
    def get_strategy_wallet(strategy_id, broker_credential_id):
        return cache.get(LiveBrokerStateCache._wallet_key(strategy_id, broker_credential_id)) or {}

    @classmethod
    def invalidate_on_fill(cls, user_id, broker_credential_id):
        cache.delete(cls._funds_key(user_id, broker_credential_id))
        cache.delete(cls._positions_key(user_id, broker_credential_id))
