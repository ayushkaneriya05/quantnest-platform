"""Runtime CLI and importable worker targets for spawned service processes."""
import argparse
import logging
import multiprocessing
import os
import signal
import threading
import time


def initialize():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
    # Bound native BLAS/OpenMP threads before importing numerical libraries.
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
        os.environ.setdefault(name, "1")
    import django
    django.setup()
    from django.conf import settings
    if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        raise RuntimeError("Trading runtime requires PostgreSQL row locks")
    if "redis" not in settings.CACHES["default"]["BACKEND"].lower():
        raise RuntimeError("Trading runtime requires shared Redis projections")
    if min(settings.EXECUTION_WORKERS, settings.ORDER_WORKERS, settings.CALCULATION_WORKERS,
           settings.ORDER_CONCURRENCY, settings.EXECUTION_TICK_BATCH, settings.TERMINAL_MATCH_BATCH,
           settings.EXECUTION_MAX_ACTORS, settings.CALCULATION_CACHE_MB) < 1:
        raise ValueError("Worker counts must be positive")
    if not 0 <= settings.EXECUTION_NODE_INDEX < settings.EXECUTION_NODE_COUNT:
        raise ValueError("Execution node index is outside the configured topology")
    if settings.ORDER_WORKERS * settings.EXECUTION_NODE_COUNT > settings.ORDER_PARTITIONS:
        raise ValueError("Gateway workers cannot exceed order partitions")
    if settings.EXECUTION_WORKERS * settings.EXECUTION_NODE_COUNT > settings.EXECUTION_SHARDS:
        raise ValueError("Execution workers cannot exceed execution partitions")
    if not settings.EXECUTION_ENABLED_SCOPES <= {"paper", "live"}:
        raise ValueError("Unknown execution scope")


def child(service, index, stop):
    try:
        run_child(service, index, stop)
    except BaseException:
        # Failed SDK I/O cannot hold this isolated child alive indefinitely.
        # Its supervisor recovers durable requests after ownership expires.
        logging.getLogger(__name__).exception("Runtime child failed service=%s index=%s", service, index)
        os._exit(1)


def run_child(service, index, stop):
    initialize()
    if service == "execution":
        from quantnest_runtime.execution import run_worker
        run_worker(index, stop)
    elif service == "terminal":
        from quantnest_runtime.terminal import run_worker
        run_worker(index, stop)
    elif service == "orders":
        from live_trading.services import LiveExecutionService
        from paper_trading.services import PaperExecutionService
        failures = []
        def consume(method):
            try:
                method(stop_event=stop, worker_index=index)
            except Exception as exc:
                failures.append(exc)
        threads = [threading.Thread(target=consume, args=(method,)) for method in (
            LiveExecutionService.run_order_stream_consumer, PaperExecutionService.run_order_stream_consumer)]
        for thread in threads:
            thread.start()
        while not stop.wait(0.2):
            if any(not thread.is_alive() for thread in threads):
                if failures:
                    raise RuntimeError("Order gateway failed") from failures[0]
                if not stop.is_set():
                    raise RuntimeError("Order gateway exited unexpectedly")
        for thread in threads:
            thread.join(timeout=10)
        if failures:
            raise RuntimeError("Order gateway failed") from failures[0]


def singleton(service, stop):
    from quantnest_runtime.ownership import Lease
    from django.conf import settings
    lease_name = f"{service}:{settings.EXECUTION_NODE_INDEX}" if service == "market-data" else service
    lease = Lease(lease_name, ttl=30)
    if not lease.acquire():
        raise RuntimeError(f"{service} is already owned")
    failed = threading.Event()
    def renew():
        while not stop.wait(5):
            try:
                if not lease.renew():
                    failed.set()
                    stop.set()
            except Exception:
                failed.set()
                stop.set()
    thread = threading.Thread(target=renew, daemon=True)
    thread.start()
    try:
        if service == "outbox":
            from core.outbox import relay_batch
            from django.db import close_old_connections
            while not stop.is_set():
                close_old_connections()
                count = relay_batch()
                if not count:
                    stop.wait(0.05)
        elif service == "market-data":
            if settings.EXECUTION_NODE_INDEX != 0:
                from marketdata.replication import run_replica
                run_replica(stop)
                if failed.is_set():
                    raise RuntimeError("Market replica lost ownership")
                return
            from marketdata.providers import live_client
            from marketdata.replication import ObservationRelay
            client = live_client()
            relay = ObservationRelay() if settings.EXECUTION_NODE_COUNT > 1 else None
            client.relay = relay
            try:
                client.connect()
                client.start_subscription_sync()
                while not stop.wait(1):
                    if relay and relay.failed.is_set():
                        raise RuntimeError("Market observation relay failed")
            finally:
                client.shutdown()
                if relay:
                    relay.close()
        elif service == "broker-events":
            from live_trading.websocket_manager import _websocket_manager
            from brokers.models import BrokerCredential
            _websocket_manager.start_health_monitor()
            try:
                while not stop.is_set():
                    for credential in BrokerCredential.objects.filter(is_active=True, is_verified=True):
                        _websocket_manager.start_processor(credential.pk)
                    stop.wait(5)
            finally:
                _websocket_manager.stop_all()
        if failed.is_set():
            raise RuntimeError(f"{service} lost ownership")
    finally:
        stop.set()
        thread.join(timeout=2)
        lease.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["market-data", "execution", "orders", "terminal", "broker-events", "outbox"])
    args = parser.parse_args()
    initialize()
    from django.conf import settings
    stop = multiprocessing.get_context("spawn").Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.service in ("execution", "orders", "terminal"):
        count = settings.EXECUTION_WORKERS if args.service == "execution" else settings.ORDER_WORKERS
        processes = {}
        crashes, started = {}, {}
        try:
            while not stop.is_set():
                for index in range(count):
                    process = processes.get(index)
                    if process and process.is_alive():
                        if time.monotonic() - started[index] >= 60:
                            crashes[index] = 0
                        continue
                    if process:
                        process.join()
                        crashes[index] = crashes.get(index, 0) + 1
                        if crashes[index] >= 5:
                            raise RuntimeError(f"{args.service} worker {index} repeatedly failed")
                        if stop.wait(min(2 ** crashes[index], 15)):
                            break
                    process = multiprocessing.get_context("spawn").Process(
                        target=child, args=(args.service, index, stop), name=f"{args.service}-{index}")
                    process.start()
                    processes[index] = process
                    started[index] = time.monotonic()
                stop.wait(0.5)
        finally:
            stop.set()
            for process in processes.values():
                process.join(timeout=10)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=3)
    else:
        singleton(args.service, stop)
