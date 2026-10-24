"""Launch provider services or delegate to the execution process supervisor.

This module owns service startup/shutdown only. Feed ingestion and broker events
run separately so their network waits cannot block strategy evaluation.
"""
import argparse
import logging
import signal
import threading
import uuid

from common.redis import runtime_redis
from execution.launcher import initialize

logger = logging.getLogger(__name__)


LEASE_TTL_SECONDS = 15
LEASE_RENEW_SECONDS = 3


class Lease:
    """Own one provider service; token checks protect replacement owners."""

    def __init__(self, name: str):
        self.key = f"quantnest:lease:{name}"
        self.token = uuid.uuid4().hex

    def acquire(self) -> bool:
        return bool(runtime_redis().set(self.key, self.token, nx=True, ex=LEASE_TTL_SECONDS))

    def renew(self) -> bool:
        return bool(runtime_redis().eval(
            "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('EXPIRE', KEYS[1], ARGV[2]) end return 0",
            1, self.key, self.token, LEASE_TTL_SECONDS))

    def release(self) -> None:
        runtime_redis().eval(
            "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end return 0",
            1, self.key, self.token)


def singleton(service, stop):
    from common.enums import ExecutionScope
    from django.conf import settings

    if service == "broker-events" and ExecutionScope.LIVE not in settings.EXECUTION_ENABLED_SCOPES:
        raise ValueError("Broker events require Live execution in this deployment")
    lease = Lease(service)
    if not lease.acquire():
        raise RuntimeError(f"{service} is already owned")
    failed = threading.Event()

    def renew():
        while not stop.wait(LEASE_RENEW_SECONDS):
            try:
                if lease.renew():
                    continue
            except Exception:
                logger.exception("Could not renew %s ownership", service)
            failed.set()
            stop.set()
    thread = threading.Thread(target=renew, daemon=True)
    thread.start()
    try:
        if service == "market-data":
            from marketdata.providers import live_client
            client = live_client()
            try:
                client.connect()
                client.start_subscription_sync()
                # A bounded wait lets Windows process Ctrl+C on Python 3.12.
                while not stop.wait(1):
                    pass
            finally:
                client.shutdown()
        elif service == "broker-events":
            from live_trading.websocket_manager import WebSocketConnectionManager
            manager = WebSocketConnectionManager()
            try:
                while not stop.is_set():
                    manager.sync_connections()
                    stop.wait(5)
            finally:
                manager.stop_all()
        if failed.is_set():
            raise RuntimeError(f"{service} lost ownership")
    finally:
        stop.set()
        thread.join(timeout=2)
        lease.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["market-data", "execution", "broker-events"])
    args = parser.parse_args()
    if args.service == "execution":
        # The execution supervisor owns Django setup, signals and child processes.
        from execution.launcher import main as run_execution
        return run_execution()
    initialize()
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    singleton(args.service, stop)
