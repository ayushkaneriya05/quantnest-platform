"""
Circuit Breaker for Broker API Calls
======================================
Implements the classic 3-state circuit breaker pattern:

    CLOSED  → normal operation, calls pass through
    OPEN    → failure threshold exceeded, calls fail immediately
    HALF_OPEN → cooldown expired, one test call is allowed

Usage:
    cb = BrokerCircuitBreaker("fyers", failure_threshold=3, recovery_timeout=30)

    with cb:
        result = fyers_api.place_order(...)

If 3 consecutive failures occur, subsequent calls raise CircuitBreakerOpenError
immediately (without hitting the broker) for `recovery_timeout` seconds.
After that window the circuit moves to HALF_OPEN and allows one test call.
A successful test call resets the circuit to CLOSED.

The breaker state is stored in Redis so it is shared across all Celery
workers — a single broken broker session fails fast for all strategies.
"""
import logging
import time
from contextlib import contextmanager
from functools import wraps

from django.core.cache import cache

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Raised when a call is attempted while the circuit breaker is OPEN."""


class BrokerCircuitBreaker:
    """
    Redis-backed circuit breaker for broker API calls.

    States (stored in Redis as a hash at `cb:{name}`):
        state:      'CLOSED' | 'OPEN' | 'HALF_OPEN'
        failures:   consecutive failure count
        opened_at:  epoch timestamp when the circuit opened
    """

    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    _CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._key = f"circuit_breaker:{name}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def __enter__(self):
        self._check_state()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._on_success()
        elif not issubclass(exc_type, CircuitBreakerOpenError):
            # Only count actual call failures, not our own open-circuit errors
            self._on_failure()
        return False  # never suppress exceptions

    @contextmanager
    def protected(self):
        """Context manager alias for cleaner usage in service code."""
        with self:
            yield

    def call(self, func, *args, **kwargs):
        """Wrap a single callable with circuit-breaker protection."""
        with self:
            return func(*args, **kwargs)

    @property
    def state(self) -> str:
        data = self._get_state()
        return data.get("state", self.STATE_CLOSED)

    def reset(self):
        """Manually reset the circuit to CLOSED (e.g., after fixing broker config)."""
        cache.set(self._key, {"state": self.STATE_CLOSED, "failures": 0, "opened_at": None}, timeout=self._CACHE_TIMEOUT)
        logger.info("CircuitBreaker[%s]: manually RESET to CLOSED", self.name)

    # ------------------------------------------------------------------
    # Internal state machine
    # ------------------------------------------------------------------

    def _check_state(self):
        data = self._get_state()
        state = data.get("state", self.STATE_CLOSED)

        if state == self.STATE_CLOSED:
            return  # allow call

        if state == self.STATE_OPEN:
            opened_at = data.get("opened_at") or 0
            elapsed = time.monotonic() - opened_at
            if elapsed >= self.recovery_timeout:
                # Transition to HALF_OPEN for one test call
                self._set_state(self.STATE_HALF_OPEN, failures=data.get("failures", 0))
                logger.info(
                    "CircuitBreaker[%s]: OPEN → HALF_OPEN after %.0fs cooldown",
                    self.name, elapsed,
                )
                return  # allow the single test call
            raise CircuitBreakerOpenError(
                f"CircuitBreaker[{self.name}] is OPEN ({self.recovery_timeout - elapsed:.0f}s remaining). "
                "Broker API calls are temporarily suppressed to prevent cascading failures."
            )

        # HALF_OPEN: allow one test call through (already transitioned above)

    def _on_success(self):
        data = self._get_state()
        state = data.get("state", self.STATE_CLOSED)
        if state in (self.STATE_HALF_OPEN, self.STATE_OPEN):
            logger.info("CircuitBreaker[%s]: %s → CLOSED (call succeeded)", self.name, state)
        self._set_state(self.STATE_CLOSED, failures=0)

    def _on_failure(self):
        data = self._get_state()
        failures = data.get("failures", 0) + 1
        self._set_state(data.get("state", self.STATE_CLOSED), failures=failures)

        if failures >= self.failure_threshold:
            self._set_state(self.STATE_OPEN, failures=failures, opened_at=time.monotonic())
            logger.error(
                "CircuitBreaker[%s]: CLOSED → OPEN after %d consecutive failures. "
                "Broker API calls blocked for %ds.",
                self.name, failures, self.recovery_timeout,
            )
        else:
            logger.warning(
                "CircuitBreaker[%s]: failure %d/%d",
                self.name, failures, self.failure_threshold,
            )

    def _get_state(self) -> dict:
        return cache.get(self._key) or {}

    def _set_state(self, state: str, *, failures: int = 0, opened_at=None):
        data = {
            "state": state,
            "failures": failures,
            "opened_at": opened_at,
        }
        cache.set(self._key, data, timeout=self._CACHE_TIMEOUT)


# ---------------------------------------------------------------------------
# Convenience decorator
# ---------------------------------------------------------------------------

def with_circuit_breaker(name: str, failure_threshold: int = 3, recovery_timeout: int = 30):
    """
    Function decorator that wraps the call with a named circuit breaker.

    Example::

        @with_circuit_breaker("fyers_order", failure_threshold=3)
        def place_order(payload):
            return fyers.place_order(data=payload)
    """
    def decorator(func):
        cb = BrokerCircuitBreaker(name, failure_threshold=failure_threshold, recovery_timeout=recovery_timeout)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)

        wrapper.circuit_breaker = cb  # expose for inspection / reset
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Pre-configured broker circuit breakers (import these in services)
# ---------------------------------------------------------------------------

fyers_circuit_breaker = BrokerCircuitBreaker(
    name="fyers",
    failure_threshold=3,
    recovery_timeout=30,
)
