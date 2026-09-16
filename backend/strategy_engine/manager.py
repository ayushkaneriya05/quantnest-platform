import multiprocessing
import logging
import time
from typing import Dict

logger = logging.getLogger(__name__)


def _run_worker(session_id, strategy_id, scope, instrument_ids, paused):
    """Initialize Django before importing the model-dependent worker module."""
    import django

    django.setup()

    from strategy_engine.engine import StrategyExecutionEngine

    engine = StrategyExecutionEngine(session_id, strategy_id, scope, instrument_ids, paused=paused)
    engine.run()


class SessionExecutionManager:
    """
    Manages the lifecycle of Multiprocessing actor workers for strategies.
    Should be run as a daemon process that polls or listens for active sessions 
    and spawns/kills execution engine workers.
    """
    def __init__(self):
        self.workers: Dict[tuple, multiprocessing.Process] = {}
        self.worker_specs = {}
        self.paused_sessions = set()
        self.restart_after = {}

    @staticmethod
    def _worker_key(session_id: str, scope: str):
        return scope, str(session_id)

    def start_worker(self, session_id: str, strategy_id: str, scope: str, instrument_ids: list, paused=False):
        """
        Spawns a new multiprocessing.Process for the StrategyExecutionEngine.
        """
        worker_key = self._worker_key(session_id, scope)
        if worker_key in self.workers and self.workers[worker_key].is_alive():
            if worker_key not in self.paused_sessions:
                return
            self.stop_worker(session_id, scope)

        if paused:
            self.paused_sessions.add(worker_key)
        else:
            self.paused_sessions.discard(worker_key)
        self.worker_specs[worker_key] = (strategy_id, scope, instrument_ids)
        self._spawn_worker(session_id, strategy_id, scope, instrument_ids, paused=paused)

    def _spawn_worker(self, session_id, strategy_id, scope, instrument_ids, paused):
        logger.info(f"Starting execution worker for {scope} session {session_id}")
        p = multiprocessing.Process(
            target=_run_worker,
            args=(session_id, strategy_id, scope, instrument_ids, paused),
            name=f"Worker-{scope}-{session_id}"
        )
        p.start()
        self.workers[self._worker_key(session_id, scope)] = p

    def stop_worker(self, session_id: str, scope: str):
        """
        Terminates the multiprocessing.Process for a given session.
        """
        worker_key = self._worker_key(session_id, scope)
        if worker_key in self.workers:
            p = self.workers[worker_key]
            if p.is_alive():
                logger.info(f"Terminating execution worker for {scope} session {session_id}")
                p.terminate()
                p.join(timeout=5)
                if p.is_alive():
                    p.kill() # Force kill if terminate fails
            del self.workers[worker_key]
        self.worker_specs.pop(worker_key, None)
        self.paused_sessions.discard(worker_key)
        self.restart_after.pop(worker_key, None)

    def pause_worker(self, session_id: str, scope: str):
        """Keep the worker alive for exits while disabling new entries."""
        worker_key = self._worker_key(session_id, scope)
        spec = self.worker_specs.get(worker_key)
        if not spec:
            return

        self.paused_sessions.add(worker_key)
        self.stop_worker(session_id, scope)
        self.paused_sessions.add(worker_key)
        self.worker_specs[worker_key] = spec
        strategy_id, scope, instrument_ids = spec
        self._spawn_worker(session_id, strategy_id, scope, instrument_ids, paused=True)
            
    def check_health(self):
        """
        Cleans up dead workers from the tracking dict.
        """
        dead_workers = []
        now = time.monotonic()
        for worker_key, p in self.workers.items():
            if not p.is_alive():
                scope, session_id = worker_key
                logger.warning(f"Worker for {scope} session {session_id} died unexpectedly.")
                dead_workers.append(worker_key)
                
        for worker_key in dead_workers:
            spec = self.worker_specs.get(worker_key)
            if not spec:
                self.workers.pop(worker_key, None)
                continue
            scope, session_id = worker_key

            if scope == "live":
                from live_trading.models import TradingSession
                allowed_statuses = {"RUNNING", "PAUSED", "STOPPING"}
                status = TradingSession.objects.filter(id=session_id).values_list("status", flat=True).first()
            else:
                from paper_trading.models import PaperTradingSession
                allowed_statuses = {"RUNNING", "PAUSED"}
                status = PaperTradingSession.objects.filter(id=session_id).values_list("status", flat=True).first()

            if status not in allowed_statuses:
                self.workers.pop(worker_key, None)
                self.worker_specs.pop(worker_key, None)
                self.paused_sessions.discard(worker_key)
                continue

            if now < self.restart_after.get(worker_key, 0):
                continue

            self.workers.pop(worker_key, None)

            strategy_id, _, instrument_ids = spec
            paused = worker_key in self.paused_sessions
            self.restart_after[worker_key] = now + 5
            self._spawn_worker(session_id, strategy_id, scope, instrument_ids, paused=paused)
            
    def cleanup(self):
        """
        Terminates all running workers.
        """
        for scope, session_id in list(self.workers.keys()):
            self.stop_worker(session_id, scope)
