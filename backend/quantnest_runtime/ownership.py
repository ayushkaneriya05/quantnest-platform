"""Stable virtual partitions and renewable ownership leases."""
import hashlib
import uuid
from core.redis import runtime_redis


def partition(identity, count):
    if count < 1:
        raise ValueError("Partition count must be positive")
    return int.from_bytes(hashlib.blake2b(str(identity).encode(), digest_size=8).digest(), "big") % count


class Lease:
    def __init__(self, name, ttl=15):
        self.key = f"quantnest:lease:{name}"
        self.token = uuid.uuid4().hex
        self.ttl = ttl

    def acquire(self):
        return bool(runtime_redis().set(self.key, self.token, nx=True, ex=self.ttl))

    def renew(self):
        return bool(runtime_redis().eval(
            "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('EXPIRE', KEYS[1], ARGV[2]) end return 0",
            1, self.key, self.token, self.ttl))

    def release(self):
        runtime_redis().eval(
            "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end return 0",
            1, self.key, self.token)
