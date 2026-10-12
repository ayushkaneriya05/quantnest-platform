"""Real local tick -> decision -> Redis -> PostgreSQL -> simulated broker tests.

Run from backend: python -m quantnest_runtime.e2e_benchmark --output PATH
Starts a private, nonpersistent Redis process and uses a disposable PostgreSQL DB.
Never connects to a broker. The adapter is simulated; its delay is an input.
"""
import argparse
import hashlib
import json
import os
import platform
import queue
import shutil
import socket
import subprocess
import threading
import time
import uuid
from contextlib import ExitStack
from datetime import datetime, time as day_time, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch


REPORT = {"cases": []}


def free_port():
    with socket.socket() as channel:
        channel.bind(("127.0.0.1", 0))
        return channel.getsockname()[1]


def forbidden(*args, **kwargs):
    raise AssertionError("Real broker access is prohibited by this benchmark")


def initialize_calculation():
    from quantnest_runtime.calculation import initialize
    initialize()
    from django.db.backends.base.base import BaseDatabaseWrapper
    from marketdata.calendar import MarketSessionCalendar
    # Simulation clock/calendar only: weekend/hour gates are not the subject here.
    MarketSessionCalendar.is_trading_day = lambda self, day, holidays=None: True
    BaseDatabaseWrapper.ensure_connection = forbidden
    socket.socket.connect = forbidden


def percentile(values):
    from quantnest_runtime.latency_benchmark import distribution
    return distribution(values)


class Traces:
    def __init__(self):
        self.lock = threading.RLock()
        self.current = {}
        self.requests = {}
        self.rows = []
        self.errors = []

    def begin(self, actors, cycle, intent, measured):
        with self.lock:
            for item in actors:
                key = item["scope"], str(item["session"].pk), item["instrument"].pk
                trace = {"scope": key[0], "session": key[1], "instrument": key[2],
                         "symbol": item["instrument"].sym_ticker, "cycle": cycle,
                         "intent": intent, "measured": measured, "marks": {}}
                self.current[key] = trace
                self.rows.append(trace)

    def actor_mark(self, actor, stage):
        with self.lock:
            row = self.current.get((actor.scope, str(actor.session), actor.instrument))
            if row:
                row["marks"].setdefault(stage, time.perf_counter_ns())

    def request(self, request):
        with self.lock:
            row = self.current.get((request.scope.lower(), str(request.session_id), request.instrument_id))
            if not row:
                raise AssertionError("Order request has no source tick")
            if row["intent"] != request.intent or "request_id" in row:
                raise AssertionError("Unexpected or duplicate actor order request")
            row["request_id"] = str(request.request_id)
            row["marks"]["request_queued"] = time.perf_counter_ns()
            self.requests[str(request.request_id)] = row

    def mark(self, request_id, stage):
        with self.lock:
            row = self.requests.get(str(request_id))
            if row:
                row["marks"].setdefault(stage, time.perf_counter_ns())

    def wave_complete(self, actors):
        with self.lock:
            return all("durable_fill" in self.current[(item["scope"], str(item["session"].pk), item["instrument"].pk)]["marks"]
                       for item in actors)


class SimulatedClock:
    monotonic = staticmethod(time.monotonic)
    perf_counter = staticmethod(time.perf_counter)

    def __init__(self):
        self.epoch = int(time.time() // 60) * 60 + 20

    def advance(self):
        self.epoch += 60

    def time(self):
        return self.epoch

    def now(self, zone=None):
        return datetime.fromtimestamp(self.epoch, zone or timezone.utc)


def wait_until(predicate, trace, deadline=30):
    end = time.monotonic() + deadline
    while not predicate():
        if trace.errors:
            raise RuntimeError(trace.errors[0])
        if time.monotonic() >= end:
            raise TimeoutError("End-to-end stage did not complete")
        time.sleep(.005)


def run_case(test, name, per_scope, cycles, shared_account=False, ack_ms=0, fill_ms=0):
    from django.contrib.auth import get_user_model
    from django.db import close_old_connections
    from common.models import ExchangeConfig, RuntimeOutbox
    from instruments.models import Instrument
    from strategies.models import Strategy, StrategyVersion
    from brokers.models import BrokerCredential
    from brokers.services import BrokerService
    from core.cache_api import cache_api
    from core.outbox import relay_batch
    from marketdata.calendar import MarketSessionCalendar
    from marketdata.live_feed import MarketObservationClient, LiveMarketDataRegistry
    from marketdata.shared_memory import SharedMemoryManager
    from paper_trading.models import Portfolio, CapitalAllocation, PaperAccount, PaperTradingSession, PaperOrder, PaperPosition, PaperTrade
    from paper_trading.services import PaperExecutionService
    from live_trading.models import LiveStrategyAllocation, TradingSession, LiveOrder, LivePosition, LiveTrade
    from live_trading.services import LiveExecutionService
    from live_trading.websocket_processor import LiveWebSocketProcessor
    from live_trading import order_processor
    from quantnest_runtime import execution
    from strategy_engine import engine, order_queue
    from strategy_engine.router import StrategyOrderRouter
    from core import runtime_projection
    from risk_management.metrics import empty_metrics
    from quantnest_runtime.tests import configuration
    import numpy as np

    trace, clock, stop = Traces(), SimulatedClock(), threading.Event()
    actors, threads, broker_events = [], [], queue.Queue()
    contexts, duplicates = {}, []
    calculated, last_results = set(), {}
    original_protection, original_apply = engine.evaluate_protection, engine.apply_calculation
    original_router = StrategyOrderRouter.publish_order
    original_publish, original_consume = order_queue.publish_order, order_queue.consume_orders
    original_paper = PaperExecutionService._execute_market_order
    original_live = LiveExecutionService._execute_market_order
    original_observation, original_projection = order_processor.apply_order_observation, runtime_projection.update
    original_snapshot = execution._snapshot

    def snapshot(index, worker_contexts):
        rows = original_snapshot(index, worker_contexts)
        for row in rows:
            identity = row["scope"], str(row["session"]), row["instrument"]
            contexts[identity] = row["context"]
        return rows

    def protect(actor, price):
        trace.actor_mark(actor, "protection_started")
        return original_protection(actor, price)

    def apply(actor, result):
        trace.actor_mark(actor, "calculation_applied")
        calculated.add(actor.key)
        last_results[actor.key] = {**result, "actor_gates": {
            "status": actor.status, "gap": actor.gap, "runtime_ready": actor.runtime_ready,
            "market_ready": actor.market_ready, "capital": actor.context.get_available_capital(),
            "last_entry_candle": actor.last_entry_candle}}
        return original_apply(actor, result)

    def route(router, request):
        trace.request(request)
        return original_router(router, request)

    def publish(request):
        trace.mark(request.request_id, "publication_started")
        result = original_publish(request)
        trace.mark(request.request_id, "stream_published")
        return result

    def consume(scope, handler, **kwargs):
        def timed_handler(data):
            trace.mark(data["request_id"], "gateway_started")
            result = handler(data)
            trace.mark(data["request_id"], "gateway_finished")
            return result
        return original_consume(scope, timed_handler, **kwargs)

    def paper(*args, **kwargs):
        result = original_paper(*args, **kwargs)
        if result.status != "FILLED":
            trace.errors.append(f"Paper order rejected: {result.rejection_reason}")
        trace.mark(result.request_id, "durable_fill")
        return result

    def live(*args, **kwargs):
        result = original_live(*args, **kwargs)
        if result.status not in ("PLACED", "FILLED", "PARTIAL_FILL"):
            trace.errors.append(f"Live order did not submit: {result.status}: {result.rejection_reason}")
        trace.mark(result.request_id, "durable_ack")
        return result

    def observe(credential, data):
        result = original_observation(credential, data)
        if result and result.status == "FILLED":
            trace.mark(result.request_id, "durable_fill")
        return result

    def projection(scope, session, instrument, updates, committed_revision=0):
        result = original_projection(scope, session, instrument, updates, committed_revision)
        if updates.get("phase") in ("OPEN", "CLOSED"):
            with trace.lock:
                row = trace.current.get((scope, str(session), instrument))
                if row:
                    row["marks"].setdefault("runtime_projected", time.perf_counter_ns())
        return result

    class Adapter:
        def __init__(self, credential):
            self.credential = credential

        def place_order(self, payload, session=None):
            # Verify the real gateway has committed ownership before the boundary.
            order = LiveOrder.objects.get(pk=int(payload["order_tag"][2:]))
            test.assertEqual(order.status, "UNKNOWN")
            test.assertEqual(order.broker_credential_id, self.credential.pk)
            trace.mark(order.request_id, "broker_sent")
            if ack_ms:
                time.sleep(ack_ms / 1000)
            trace.mark(order.request_id, "broker_ack_received")
            identity = f"SIM-{order.pk}"
            broker_events.put((time.monotonic() + fill_ms / 1000, self.credential, {
                "broker_order_id": identity, "order_tag": payload["order_tag"], "symbol": payload["instrument"],
                "side": payload["side"], "quantity": payload["quantity"], "filled_quantity": payload["quantity"],
                "avg_fill_price": 101 if payload["side"] == "BUY" else 94, "status": "FILLED"}))
            return {"broker_order_id": identity, "status": "PLACED"}

    def guarded_adapter(credential):
        if credential.pk not in {item["credential"].pk for item in actors if item["scope"] == "live"}:
            forbidden()
        return Adapter(credential)

    def background_outbox():
        while not stop.is_set():
            close_old_connections()
            if not relay_batch():
                stop.wait(.05)
        close_old_connections()

    def background_broker():
        processors = {}
        while not stop.is_set():
            try:
                due, credential, update = broker_events.get(timeout=.05)
            except queue.Empty:
                continue
            stop.wait(max(0, due - time.monotonic()))
            if stop.is_set():
                break
            processor = processors.setdefault(credential.pk, LiveWebSocketProcessor(credential))
            # One duplicate websocket observation per order; it must not double-fill.
            processor._handle_order_update(update)
            processor._handle_order_update(update)
            duplicates.append(update["broker_order_id"])
        close_old_connections()

    def launch(function, label, *args, **kwargs):
        def guarded():
            try:
                function(*args, **kwargs)
            except Exception as error:
                trace.errors.append(f"{label}: {type(error).__name__}: {error}")
            finally:
                close_old_connections()
        thread = threading.Thread(target=guarded, name=f"e2e-{label}")
        thread.start()
        threads.append(thread)

    with ExitStack() as stack:
        stack.enter_context(patch("notifications.services.NotificationService.notify"))
        stack.enter_context(patch("celery.app.task.Task.apply_async", forbidden))
        stack.enter_context(patch.object(BrokerService, "ensure_session", return_value=SimpleNamespace(is_valid=True)))
        stack.enter_context(patch.object(BrokerService, "get_adapter", guarded_adapter))
        stack.enter_context(patch.object(execution, "_snapshot", snapshot))
        stack.enter_context(patch.object(execution, "time", clock))
        stack.enter_context(patch("quantnest_runtime.calculation.initialize", initialize_calculation))
        stack.enter_context(patch.object(engine, "datetime", clock))
        stack.enter_context(patch.object(MarketSessionCalendar, "is_trading_day", lambda self, day, holidays=None: True))
        stack.enter_context(patch.object(engine, "evaluate_protection", protect))
        stack.enter_context(patch.object(engine, "apply_calculation", apply))
        stack.enter_context(patch.object(StrategyOrderRouter, "publish_order", route))
        stack.enter_context(patch.object(StrategyOrderRouter(), "_publisher", None, create=True))
        stack.enter_context(patch.object(order_queue, "publish_order", publish))
        stack.enter_context(patch.object(order_queue, "consume_orders", consume))
        stack.enter_context(patch.object(PaperExecutionService, "_execute_market_order", paper))
        stack.enter_context(patch.object(LiveExecutionService, "_execute_market_order", live))
        stack.enter_context(patch.object(order_processor, "apply_order_observation", observe))
        stack.enter_context(patch.object(runtime_projection, "update", projection))
        ExchangeConfig.objects.update_or_create(exchange="NSE", defaults={"timezone": "UTC",
            "market_open": day_time(0), "market_close": day_time(23, 59), "is_active": True})
        user = get_user_model().objects.create_user(username=f"e2e-{name}", email=f"e2e-{name}@example.invalid")
        portfolio = Portfolio.objects.create(user=user, current_capital=1000000)
        credential_shared = None
        # Real observation client publishes UI quotes through the normal 50ms coalescer.
        feed = MarketObservationClient()
        symbol_prefix = hashlib.sha256(name.encode()).hexdigest()[:6].upper()
        try:
            for scope in ("paper", "live"):
                for ordinal in range(per_scope):
                    symbol = f"E2E{symbol_prefix}{scope.upper()[0]}{ordinal}"
                    instrument = Instrument.objects.create(fy_token=f"{name}-{scope}-{ordinal}", symbol=symbol,
                        name="Synthetic latency instrument", sym_ticker=f"NSE:{symbol}-EQ",
                        exchange="NSE", instrument_type="STOCK")
                    strategy = Strategy.objects.create(user=user, name=f"{scope}-{ordinal}", status="ACTIVE",
                        paper_trading_enabled=True, live_trading_enabled=True, auto_version_enabled=False)
                    config = configuration([instrument.pk])
                    config["time_rule"]["timezone"] = "UTC"
                    config["rule_groups"].append({"name": "Five point stop", "rule_type": "STOP_LOSS", "is_active": True,
                        "logical_operator": "AND", "rules": [{"operand_a_type": "POSITION_PNL_POINTS",
                        "operand_a_params": {}, "comparison": "LTE", "operand_b_type": "CONSTANT",
                        "operand_b_params": {"value": -5}}]})
                    # Real EMA entry computation, with a clearly true completed-bar signal.
                    config["rule_groups"][0]["rules"][0] = {"operand_a_type": "CLOSE", "operand_a_params": {},
                        "comparison": "GT", "operand_b_type": "EMA", "operand_b_params": {"period": 20}}
                    config["rule_groups"][0]["rules"].append({"operand_a_type": "CLOSE", "operand_a_params": {},
                        "comparison": "GT", "operand_b_type": "CONSTANT", "operand_b_params": {"value": 100}})
                    version = StrategyVersion.objects.get(strategy=strategy, version_number=1)
                    version.config_snapshot = config
                    version.save(update_fields=["config_snapshot"])
                    if scope == "paper":
                        allocation = CapitalAllocation.objects.create(portfolio=portfolio, strategy=strategy,
                            deployed_version=version, allocated_amount=10000)
                        account = PaperAccount.objects.create(user=user, allocation=allocation,
                            initial_balance=10000, current_balance=10000)
                        session = PaperTradingSession.objects.create(user=user, strategy=strategy, allocation=allocation,
                            account=account, status="RUNNING", include_charges=False)
                        item = {"account": account}
                    else:
                        if credential_shared is None or not shared_account:
                            credential_shared = BrokerCredential.objects.create(user=user, broker_name="FYERS",
                                client_id=f"sim-{ordinal}", is_active=True, is_verified=True)
                        credential = credential_shared
                        allocation = LiveStrategyAllocation.objects.create(user=user, strategy=strategy,
                            broker_credential=credential, deployed_version=version, allocated_capital=10000)
                        session = TradingSession.objects.create(user=user, strategy=strategy,
                            broker_credential=credential, allocation=allocation, status="RUNNING")
                        cache_api.update_funds(credential.pk, {"available_margin": "1000000", "net_equity": "1000000",
                            "cash_balance": "1000000", "snapshot_time": datetime.now(timezone.utc).isoformat()})
                        cache_api.update_session_funds("live", str(session.pk), {"available_margin": "1000000",
                            "allocation_available_capital": "10000"})
                        item = {"credential": credential}
                    cache_api.update_risk_metrics(scope, str(session.pk), empty_metrics(10000, datetime.now(timezone.utc)))
                    service = PaperExecutionService if scope == "paper" else LiveExecutionService
                    service._publish_execution_event("START", session)
                    writer = SharedMemoryManager(instrument.sym_ticker, "1m", create=True, max_size=1000)
                    epochs = np.arange(int(clock.epoch // 60) * 60 - 301 * 60, int(clock.epoch // 60) * 60, 60)
                    prices = np.full(len(epochs), 99.)
                    history = np.column_stack((prices, prices + 1, prices - 1, prices, np.ones(len(prices)), epochs))
                    with writer._locked():
                        writer.array[:len(history)] = history
                        writer.meta_array[0] = len(history) - 1
                        writer.meta_array[3] = writer.meta_array[4] = 1
                    feed.shm_managers[instrument.sym_ticker] = writer
                    feed.ingest_observation(instrument.sym_ticker, {"price": 99}, 1, clock.epoch, time.time())
                    LiveMarketDataRegistry.set_readiness(instrument.sym_ticker, 1000, True)
                    actors.append({"scope": scope, "session": session, "instrument": instrument,
                                   "strategy": strategy, "version": version, **item})
            while RuntimeOutbox.objects.filter(published_at__isnull=True).exists():
                if not relay_batch():
                    raise AssertionError("Fixture outbox could not be delivered")
            launch(background_outbox, "outbox")
            launch(background_broker, "broker")
            launch(PaperExecutionService.run_order_stream_consumer, "paper-gateway", stop_event=stop)
            launch(LiveExecutionService.run_order_stream_consumer, "live-gateway", stop_event=stop)
            launch(execution.run_worker, "owner", 0, stop)
            wait_until(lambda: len(calculated) == len(actors), trace, 60)

            def ready(phase):
                for item in actors:
                    key = item["scope"], str(item["session"].pk), item["instrument"].pk
                    state = contexts[key].get_runtime_state(key[2])
                    if state.get("phase", "CLOSED") != phase:
                        return False
                return not RuntimeOutbox.objects.filter(published_at__isnull=True, topic="runtime").exists()

            for cycle in range(-1, cycles):
                # Warmup is one full round trip. Synthetic event time advances;
                # all measured durations remain the real monotonic wall clock.
                measured = cycle >= 0
                for intent, price in (("ENTRY", 101), ("EXIT", 94)):
                    if intent == "ENTRY":
                        # Set the forming candle above EMA, then close it with the
                        # next minute's tick; no fixture edits bypass ingestion.
                        for item in actors:
                            feed.ingest_observation(item["instrument"].sym_ticker, {"price": 101}, 1, clock.epoch, time.time())
                        clock.advance()
                    trace.begin(actors, cycle, intent, measured)
                    wave_ready = time.perf_counter_ns()
                    for item in actors:
                        key = item["scope"], str(item["session"].pk), item["instrument"].pk
                        row = trace.current[key]
                        row["marks"]["source_callback"] = time.perf_counter_ns()
                        row["marks"]["wave_started"] = wave_ready
                        feed.ingest_observation(item["instrument"].sym_ticker, {"price": price}, 1, clock.epoch, time.time())
                        row["marks"]["ingested"] = time.perf_counter_ns()
                    wait_until(lambda: trace.wave_complete(actors), trace)
                    wait_until(lambda: ready("OPEN" if intent == "ENTRY" else "CLOSED"), trace)
                    if not measured:
                        print(f"  warmup {intent} settled", flush=True)
                    if intent == "EXIT":
                        test.assertFalse(PaperPosition.objects.filter(account__user=user).exists())
                        test.assertFalse(LivePosition.objects.filter(user=user).exists())
                    # Outbox convergence restores funds/risk and exercises next-tick behavior.
                    wait_until(lambda: not RuntimeOutbox.objects.filter(published_at__isnull=True).exists(), trace)
            for model in (PaperOrder, LiveOrder):
                query = model.objects.filter(account__user=user) if model is PaperOrder else model.objects.filter(user=user)
                test.assertEqual(query.count(), per_scope * (cycles + 1) * 2)
                test.assertFalse(query.exclude(status="FILLED").exists())
            test.assertEqual(PaperTrade.objects.filter(account__user=user).count(), per_scope * (cycles + 1))
            test.assertEqual(LiveTrade.objects.filter(user=user).count(), per_scope * (cycles + 1))
            test.assertEqual(len(duplicates), per_scope * (cycles + 1) * 2)
            for trade in LiveTrade.objects.filter(user=user):
                test.assertEqual((trade.quantity, trade.entry_price, trade.exit_price, trade.gross_pnl), (1, 101, 94, -7))
            for item in actors:
                if item["scope"] == "paper":
                    item["account"].refresh_from_db()
                    test.assertEqual(item["account"].current_balance, 10000 - (cycles + 1) * 7)
                    test.assertEqual(item["account"].margin_used, 0)
                else:
                    test.assertEqual(LiveOrder.objects.filter(session=item["session"], strategy_version=item["version"]).count(), (cycles + 1) * 2)
        except Exception:
            print("Failed case diagnostics: " + json.dumps({
                "case": name, "traces": trace.rows[-len(actors):],
                "states": [{"scope": key[0], "session": key[1], "instrument": key[2],
                            "state": context.get_runtime_state(key[2]),
                            "calculation": last_results.get(key)} for key, context in contexts.items()],
                "paper_orders": list(PaperOrder.objects.filter(account__user=user).values("id", "status", "side", "rejection_reason", "avg_fill_price")),
                "live_orders": list(LiveOrder.objects.filter(user=user).values("id", "status", "side", "rejection_reason")),
            }, default=str), flush=True)
            raise
        finally:
            stop.set()
            for thread in threads:
                thread.join(timeout=15)
                if thread.is_alive():
                    trace.errors.append(f"{thread.name} failed to stop")
            feed.shutdown()
            for item in actors:
                item["session"].status = "STOPPED"
                item["session"].save(update_fields=["status", "updated_at"])
                service = PaperExecutionService if item["scope"] == "paper" else LiveExecutionService
                service._publish_execution_event("STOP", item["session"])
    if trace.errors:
        raise AssertionError(trace.errors)
    measured = [row for row in trace.rows if row["measured"]]
    stages = {"tick_to_request": ("source_callback", "request_queued"),
              "request_to_stream": ("request_queued", "stream_published"),
              "publication_to_gateway": ("publication_started", "gateway_started"),
              "tick_to_gateway": ("source_callback", "gateway_started"),
              "tick_to_broker_send": ("source_callback", "broker_sent"),
              "broker_round_trip": ("broker_sent", "broker_ack_received"),
              "tick_to_broker_ack": ("source_callback", "broker_ack_received"),
              "tick_to_durable_ack": ("source_callback", "durable_ack"),
              "tick_to_durable_fill": ("source_callback", "durable_fill"),
              "tick_to_runtime_projection": ("source_callback", "runtime_projected")}
    groups = []
    for scope in ("paper", "live"):
        for intent in ("ENTRY", "EXIT"):
            rows = [row for row in measured if row["scope"] == scope and row["intent"] == intent]
            groups.append({"scope": scope, "intent": intent, "stages": {
                stage: percentile([(row["marks"][end] - row["marks"][start]) / 1e6 for row in rows
                                   if end in row["marks"] and start in row["marks"]])
                for stage, (start, end) in stages.items()}})
    per_actor = []
    for item in actors:
        for intent in ("ENTRY", "EXIT"):
            rows = [row for row in measured if row["scope"] == item["scope"] and row["session"] == str(item["session"].pk)
                    and row["instrument"] == item["instrument"].pk and row["intent"] == intent]
            per_actor.append({"scope": item["scope"], "session": str(item["session"].pk),
                "instrument": item["instrument"].pk, "intent": intent,
                "stages": {stage: percentile([(row["marks"][end] - row["marks"][start]) / 1e6
                    for row in rows if start in row["marks"] and end in row["marks"]])
                    for stage, (start, end) in stages.items()}})
    result = {"name": name, "instruments_per_scope": per_scope, "shared_live_account": shared_account,
              "measured_cycles": cycles, "warmup_cycles": 1, "broker_ack_delay_ms": ack_ms,
              "broker_fill_delay_after_ack_ms": fill_ms, "measured_orders": len(measured),
              "duplicate_fill_observations_checked": len(duplicates), "errors": trace.errors,
              "groups": groups, "per_actor": per_actor, "traces": measured}
    REPORT["cases"].append(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="quantnest-e2e-") as directory:
        port, token = free_port(), uuid.uuid4().hex
        command = ["redis-server"] if shutil.which("redis-server") else ["wsl", "-d", "Ubuntu", "--exec", "redis-server"]
        command += ["--bind", "127.0.0.1", "--port", str(port), "--save", "", "--appendonly", "no",
                    "--requirepass", token, "--protected-mode", "yes"]
        import redis
        url = f"redis://:{token}@127.0.0.1:{port}/0"
        client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            end = time.monotonic() + 20
            while True:
                try:
                    client.ping()
                    break
                except redis.RedisError:
                    if process.poll() is not None or time.monotonic() >= end:
                        raise RuntimeError("Private Redis test server did not start")
                    time.sleep(.1)
            client.set("quantnest:e2e-server", token)
            os.environ.update({"DJANGO_SETTINGS_MODULE": "quantnest_runtime.e2e_settings", "DEBUG": "False",
                "QUANTNEST_E2E_REDIS_URL": url, "QUANTNEST_E2E_NOTIFY_PORT": str(free_port()),
                "QUANTNEST_RUNTIME_DIR": directory, "MARKET_TICK_CAPACITY": "1024",
                "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMBA_NUM_THREADS": "1"})
            import django
            django.setup()
            from django.test import TransactionTestCase
            from django.test.runner import DiscoverRunner

            class EndToEndChecks(TransactionTestCase):
                def test_transports(self):
                    scenarios = [("single-account", 1, 3 if args.quick else 20, False, 0, 0)]
                    if not args.quick:
                        scenarios += [("parallel-accounts", 4, 10, False, 0, 0),
                                      ("shared-live-account", 4, 10, True, 0, 0),
                                      ("broker-250ms", 1, 10, False, 250, 100)]
                    for name, count, cycles, shared, ack, fill in scenarios:
                        print(f"Running {name}: {count * 2} actors...", flush=True)
                        result = run_case(self, name, count, cycles, shared_account=shared, ack_ms=ack, fill_ms=fill)
                        for group in result["groups"]:
                            stage = "tick_to_durable_fill" if group["scope"] == "paper" else "tick_to_broker_ack"
                            print(f"  {group['scope']} {group['intent']}: {group['stages'][stage]}", flush=True)
                        args.output.write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
                        # Only clear this private server, after checking its unique marker.
                        self.assertEqual(client.get("quantnest:e2e-server"), token.encode())
                        client.flushdb()
                        client.set("quantnest:e2e-server", token)

            # Register a concrete unittest class for Django's standard DB runner.
            import unittest
            suite = unittest.TestSuite([EndToEndChecks("test_transports")])
            class Runner(DiscoverRunner):
                def build_suite(self, *args, **kwargs):
                    return suite
            REPORT.update({"recorded_at": datetime.now(timezone.utc).isoformat(),
                "environment": {"os": platform.platform(), "cpu": platform.processor(),
                                "logical_cpus": os.cpu_count(), "python": platform.python_version(),
                                "redis_version": client.info("server")["redis_version"]},
                "workers": {"execution": 1, "calculation_per_owner": 1, "gateways": 1, "gateway_concurrency_per_scope": 2},
                "limitations": ["Synthetic normalized feed, simulated broker adapter and fill updates; no actual exchange/broker network.",
                    "Real private Redis Streams/cache/leases/Lua, real disposable PostgreSQL, real owner/calculation/gateways/outbox.",
                    "Synthetic clock advances completed minutes; fixture calendar allows weekends/all-day; durations use real monotonic time.",
                    "One owner process running in a test thread, real spawned calculation process, same-process gateway/control/outbox threads.",
                    "Redis runs in WSL on Windows with persistence disabled; PostgreSQL and Python run on Windows.",
                    "Warm startup excluded; finite round-trip batches, not sustained production capacity or Oracle ARM timings."],
                "source_sha256": {name: hashlib.sha256((Path(__file__).resolve().parents[1] / name).read_bytes()).hexdigest()
                                  for name in ("quantnest_runtime/e2e_benchmark.py", "quantnest_runtime/execution.py",
                                      "strategy_engine/order_queue.py", "core/cache_api.py",
                                      "paper_trading/services.py", "live_trading/services.py")}})
            failures = Runner(verbosity=1, interactive=False).run_tests([])
            REPORT["test_failures"] = failures
            args.output.write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
            if failures:
                raise SystemExit(1)
            print(f"Report: {args.output.resolve()}", flush=True)
        finally:
            try:
                if client.get("quantnest:e2e-server") == token.encode():
                    client.shutdown(nosave=True)
            except redis.RedisError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
