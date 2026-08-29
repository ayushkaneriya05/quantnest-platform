import multiprocessing
import logging
from typing import Dict

logger = logging.getLogger(__name__)

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

    @staticmethod
    def _worker_key(session_id: str, scope: str):
        return scope, str(session_id)

    def start_worker(self, session_id: str, strategy_id: str, scope: str, instrument_ids: list):
        """
        Spawns a new multiprocessing.Process for the StrategyExecutionEngine.
        """
        worker_key = self._worker_key(session_id, scope)
        if worker_key in self.workers and self.workers[worker_key].is_alive():
            if worker_key not in self.paused_sessions:
                return
            self.stop_worker(session_id, scope)

        self.paused_sessions.discard(worker_key)
        self.worker_specs[worker_key] = (strategy_id, scope, instrument_ids)
        self._spawn_worker(session_id, strategy_id, scope, instrument_ids, paused=False)

    def _spawn_worker(self, session_id, strategy_id, scope, instrument_ids, paused):
        logger.info(f"Starting execution worker for {scope} session {session_id}")
            
        # Lazy import to avoid circular dependencies
        from strategy_engine.engine import StrategyExecutionEngine
        
        engine = StrategyExecutionEngine(session_id, strategy_id, scope, instrument_ids, paused=paused)
        p = multiprocessing.Process(
            target=engine.run, 
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
        for worker_key, p in self.workers.items():
            if not p.is_alive():
                scope, session_id = worker_key
                logger.warning(f"Worker for {scope} session {session_id} died unexpectedly.")
                dead_workers.append(worker_key)
                
        for worker_key in dead_workers:
            del self.workers[worker_key]
            self.worker_specs.pop(worker_key, None)
            self.paused_sessions.discard(worker_key)
            
    def cleanup(self):
        """
        Terminates all running workers.
        """
        for scope, session_id in list(self.workers.keys()):
            self.stop_worker(session_id, scope)
