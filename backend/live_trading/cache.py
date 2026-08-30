from django.core.cache import cache
from django.utils import timezone
from common.cache_keys import CacheKeys


class LiveBrokerStateCache:
    """Minimal broker state cache for HOT path low-latency execution."""
    TTL_SECONDS = 60

    @staticmethod
    def _funds_key(user_id, broker_credential_id):
        return CacheKeys.BROKER_FUNDS.format(user_id=user_id, credential_id=broker_credential_id)

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

    @classmethod
    def invalidate_on_fill(cls, user_id, broker_credential_id):
        """Invalidate funds state on fill for HOT path consistency."""
        cache.delete(cls._funds_key(user_id, broker_credential_id))
