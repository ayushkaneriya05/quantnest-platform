"""Fixed execution workers with single-owner actors and bounded fair CPU admission."""
import json
import logging
import multiprocessing
import queue
import socket
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.conf import settings
from django.db import close_old_connections

from core.redis import runtime_redis
from core.shared_state_store import shared_state_store
from quantnest_runtime.ownership import Lease, partition

logger = logging.getLogger(__name__)


@dataclass
class Actor:
    scope: str
    session: str
    strategy: str
    instrument: int
    symbol: str
    context: object
    config: dict
    calendar: object
    events: dict
    market: object
    lease: object
    status: str
    configuration_key: str
    version_id: int
    last_tick: int = 0
    last_candle: tuple = ()
    generation: int = 0
    market_ready: bool = True
    runtime_ready: bool = True
    account_active: bool = False
    last_entry_candle: str = ""
    last_gap_revision: int = 0
    in_flight: bool = False
    gap: bool = False
    watch: dict = field(default_factory=dict)
    program: object = field(init=False)

    def __post_init__(self):
        from trading_domain.strategy import StrategyProgram
        self.program = StrategyProgram(self.config, session_minutes=self.calendar.session_minutes,
                                       active_event_cache=self.events)

    @property
    def key(self):
        return self.scope, self.session, self.instrument


def _apply_controls(actor, row):
    resumed = actor.status != "RUNNING" and row["status"] == "RUNNING"
    recovered = (not actor.market_ready and row["market_ready"]) or (not actor.runtime_ready and row["runtime_ready"])
    if resumed:
        actor.gap = False  # Explicit user resume acknowledges the recorded gap.
    if resumed or recovered:
        actor.last_candle = ()
    actor.status, actor.events = row["status"], row["events"]
    actor.program.active_event_cache = actor.events
    actor.market_ready, actor.runtime_ready = row["market_ready"], row["runtime_ready"]
    actor.account_active = row["account_active"]


def _snapshot(index, contexts):
    """Cold recovery/context path. Never called by a tick or calculation worker."""
    from common.models import RuntimeOutbox, RuntimeAssignment
    from instruments.models import Instrument
    from live_trading.models import TradingSession
    from paper_trading.models import PaperTradingSession
    from marketdata.calendar import MarketSessionCalendar
    from marketdata.event_context import load_events
    from marketdata.live_feed import LiveMarketDataRegistry
    from strategy_engine.context import LiveSessionContext, PaperSessionContext
    from strategy_engine.runtime import StrategyRuntimeState
    from trading_domain.configuration import requirements
    rows = []
    total_workers = settings.EXECUTION_WORKERS * settings.EXECUTION_NODE_COUNT
    global_index = settings.EXECUTION_NODE_INDEX * settings.EXECUTION_WORKERS + index
    assigned = defaultdict(lambda: defaultdict(list))
    shards = [shard for shard in range(settings.EXECUTION_SHARDS) if shard % total_workers == global_index]
    for assignment in RuntimeAssignment.objects.filter(shard__in=shards, scope__in=settings.EXECUTION_ENABLED_SCOPES):
        assigned[assignment.scope][assignment.session_id].append(assignment.instrument_id)
    for scope, model, context_type in (("live", TradingSession, LiveSessionContext),
                                       ("paper", PaperTradingSession, PaperSessionContext)):
        if scope not in settings.EXECUTION_ENABLED_SCOPES:
            continue
        sessions = model.objects.filter(pk__in=assigned[scope], status__in=["RUNNING", "PAUSED", "STOPPING", "ERROR"]).select_related(
            "allocation__deployed_version", "user")
        for session in sessions:
            from core.lifecycle import finalize_stop
            if finalize_stop(scope, session):
                continue
            version = session.allocation.deployed_version if session.allocation_id else None
            if version is None:
                continue
            config = version.config_snapshot
            owned = assigned[scope][str(session.pk)]
            if not owned:
                continue
            identity = scope, str(session.pk)
            context = contexts.get(identity)
            if context is None:
                # Recover from durable orders/positions before publishing a ready actor.
                from django.db import transaction
                with transaction.atomic():
                    if scope == "live":
                        from brokers.models import BrokerCredential
                        BrokerCredential.objects.select_for_update().get(pk=session.broker_credential_id)
                    else:
                        from paper_trading.models import PaperAccount
                        PaperAccount.objects.select_for_update().get(pk=session.account_id)
                    StrategyRuntimeState.rebuild_runtime_state_from_db(scope, str(session.pk), owned)
                    StrategyRuntimeState.ensure_risk_metrics(scope, str(session.pk))
                context = context_type(str(session.pk), str(session.strategy_id))
                contexts[identity] = context
            if scope == "paper":
                if not shared_state_store.get_session_funds(scope, str(session.pk)):
                    from django.db import transaction
                    from paper_trading.models import PaperAccount
                    from paper_trading.services import _refresh_paper_account_funds_after_commit
                    with transaction.atomic():
                        account = PaperAccount.objects.select_for_update().get(pk=session.account_id)
                        _refresh_paper_account_funds_after_commit(account)
            context.refresh_execution_context()
            runtime_ready = not RuntimeOutbox.objects.filter(
                topic="runtime", published_at__isnull=True,
                aggregate_key__startswith=f"{scope}:{session.pk}:").exists()
            for instrument in Instrument.objects.filter(pk__in=owned):
                metadata = getattr(context, "market_metadata", {})
                cached = metadata.get(instrument.pk)
                calendar = cached["calendar"] if cached else MarketSessionCalendar.for_instrument(instrument)
                required = (cached["required"] if cached and cached["version"] == version.pk
                            else requirements(config, calendar.session_minutes)[2])
                market_ready = LiveMarketDataRegistry.is_ready(instrument.sym_ticker, required, require_fresh=False)
                today = datetime.now(calendar.zone).date()
                context.account_key = f"broker:{session.broker_credential_id}" if scope == "live" else f"paper:{session.account_id}"
                if cached is None or time.monotonic() - cached["loaded"] > 60 or cached["version"] != version.pk:
                    calendar.load_holidays(today - timedelta(days=max(365, required // calendar.session_minutes * 2)),
                                           today + timedelta(days=14))
                    cached = {"calendar": calendar, "required": required,
                              "events": load_events(instrument.pk, today, today + timedelta(days=2)),
                              "loaded": time.monotonic(), "version": version.pk}
                    metadata[instrument.pk] = cached
                    context.market_metadata = metadata
                rows.append({"scope": scope, "session": str(session.pk), "strategy": str(session.strategy_id),
                             "instrument": instrument.pk, "symbol": instrument.sym_ticker, "context": context,
                             "config": config, "calendar": calendar,
                             "events": cached["events"],
                             "status": session.status, "configuration_key": f"{version.pk}:{instrument.pk}", "version_id": version.pk,
                             "market_ready": market_ready,
                              "runtime_ready": runtime_ready,
                              "account_active": session.user.is_active,
                             "contract": {"lot_size": instrument.lot_size or 1, "tick_size": str(instrument.tick_size)}})
    return rows


def run_worker(index, stop):
    from marketdata.shared_memory import SharedMemoryManager
    from quantnest_runtime.calculation import evaluate, initialize
    from quantnest_runtime.signals import notification_socket
    from strategy_engine.router import StrategyOrderRouter
    from strategy_engine.runtime import StrategyRuntimeState
    from core.runtime_projection import snapshot, stream_key, checkpoint
    from quantnest_runtime.telemetry import metrics

    actors, contexts, cursors, leases = {}, {}, {}, {}
    inbox, publications = queue.Queue(maxsize=4096), queue.Queue(maxsize=1024)
    total_workers = settings.EXECUTION_WORKERS * settings.EXECUTION_NODE_COUNT
    global_index = settings.EXECUTION_NODE_INDEX * settings.EXECUTION_WORKERS + index
    for shard in range(settings.EXECUTION_SHARDS):
        if shard % total_workers == global_index:
            lease = Lease(f"execution:{shard}")
            if not lease.acquire():
                for held in leases.values():
                    held.release()
                raise RuntimeError(f"Execution partition {shard} is already owned")
            leases[shard] = lease
    alive = threading.Event()
    alive.set()
    StrategyOrderRouter().set_publisher(publications.put_nowait)

    def background():
        last_snapshot, last_renew, last_checkpoint = 0.0, 0.0, 0.0
        # Lifecycle messages are committed invalidations. Reload PostgreSQL
        # assignments, session status and pinned configuration in _snapshot;
        # applying the message's old status would regress a later transition.
        try:
            tail = runtime_redis().xrevrange("execution_control", count=1)
            control_cursor = tail[0][0] if tail else "0-0"
        except Exception:
            logger.exception("Execution control startup failed; worker relinquishing ownership")
            alive.clear()
            return
        control_dirty = True
        while not stop.is_set() and alive.is_set():
            close_old_connections()
            try:
                for _, messages in runtime_redis().xread({"execution_control": control_cursor}, count=100):
                    for message_id, fields in messages:
                        event = json.loads(fields["payload"])
                        if event["scope"] in {"paper", "live"}:
                            control_dirty = True
                        control_cursor = message_id
                if time.monotonic() - last_renew >= 3:
                    if not all(lease.renew() for lease in leases.values()):
                        raise RuntimeError("Execution ownership was lost")
                    last_renew = time.monotonic()
                    runtime_redis().set(f"quantnest:health:execution:{global_index}",
                                       json.dumps({"at": time.time(), "latency": metrics.export()}), ex=15)
                if time.monotonic() - last_snapshot >= 3 or (control_dirty and time.monotonic() - last_snapshot >= 0.25):
                    # Tail first, then snapshot. Concurrent commits are replayed after the snapshot.
                    rows = _snapshot(index, contexts)
                    for row in rows:
                        key = stream_key(row["scope"], row["session"])
                        if key not in cursors:
                            tail = runtime_redis().xrevrange(key, count=1)
                            cursors[key] = tail[0][0] if tail else "0-0"
                    live_keys = {stream_key(row["scope"], row["session"]) for row in rows}
                    cursors_keys = set(cursors) - live_keys
                    for obsolete in cursors_keys:
                        cursors.pop(obsolete, None)
                    states = {}
                    for row in rows:
                        identity = row["scope"], row["session"]
                        if identity not in states:
                            states[identity] = snapshot(*identity)
                    inbox.put(("snapshot", (rows, states)), timeout=1)
                    last_snapshot = time.monotonic()
                    control_dirty = False
                if cursors:
                    for key, messages in runtime_redis().xread(cursors, count=500):
                        # Financial state publications may have drained the
                        # pending-outbox gate. Refresh it on the cold path.
                        control_dirty = True
                        for message_id, fields in messages:
                            parts = key.split(":")
                            inbox.put(("state", (parts[-2], parts[-1], int(fields["instrument_id"]),
                                                 json.loads(fields["state"]))), timeout=1)
                            cursors[key] = message_id
                if time.monotonic() - last_checkpoint >= 1:
                    for context in tuple(contexts.values()):
                        for instrument, ownership in tuple(getattr(context, "ownership", {}).items()):
                            state = context.get_runtime_state(instrument)
                            checkpoint(context.scope, context.session_id, instrument, state, *ownership)
                    last_checkpoint = time.monotonic()
                try:
                    request = publications.get(timeout=0.05)
                except queue.Empty:
                    continue
                try:
                    if isinstance(request, tuple) and request[0] == "checkpoint":
                        checkpoint(*request[1:])
                        continue
                    if isinstance(request, tuple) and request[0] == "gap":
                        _, scope, session_id, user_id, instrument_id = request
                        from live_trading.models import TradingSession
                        from paper_trading.models import PaperTradingSession
                        model = TradingSession if scope == "live" else PaperTradingSession
                        model.objects.filter(pk=session_id, status="RUNNING").update(status="PAUSED")
                        from notifications.services import NotificationService
                        NotificationService.notify(
                            user_id=user_id, title="Trading paused after a market data gap",
                            message="Observed tick history was incomplete. Protective checks continue; review the session before resuming.",
                            data={"module": scope, "session_id": session_id, "instrument_id": instrument_id},
                            dedupe_key=f"tick-gap:{scope}:{session_id}:{instrument_id}",
                        )
                        continue
                    from strategy_engine.order_queue import publish_order
                    publish_order(request)
                except Exception:
                    logger.exception("Order publication failed request=%s", getattr(request, "request_id", "control"))
                    if isinstance(request, tuple):
                        raise RuntimeError("Data-gap pause could not be persisted")
                    StrategyRuntimeState.reconcile_trade_state(
                        request.scope, request.session_id, request.instrument_id, failed_reason="Publication failed",
                        settled_request_id=request.request_id)
                finally:
                    publications.task_done()
            except Exception:
                logger.exception("Execution control path failed; worker relinquishing ownership")
                alive.clear()
            finally:
                close_old_connections()

    thread = threading.Thread(target=background, name="execution-control", daemon=True)
    thread.start()
    channel = notification_socket(index)
    pool = ProcessPoolExecutor(max_workers=settings.CALCULATION_WORKERS,
                               mp_context=multiprocessing.get_context("spawn"), initializer=initialize)
    futures, ready, admitted = {}, defaultdict(deque), set()
    tenants = deque()
    worker_started = time.monotonic()
    try:
        while not stop.is_set() and alive.is_set():
            try:
                channel.recv(1024)
            except socket.timeout:
                pass
            while True:
                try:
                    kind, value = inbox.get_nowait()
                except queue.Empty:
                    break
                if kind == "snapshot":
                    rows, states = value
                    present = set()
                    for row in rows:
                        key = row["scope"], row["session"], row["instrument"]
                        present.add(key)
                        actor = actors.get(key)
                        if actor and actor.configuration_key == row["configuration_key"]:
                            _apply_controls(actor, row)
                        else:
                            if actor is None and (not row["market_ready"] or not row["runtime_ready"]):
                                continue
                            if actor:
                                actor.market.close()
                            if not actor and len(actors) >= settings.EXECUTION_MAX_ACTORS:
                                raise RuntimeError("Registered execution demand exceeds worker capacity; increase capacity before restarting")
                            market = SharedMemoryManager(row["symbol"], "1m")
                            shard = partition(f"{row['scope']}:{row['session']}:{row['instrument']}", settings.EXECUTION_SHARDS)
                            contract = row.pop("contract")
                            actor = Actor(**row, market=market, lease=leases[shard])
                            actor.last_tick = max(0, market.tick_counter - 1)
                            actor.last_gap_revision = market.source_gap
                            actor.watch = {int(item["instrument_id"]): item for item in actor.config["watchlist_instruments"]}
                            actor.context.contracts = getattr(actor.context, "contracts", {})
                            actor.context.contracts[actor.instrument] = contract
                            actors[key] = actor
                        state = states.get((actor.scope, actor.session), {}).get(actor.instrument)
                        if state is not None:
                            if actor.context.apply_external_runtime_state(actor.instrument, state):
                                actor.generation += 1
                        # Seed flat actors as well: hot reads must never initialize from Redis.
                        actor.context._runtime_l1.setdefault(actor.instrument, {})
                    for key in set(actors) - present:
                        removed = actors.pop(key)
                        removed.context.ownership.pop(removed.instrument, None)
                        removed.market.close()
                    for identity in set(contexts) - {(key[0], key[1]) for key in present}:
                        contexts.pop(identity, None)
                elif kind == "state":
                    scope, session, instrument, state = value
                    actor = actors.get((scope, session, instrument))
                    if actor:
                        if actor.context.apply_external_runtime_state(instrument, state):
                            actor.generation += 1
            now = time.time()
            for actor in tuple(actors.values()):
                ticks, gap = actor.market.read_ticks(actor.last_tick, limit=settings.EXECUTION_TICK_BATCH)
                if gap or actor.market.source_gap != actor.last_gap_revision:
                    if not actor.gap:
                        publications.put_nowait(("gap", actor.scope, actor.session, actor.context.user_id, actor.instrument))
                    actor.gap = True
                    actor.last_gap_revision = actor.market.source_gap
                    logger.error("Observed tick history gap actor=%s; entries blocked until recovery", actor.key)
                for sequence, event_time, received, price, volume in ticks:
                    from strategy_engine.engine import evaluate_protection
                    started = time.perf_counter()
                    evaluate_protection(actor, price)
                    metrics.observe("protection", (time.perf_counter() - started) * 1000)
                    metrics.observe("tick_to_decision", (time.time() - received) * 1000)
                    actor.last_tick = int(sequence)
                candle = (actor.market.revision, int(now // 60))
                if candle != actor.last_candle and not actor.in_flight:
                    actor.last_candle = candle
                    if actor.key not in admitted:
                        tenant = actor.context.user_id
                        if not ready[tenant]:
                            tenants.append(tenant)
                        ready[tenant].append(actor.key)
                        admitted.add(actor.key)
            for future, (actor, generation, started) in list(futures.items()):
                if time.monotonic() - started > (settings.EXECUTION_STARTUP_TASK_TIMEOUT if time.monotonic() - worker_started < 60 else settings.EXECUTION_TASK_TIMEOUT):
                    # A stuck native calculation cannot hold the owner's protective loop indefinitely.
                    raise TimeoutError("Calculation deadline exceeded; supervisor will restart this worker")
                if not future.done():
                    continue
                del futures[future]
                actor.in_flight = False
                if actors.get(actor.key) is not actor:
                    continue
                if actor.generation != generation:
                    # A committed fill/state update invalidated the calculation.
                    # Evaluate the current candle with that new state instead of
                    # waiting for the next candle and losing its entry/exit signal.
                    actor.last_candle = ()
                    continue
                try:
                    result = future.result()
                    metrics.observe("calculation_total", (time.monotonic() - started) * 1000)
                    from strategy_engine.engine import apply_calculation
                    apply_calculation(actor, result)
                except Exception:
                    if not actor.gap:
                        publications.put_nowait(("gap", actor.scope, actor.session, actor.context.user_id, actor.instrument))
                    actor.gap = True
                    logger.exception("Calculation failed actor=%s; entries disabled", actor.key)
            while tenants and len(futures) < settings.CALCULATION_WORKERS * 2:
                tenant = tenants.popleft()
                key = ready[tenant].popleft()
                admitted.discard(key)
                if ready[tenant]:
                    tenants.append(tenant)
                actor = actors.get(key)
                if actor is None or actor.in_flight:
                    continue
                state = actor.context.get_runtime_state(actor.instrument)
                position = actor.context.get_position(actor.instrument, config=actor.config)
                task = {"config": actor.config, "configuration_key": actor.configuration_key,
                        "symbol": actor.symbol, "calendar": actor.calendar, "events": actor.events,
                        "state": state, "position": position, "risk": actor.context.get_risk_stats(),
                        "as_of": now}
                future = pool.submit(evaluate, task)
                futures[future] = actor, actor.generation, time.monotonic()
                actor.in_flight = True
        if not alive.is_set() and not stop.is_set():
            raise RuntimeError("Execution control path stopped")
    finally:
        alive.clear()
        channel.close()
        thread.join(timeout=6)
        pool.shutdown(wait=False, cancel_futures=True)
        # Terminate stuck calculation children so an orderly supervisor restart stays bounded.
        for child in multiprocessing.active_children():
            child.terminate()
            child.join(timeout=2)
        for actor in actors.values():
            actor.market.close()
        for lease in leases.values():
            lease.release()
