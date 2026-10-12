"""Isolated instrument fairness benchmark of the real execution owner loop.

Run from backend: python -m quantnest_runtime.latency_benchmark --output PATH
No trading database, Redis server, broker, or running runtime service is used.
Synthetic fixtures use private mmap files and an ephemeral loopback UDP socket.
This measures local decisions, not exchange execution or broker fill latency.
"""
import argparse
import hashlib
import json
import math
import multiprocessing
import os
import platform
import socket
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
from datetime import datetime, time as day_time, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def _forbidden(*args, **kwargs):
    raise AssertionError("External I/O or order publication attempted by isolated benchmark")


def _setup():
    # Set, rather than default, so a developer's service settings cannot leak in.
    os.environ["DJANGO_SETTINGS_MODULE"] = "research.test_settings"
    os.environ["DEBUG"] = "False"
    import django
    django.setup()


def _initialize_calculation():
    _setup()
    from django.db.backends.base.base import BaseDatabaseWrapper
    import core.redis
    from brokers.services import BrokerService
    BaseDatabaseWrapper.ensure_connection = _forbidden
    core.redis.runtime_redis = _forbidden
    BrokerService.get_adapter = _forbidden
    # Calculation workers need only local mmap data and process-pool IPC.
    socket.socket.connect = _forbidden
    socket.socket.connect_ex = _forbidden


def _timed_calculation(task):
    from quantnest_runtime.calculation import evaluate
    started = time.perf_counter_ns()
    result = evaluate(task)
    result["_benchmark"] = {
        "started_ns": started, "finished_ns": time.perf_counter_ns(),
        "submitted_ns": task["_benchmark_submitted_ns"],
        "ready_ns": task["_benchmark_ready_ns"], "wave": task["_benchmark_wave"],
    }
    return result


def distribution(values):
    ordered = sorted(values)
    if not ordered:
        return {"count": 0, "p50_ms": None, "p95_ms": None, "p99_ms": None, "max_ms": None}
    def percentile(p):
        return round(ordered[max(0, math.ceil(len(ordered) * p) - 1)], 4)
    return {"count": len(ordered), "p50_ms": percentile(.5), "p95_ms": percentile(.95),
            "p99_ms": percentile(.99), "max_ms": round(ordered[-1], 4)}


class Recorder:
    def __init__(self):
        self.condition = threading.Condition()
        self.pending_ticks = defaultdict(deque)
        self.ready = {}
        self.ticks = defaultdict(lambda: defaultdict(list))
        self.calculations = defaultdict(list)
        self.cold_calculations = set()
        self.expected_ticks = {}
        self.tick_counts = defaultdict(int)
        self.expected_calculations = {}
        self.calculation_counts = defaultdict(int)
        self.actor_count = 0
        self.errors = []

    def tick(self, actor, original, price):
        sequence, received = self.pending_ticks[actor.symbol].popleft()
        started = time.perf_counter_ns()
        original(actor, price)
        finished = time.perf_counter_ns()
        wave, ready = self.ready.get(actor.symbol, (0, started))
        if wave in self.expected_ticks:
            with self.condition:
                if wave > 0:
                    self.ticks[wave][actor.symbol].append({
                        "sequence": sequence, "ready_ms": (finished - ready) / 1e6,
                        "receipt_ms": (time.time() - received) * 1000,
                        "service_ms": (finished - started) / 1e6,
                    })
                self.tick_counts[wave] += 1
                # Wake the observer once per full wave, not on every instrument.
                # Otherwise observer/owner GIL contention distorts the scan spread.
                if self.tick_counts[wave] == self.expected_ticks[wave]:
                    self.condition.notify_all()

    def calculation(self, actor, original, result):
        timing = result.pop("_benchmark")
        if result.get("empty"):
            raise AssertionError("Synthetic history did not produce a completed calculation")
        if result["exit"][0] or result["entry"][0]:
            raise AssertionError("Benchmark fixture unexpectedly proposed an order")
        original(actor, result)
        applied = time.perf_counter_ns()
        if not timing["ready_ns"] <= timing["submitted_ns"] <= timing["started_ns"] <= timing["finished_ns"] <= applied:
            raise AssertionError("Process clocks or calculation timestamps are inconsistent")
        with self.condition:
            if timing["wave"] > 0:
                self.calculations[actor.symbol].append({
                    "wave": timing["wave"],
                    "admission_ms": (timing["submitted_ns"] - timing["ready_ns"]) / 1e6,
                    "pool_wait_ms": (timing["started_ns"] - timing["submitted_ns"]) / 1e6,
                    "compute_ms": (timing["finished_ns"] - timing["started_ns"]) / 1e6,
                    "ready_to_applied_ms": (applied - timing["ready_ns"]) / 1e6,
                })
            else:
                self.cold_calculations.add(actor.symbol)
            if timing["wave"] in self.expected_calculations:
                self.calculation_counts[timing["wave"]] += 1
                if self.calculation_counts[timing["wave"]] == self.expected_calculations[timing["wave"]]:
                    self.condition.notify_all()
            elif len(self.cold_calculations) == self.actor_count:
                self.condition.notify_all()

    def wait_for(self, predicate, deadline=60):
        end = time.monotonic() + deadline
        with self.condition:
            while not predicate():
                if self.errors:
                    raise RuntimeError(self.errors[0])
                remaining = end - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Benchmark did not receive every expected instrument decision")
                self.condition.wait(min(remaining, .1))


class Wakeup:
    """Pause at recv boundaries to publish a simultaneous wave to every actor.

    After resume the real socket and configured polling timeout are used.
    Publication time is reported separately from ready-to-decision latency.
    """
    def __init__(self, interval):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("127.0.0.1", 0))
        self.address = self.socket.getsockname()
        self.socket.settimeout(interval)
        self.condition = threading.Condition()
        self.paused = self.blocked = self.closed = False

    def recv(self, length):
        with self.condition:
            self.blocked = True
            self.condition.notify_all()
            while self.paused and not self.closed:
                self.condition.wait(.1)
            self.blocked = False
        return self.socket.recv(length)

    def pause(self):
        with self.condition:
            self.paused = True
            if not self.condition.wait_for(lambda: self.blocked or self.closed, timeout=10):
                raise TimeoutError("Owner failed to reach a scan boundary")

    def resume(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(b"benchmark", self.address)
        with self.condition:
            self.paused = False
            self.condition.notify_all()

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify_all()
        self.socket.close()


class LocalLease:
    def __init__(self, name):
        self.key, self.token = f"benchmark:{name}", "isolated"

    def acquire(self):
        return True

    renew = acquire

    def release(self):
        pass


class LocalControl:
    def xread(self, *args, **kwargs):
        return []

    xrevrange = xread

    def set(self, *args, **kwargs):
        return True


def _configuration(instruments, heavy=False):
    rules = []
    periods = (10, 20, 50, 100, 200, 500) if heavy else (20,)
    for operand in (("EMA", "RSI") if heavy else ("EMA",)):
        for period in periods:
            rules.append({"operand_a_type": operand, "operand_a_params": {"period": period},
                          "comparison": "LT", "operand_b_type": "CONSTANT",
                          "operand_b_params": {"value": -1000000}})
    return {
        "name": "Latency fixture", "strategy_type": "INTRADAY", "market_type": "INDIAN",
        "exchange": "NSE", "instrument_type": "STOCK",
        "entry_order_config": {"entry_side": "BUY", "entry_group_operator": "OR"},
        "exit_order_config": {}, "time_rule": {"timezone": "Asia/Kolkata", "candle_timeframe": "1m"},
        "special_event_filter": {}, "auto_disable_rules": [],
        "position_sizing_rule": {"sizing_method": "FIXED", "fixed_quantity": 1},
        "watchlist_instruments": [{"instrument_id": i, "execution_routes": [{"route_type": "DIRECT"}]}
                                  for i in instruments],
        "rule_groups": [{"name": "Never exit", "rule_type": "EXIT", "is_active": True,
                         "logical_operator": "OR", "rules": rules}],
    }


def _history(calendar):
    """Eight full sessions plus 250 minutes, leaving room for measured waves."""
    import numpy as np
    day = datetime.now(calendar.zone).date() - timedelta(days=1)
    while not calendar.is_trading_day(day):
        day -= timedelta(days=1)
    days = [day]
    while len(days) < 9:
        day -= timedelta(days=1)
        if calendar.is_trading_day(day):
            days.append(day)
    epochs = [calendar.session_open(day).timestamp() + minute * 60
              for day in reversed(days) for minute in range(250 if day == days[0] else 375)]
    epochs = np.asarray(epochs)
    prices = 100 + np.sin(np.arange(len(epochs)) / 20)
    return np.column_stack((prices, prices + 1, prices - 1, prices, np.ones(len(prices)), epochs))


def run_case(name, count, waves, warmup, workers=1, reverse=False, burst=1,
             burst_position="first", calculate=False, mixed=False):
    from django.conf import settings
    from django.db.backends.base.base import BaseDatabaseWrapper
    from django.test import override_settings
    from marketdata.calendar import MarketSessionCalendar
    from marketdata.shared_memory import SharedMemoryManager
    from quantnest_runtime import execution
    from quantnest_runtime.telemetry import RuntimeMetrics
    from strategy_engine import engine
    from strategy_engine.context import PaperSessionContext, LiveSessionContext
    from strategy_engine.router import StrategyOrderRouter
    from risk_management.metrics import empty_metrics

    recorder, stop = Recorder(), threading.Event()
    recorder.actor_count = count
    channel = Wakeup(settings.EXECUTION_SCAN_INTERVAL)
    original_protection, original_apply = engine.evaluate_protection, engine.apply_calculation
    writers, rows, groups = [], [], {}
    calendar = MarketSessionCalendar("NSE", "Asia/Kolkata", day_time(9, 15), day_time(15, 30))
    history = _history(calendar)
    publish_times = []
    published_sequences = defaultdict(list)
    calculation_pool = None
    thread = None
    burst_ordinal = (count - 1 if reverse else 0) if burst_position == "first" else (0 if reverse else count - 1)

    def group_for(ordinal):
        return count if mixed and ordinal == 0 else ordinal // 5

    class Reader(SharedMemoryManager):
        def read_ticks(self, after_sequence, limit=None):
            ticks, gap = super().read_ticks(after_sequence, limit)
            recorder.pending_ticks[self.symbol].extend((int(row[0]), row[2]) for row in ticks)
            if gap:
                recorder.errors.append(f"Unexpected lost tick for {self.symbol}")
            return ticks, gap

    class MeasuredPool:
        def __init__(self, max_workers, **kwargs):
            self.pool = ProcessPoolExecutor(max_workers=max_workers,
                mp_context=multiprocessing.get_context("spawn"), initializer=_initialize_calculation)
            nonlocal calculation_pool
            calculation_pool = self.pool

        def submit(self, function, task):
            wave, ready = recorder.ready.get(task["symbol"], (0, time.perf_counter_ns()))
            task = {**task, "_benchmark_wave": wave, "_benchmark_ready_ns": ready,
                    "_benchmark_submitted_ns": time.perf_counter_ns()}
            return self.pool.submit(_timed_calculation, task)

        def shutdown(self, **kwargs):
            self.pool.shutdown(**kwargs)

    def snapshot(index, contexts):
        for context in groups.values():
            context._execution_context_updated = time.monotonic()
        return [dict(row) for row in rows]

    def owner():
        try:
            execution.run_worker(0, stop)
        except Exception as error:
            with recorder.condition:
                recorder.errors.append(f"{type(error).__name__}: {error}")
                recorder.condition.notify_all()

    with TemporaryDirectory(prefix="quantnest-latency-") as directory, ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {"QUANTNEST_RUNTIME_DIR": directory,
                                                   "MARKET_TICK_CAPACITY": "1024"}))
        # Assign every fixture to this private owner; normal deployment partitions
        # across owners, so the case count means instruments per owner.
        stack.enter_context(override_settings(CALCULATION_WORKERS=workers,
            EXECUTION_WORKERS=1, EXECUTION_NODE_COUNT=1, EXECUTION_NODE_INDEX=0))
        stack.enter_context(patch.object(BaseDatabaseWrapper, "ensure_connection", _forbidden))
        stack.enter_context(patch("core.redis.runtime_redis", _forbidden))
        stack.enter_context(patch("brokers.services.BrokerService.get_adapter", _forbidden))
        stack.enter_context(patch("strategy_engine.order_queue.publish_order", _forbidden))
        stack.enter_context(patch("core.runtime_projection.snapshot", return_value={}))
        stack.enter_context(patch("core.runtime_projection.checkpoint", return_value=None))
        stack.enter_context(patch.object(execution, "runtime_redis", return_value=LocalControl()))
        stack.enter_context(patch.object(execution, "Lease", LocalLease))
        stack.enter_context(patch.object(execution, "_snapshot", snapshot))
        stack.enter_context(patch.object(execution, "ProcessPoolExecutor", MeasuredPool))
        stack.enter_context(patch("marketdata.shared_memory.SharedMemoryManager", Reader))
        stack.enter_context(patch("quantnest_runtime.signals.notification_socket", return_value=channel))
        stack.enter_context(patch("quantnest_runtime.telemetry.metrics", RuntimeMetrics()))
        stack.enter_context(patch.object(engine, "evaluate_protection",
            lambda actor, price: recorder.tick(actor, original_protection, price)))
        stack.enter_context(patch.object(engine, "apply_calculation",
            lambda actor, result: recorder.calculation(actor, original_apply, result)))
        # Restore the singleton's publisher so this benchmark cannot affect other tests.
        stack.enter_context(patch.object(StrategyOrderRouter(), "_publisher", None, create=True))
        try:
            for ordinal in range(count):
                instrument, symbol = ordinal + 1, f"BENCH-{ordinal + 1:03d}"
                # Multiple instruments per strategy; both paper/live contexts and four tenants.
                # The heavy actor has a separate strategy/version, as in a real deployment.
                group = group_for(ordinal)
                scope = "paper" if group % 2 == 0 else "live"
                if group not in groups:
                    cls = PaperSessionContext if scope == "paper" else LiveSessionContext
                    with patch.object(cls, "_fetch_user_id", return_value=group % 4 + 1):
                        context = cls(str(group + 1), str(group + 1))
                    context._cached_capital = 100000
                    context._cached_risk_stats = empty_metrics(100000, datetime.now(timezone.utc))
                    context._execution_context_updated = time.monotonic()
                    groups[group] = context
                context = groups[group]
                context._runtime_l1[instrument] = {"phase": "OPEN", "side": "BUY", "quantity": 1,
                    "avg_price": 100, "peak_price": 100, "protected_stop_price": 1,
                    "protected_target_price": 10000, "entry_time": "2026-01-01T00:00:00+00:00"}
                writer = SharedMemoryManager(symbol, "1m", create=True, max_size=len(history) + waves + warmup + 4)
                with writer._locked():
                    writer.array[:len(history)] = history
                    writer.meta_array[0] = len(history) - 1
                    writer.meta_array[3] = writer.meta_array[4] = 1
                writer.update_current_candle(100, 1, timestamp=history[-1, 5])
                writers.append(writer)
                config = _configuration([other + 1 for other in range(count) if group_for(other) == group],
                                        heavy=mixed and ordinal == 0)
                rows.append({"scope": scope, "session": context.session_id, "strategy": context.strategy_id,
                    "instrument": instrument, "symbol": symbol, "context": context, "config": config,
                    "calendar": calendar, "events": {}, "status": "RUNNING",
                    "configuration_key": symbol, "version_id": group + 1,
                    "market_ready": True, "runtime_ready": True,
                    "contract": {"lot_size": 1, "tick_size": "0.05"}})
            if reverse:
                rows.reverse()
            thread = threading.Thread(target=owner, name="isolated-benchmark-owner")
            thread.start()
            recorder.wait_for(lambda: len(recorder.cold_calculations) == count)
            channel.pause()
            started = time.perf_counter()
            for wave in range(-warmup + 1, waves + 1):
                receipt = time.time()
                publish_started = time.perf_counter_ns()
                # No actor reads while fixtures publish. All are ready on the same release.
                for ordinal, writer in enumerate(writers):
                    number = burst if ordinal == burst_ordinal else 1
                    stamp = history[-1, 5] + ((wave + warmup) * 60 if calculate else 0)
                    for _ in range(number):
                        sequence = writer.update_current_candle(100, 1, timestamp=stamp, received_time=receipt)
                        if wave > 0:
                            published_sequences[writer.symbol].append(sequence)
                    if calculate:
                        # A new completed-history observation must invalidate analytical caches.
                        with writer._locked():
                            writer.meta_array[4] += 1
                ready = time.perf_counter_ns()
                if wave > 0:
                    publish_times.append((ready - publish_started) / 1e6)
                recorder.ready = {writer.symbol: (wave, ready) for writer in writers}
                recorder.expected_ticks[wave] = count - 1 + burst
                recorder.tick_counts[wave] = 0
                if calculate:
                    recorder.expected_calculations[wave] = count
                    recorder.calculation_counts[wave] = 0
                channel.resume()
                recorder.wait_for(lambda: recorder.tick_counts[wave] == recorder.expected_ticks[wave])
                if calculate:
                    recorder.wait_for(lambda: recorder.calculation_counts[wave] == count)
                channel.pause()
            elapsed = time.perf_counter() - started
        finally:
            stop.set()
            channel.resume()
            if thread:
                thread.join(timeout=15)
                if thread.is_alive():
                    raise RuntimeError("Isolated execution worker did not stop")
            else:
                channel.close()
            if calculation_pool:
                calculation_pool.shutdown(wait=True, cancel_futures=True)
            for writer in writers:
                writer.close()
        if recorder.errors:
            raise RuntimeError(recorder.errors[0])

    instruments = []
    spreads = []
    first_symbol, last_symbol = rows[0]["symbol"], rows[-1]["symbol"]
    paired = []
    for wave in range(1, waves + 1):
        first_ticks = [recorder.ticks[wave][writer.symbol][0]["ready_ms"] for writer in writers]
        spreads.append(max(first_ticks) - min(first_ticks))
        paired.append(recorder.ticks[wave][last_symbol][0]["ready_ms"] -
                      recorder.ticks[wave][first_symbol][0]["ready_ms"])
    for scan_index, row in enumerate(rows):
        symbol = row["symbol"]
        ticks = [tick for wave in range(1, waves + 1) for tick in recorder.ticks[wave][symbol]]
        sequences = [tick["sequence"] for tick in ticks]
        if sequences != published_sequences[symbol]:
            raise AssertionError(f"Lost, duplicated, or out-of-order tick: {symbol}")
        calculations = recorder.calculations[symbol] if calculate else []
        if calculate and sorted(item["wave"] for item in calculations) != list(range(1, waves + 1)):
            raise AssertionError(f"Lost or duplicate calculation: {symbol}")
        instruments.append({"symbol": symbol, "scan_index": scan_index, "scope": row["scope"],
            "session": row["session"], "tenant": row["context"].user_id,
            "heavy": mixed and symbol == writers[0].symbol,
            "first_tick_ready_ms": distribution([recorder.ticks[wave][symbol][0]["ready_ms"] for wave in range(1, waves + 1)]),
            "tick_receipt_ms": distribution([item["receipt_ms"] for item in ticks]),
            "protection_service_ms": distribution([item["service_ms"] for item in ticks]),
            "calculation": {key: distribution([item[key] for item in calculations])
                            for key in ("admission_ms", "pool_wait_ms", "compute_ms", "ready_to_applied_ms")}})
    return {"name": name, "instrument_count": count, "execution_owners": 1, "measured_waves": waves,
            "warmup_waves": warmup, "calculation_workers": workers, "burst_ticks": burst,
            "burst_scan_position": burst_position,
            "elapsed_seconds": round(elapsed, 3), "fixture_publication_ms": distribution(publish_times),
            "same_wave_first_tick_spread_ms": distribution(spreads),
            "last_minus_first_scan_ms": distribution(paired),
            "validated_tick_count": sum(len(values) for values in published_sequences.values()),
            "validated_calculation_count": count * waves if calculate else 0,
            "lost_or_duplicate_ticks": 0, "errors": recorder.errors, "instruments": instruments}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--waves", type=int, default=80)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--quick", action="store_true", help="Small smoke run, not a capacity benchmark")
    args = parser.parse_args()
    if not 1 <= args.waves <= 80 or not 1 <= args.warmup <= 20:
        parser.error("waves must be 1..80; warmup must be 1..20")
    _setup()
    from django.conf import settings
    cases = [(f"equal-{count}", {"count": count}) for count in ([10] if args.quick else [10, 50, 100, 200])]
    if not args.quick:
        cases.extend([("equal-100-reversed", {"count": 100, "reverse": True}),
                      ("burst-100-first", {"count": 100, "burst": settings.EXECUTION_TICK_BATCH}),
                      ("burst-100-last", {"count": 100, "burst": settings.EXECUTION_TICK_BATCH, "burst_position": "last"}),
                      ("backlog-100-first", {"count": 100, "burst": settings.EXECUTION_TICK_BATCH * 2})])
    for workers in ([1] if args.quick else [1, 2]):
        for mixed in (False, True):
            cases.append((f"calculation-{'mixed' if mixed else 'equal'}-{workers}-cpu",
                          {"count": 12, "workers": workers, "calculate": True, "mixed": mixed}))
    report = {"recorded_at": datetime.now(timezone.utc).isoformat(),
        "environment": {"os": platform.platform(), "cpu": platform.processor(),
                        "logical_cpus": os.cpu_count(), "python": platform.python_version()},
        "source_sha256": {name: hashlib.sha256((Path(__file__).resolve().parents[1] / name).read_bytes()).hexdigest()
                          for name in ("quantnest_runtime/execution.py", "quantnest_runtime/calculation.py",
                              "quantnest_runtime/latency_benchmark.py", "strategy_engine/engine.py",
                              "strategy_engine/context.py", "marketdata/shared_memory.py")},
        "runtime": {key: getattr(settings, key) for key in ("EXECUTION_WORKERS", "CALCULATION_WORKERS",
                    "EXECUTION_SCAN_INTERVAL", "EXECUTION_TICK_BATCH", "EXECUTION_MAX_ACTORS", "CALCULATION_CACHE_MB")},
        "method": "Real run_worker, real mmap ticks, real Paper/LiveSessionContext, real protection and calculation functions; private UDP wakeups; fake cold control/leases; no external services or orders.",
        "limitations": ["One execution owner per case, not a multi-node benchmark.",
                        "Synthetic bars/ticks with false exit conditions; no order gateway, broker, network feed, or fill latency.",
                        "Warm process/cache startup is excluded; new history invalidates calculation caches in calculation cases.",
                        "All ticks in a wave become readable at the same scan boundary; ready latency excludes fixture publication.",
                        "Finite batch test, not a sustained-rate capacity or HFT guarantee.",
                        "Instrumented wall times include recorder overhead and Windows scheduling/file-lock behavior."],
        "cases": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for name, options in cases:
        print(f"Running {name}...", flush=True)
        result = run_case(name, waves=min(args.waves, 8) if options.get("calculate") else args.waves,
                          warmup=min(args.warmup, 2) if options.get("calculate") else args.warmup, **options)
        report["cases"].append(result)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        spread = result["same_wave_first_tick_spread_ms"]["p95_ms"]
        print(f"  validated {result['validated_tick_count']} ticks, {result['validated_calculation_count']} calculations; p95 instrument spread {spread} ms", flush=True)
    print(f"Report: {args.output.resolve()}", flush=True)


if __name__ == "__main__":
    main()
