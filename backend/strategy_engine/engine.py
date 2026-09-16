import time
import logging
import json
import threading
import django
from typing import List, Dict

from strategy_engine.context import LiveSessionContext, PaperSessionContext
from strategy_engine.executor import StrategyExecutor
from marketdata.shared_memory import SharedMemoryManager
from strategy_engine.data_feed import DataPreprocessor
from strategy_engine.dispatcher import OrderDispatcher

from common.enums import Side, TradePhase

logger = logging.getLogger(__name__)


def _start_runtime_lifecycle_listener(context, scope, session_id):
    from django.core.cache import cache
    from django.conf import settings

    stop_event = threading.Event()

    def listen():
        # Redis state is authoritative after recovery; only consume lifecycle events published after this worker starts.
        stream_id = "$"
        while not stop_event.is_set():
            try:
                if hasattr(cache, "client"):
                    redis_client = cache.client.get_client()
                else:
                    import redis
                    redis_client = redis.from_url(settings.REDIS_URL)
                entries = redis_client.xread({"runtime_state_lifecycle": stream_id}, count=100, block=1000)

                if not entries:
                    continue
                for _, messages in entries:
                    for message_id, fields in messages:
                        stream_id = message_id
                        raw_payload = fields.get(b"payload", fields.get("payload"))
                        payload = json.loads(raw_payload)
                        if payload.get("scope") != scope or str(payload.get("session_id")) != str(session_id):
                            continue
                        context.apply_external_runtime_state(payload["instrument_id"], payload["updates"])
            except Exception:
                if stop_event.is_set():
                    break
                logger.exception("Runtime lifecycle stream read failed; retrying")
                stop_event.wait(1.0)

    thread = threading.Thread(target=listen, name="runtime-lifecycle-sync", daemon=True)
    thread.start()
    return stop_event


class StrategyExecutionEngine:
    """
    Multiprocessing Actor worker that runs a strategy for a specific session.
    Reads O(1) tick data directly from Shared Memory and executes Two-Tier evaluations.
    """
    def __init__(self, session_id: str, strategy_id: str, scope: str, instrument_ids: List[int], paused=False):
        self.session_id = session_id
        self.strategy_id = strategy_id
        self.scope = scope
        self.instrument_ids = instrument_ids
        self.paused = paused
        self.is_running = False
        self.slow_path_executor = None

      
    def _init_context(self):
        if self.scope == "live":
            return LiveSessionContext(self.session_id, self.strategy_id)
        else:
            return PaperSessionContext(self.session_id, self.strategy_id)

    @staticmethod
    def _required_1m_candles(config):
        from marketdata.access import StrategyMarketDataService
        from rules_engine.metadata import IndicatorRequirementAnalyzer

        _, required_timeframes = StrategyMarketDataService.required_timeframes(config)
        requirements = IndicatorRequirementAnalyzer.get_warmup_requirements(config)
        timeframe_minutes = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1H": 60, "4H": 240, "1D": 375, "1W": 1875}

        return max(2, max(requirements.get(timeframe, 0) * timeframe_minutes.get(timeframe, 1) for timeframe in required_timeframes ))

    @staticmethod
    def _valid_candle_count(shm):
        data = shm.get_latest_data()
        return int(((data[:, 0] > 0) & (data[:, 1] > 0) & (data[:, 2] > 0) & (data[:, 3] > 0)).sum())

    def _mark_startup_error(self, message):
        try:
            if self.scope == "live":
                from live_trading.models import TradingSession
                TradingSession.objects.filter(id=self.session_id).update(status="ERROR", error_message=message)
            else:
                from paper_trading.models import PaperTradingSession
                PaperTradingSession.objects.filter(id=self.session_id).update(status="ERROR", error_message=message)
        except Exception:
            logger.exception("Failed to mark %s session %s as ERROR", self.scope, self.session_id)

    def _validate_worker_readiness(self, config, instruments, shm_managers):
        if len(shm_managers) != len(self.instrument_ids):
            missing_symbols = sorted(
                set(instruments.values()) - {shm.symbol for shm in shm_managers.values()}
            )
            for shm in shm_managers.values():
                shm.close()
            message = f"Required shared memory is unavailable: {missing_symbols}"
            self._mark_startup_error(message)
            raise RuntimeError(message)

        expected_ids = {
            int(item.get("instrument_id"))
            for item in config.get("watchlist_instruments", [])
            if item.get("instrument_id") is not None
        }
        supplied_ids = set(self.instrument_ids)
        if expected_ids != supplied_ids:
            message = f"Direct-routing instrument mismatch: expected={sorted(expected_ids)}, supplied={sorted(supplied_ids)}"
            self._mark_startup_error(message)
            raise RuntimeError(message)

        missing_ids = sorted(expected_ids - set(instruments))
        if missing_ids:
            message = f"Required instruments are missing or inactive: {missing_ids}"
            self._mark_startup_error(message)
            raise RuntimeError(message)

        required_candles = self._required_1m_candles(config)
        not_ready = []
        for instrument_id, shm in shm_managers.items():
            candle_count = self._valid_candle_count(shm)
            if candle_count < required_candles or shm.get_latest_price() is None:
                not_ready.append((instrument_id, candle_count, required_candles))
        if not_ready:
            message = f"Shared memory warmup is incomplete: {not_ready}"
            self._mark_startup_error(message)
            raise RuntimeError(message)

          
    def run(self):
        """
        Main actor loop. Runs inside a dedicated multiprocessing.Process.
        """
        self.is_running = True
        django.setup() # Ensure Django ORM is available in the new process

        from strategy_engine.runtime import StrategyRuntimeState
        from concurrent.futures import ThreadPoolExecutor

        try:
            context = self._init_context()
            config = context.get_strategy_config()
            executor = StrategyExecutor(config)
        except Exception as exc:
            message = f"Worker configuration is not ready: {exc}"
            self._mark_startup_error(message)
            raise RuntimeError(message) from exc
        
        shm_managers: Dict[int, SharedMemoryManager] = {}
        last_ticks: Dict[int, int] = {}
        last_indices: Dict[int, int] = {}
        
        from instruments.models import Instrument
        instruments = {inst.id: inst.sym_ticker for inst in Instrument.objects.filter(id__in=self.instrument_ids, is_active=True).values_list("id", "sym_ticker")}
        
        for inst_id, symbol in instruments.items():
            try:
                shm = SharedMemoryManager(symbol, "1m", create=False)
                shm_managers[inst_id] = shm
                last_ticks[inst_id] = shm.tick_counter
                last_indices[inst_id] = shm.current_index
            except Exception as e:
                logger.error(f"Failed to attach to SHM for {symbol}: {e}")

        self._validate_worker_readiness(config, instruments, shm_managers)

        recovered_positions = StrategyRuntimeState.rebuild_runtime_state_from_db(self.scope, str(self.session_id))
        recovered_orders = StrategyRuntimeState.rebuild_pending_order_state(self.scope, str(self.session_id))
        risk_rebuilt = StrategyRuntimeState.ensure_risk_metrics(self.scope, str(self.session_id))

        logger.info("Worker %s-%s recovered %s positions and %s pending orders; risk_rebuilt=%s.", self.scope, self.session_id, recovered_positions, recovered_orders, risk_rebuilt)

        pool_size = max(5, min(32, len(self.instrument_ids)))
        self.slow_path_executor = ThreadPoolExecutor(max_workers=pool_size)
        
        runtime_listener_stop = _start_runtime_lifecycle_listener(context, self.scope, str(self.session_id))

        # Build watch_map from config_snapshot
        watch_map = {}
        for wi_data in config.get('watchlist_instruments', []):
            inst_id = wi_data.get('instrument_id')
            if inst_id:
                watch_map[int(inst_id)] = wi_data  # Include routes data from config
                
        pending_slow_tasks = {inst_id: False for inst_id in instruments.keys()}
        pending_slow_task_times = {inst_id: 0.0 for inst_id in instruments.keys()}
        SLOW_TASK_TIMEOUT = 30.0  # Auto-reset stuck tasks after 30 seconds
        
        def _on_slow_task_done(fut, i_id):
            pending_slow_tasks[i_id] = False
            pending_slow_task_times[i_id] = 0.0
            exc = fut.exception()
            if exc:
                logger.error(f"Slow path task for instrument {i_id} failed: {exc}")

        logger.info(f"Worker {self.scope}-{self.session_id} initialized.")
        
        try:
            while self.is_running:

                now = time.time()
                for inst_id, shm in shm_managers.items():
                    current_tick = shm.tick_counter
                    current_idx = shm.current_index

                    # Auto-reset stuck slow tasks
                    if pending_slow_tasks[inst_id] and pending_slow_task_times[inst_id] > 0:
                        if now - pending_slow_task_times[inst_id] > SLOW_TASK_TIMEOUT:
                            logger.warning(f"Auto-resetting stuck slow task for instrument {inst_id} after {SLOW_TASK_TIMEOUT}s")
                            pending_slow_tasks[inst_id] = False
                            pending_slow_task_times[inst_id] = 0.0
                    
                    if current_tick != last_ticks[inst_id]:
                        try:
                            self._evaluate_fast_path(context, inst_id, shm)
                            
                            trigger_slow = False
                            if current_idx != last_indices[inst_id]:
                                trigger_slow = True
                                last_indices[inst_id] = current_idx
                                
                            if trigger_slow and not pending_slow_tasks[inst_id]:
                                pending_slow_tasks[inst_id] = True
                                pending_slow_task_times[inst_id] = now
                                fut = self.slow_path_executor.submit(
                                    self._evaluate_slow_path,
                                    executor,
                                    context,
                                    inst_id,
                                    shm,
                                    watch_map,
                                    config.get('user_id'),  # Use config instead of strategy.user_id
                                    shm_managers,
                                )
                                fut.add_done_callback(lambda f, i=inst_id: _on_slow_task_done(f, i))
                                
                            last_ticks[inst_id] = current_tick
                        except (ValueError, TypeError, IndexError) as e:
                            # Data corruption or type errors - critical
                            logger.error(f"Data corruption error evaluating tick for {shm.symbol}: {e}")
                            from notifications.services import NotificationService
                            from common.enums import NotificationType
                            NotificationService.notify(
                                user_id=config.get('user_id'),
                                notification_type=NotificationType.STRATEGY_ERROR,
                                message=f"Data corruption detected on {shm.symbol}: {str(e)}",
                                metadata={"strategy_id": self.strategy_id, "session_id": self.session_id}
                            )
                        except Exception as e:
                            logger.warning(f"Transient error evaluating tick for {shm.symbol}: {e}")
                        
                # Yield CPU slightly to avoid 100% core lockup
                time.sleep(0.001) 
        except KeyboardInterrupt:
            self.is_running = False
        except Exception as e:
            logger.exception(f"Fatal error in worker {self.session_id}: {e}")
        finally:
            runtime_listener_stop.set()
            self.slow_path_executor.shutdown(wait=False)
            for shm in shm_managers.values():
                shm.close()


    def _evaluate_fast_path(self, context, instrument_id, shm):
        """
        Microsecond-level check for stop-losses and trailing peaks.
        """
        try:
            position = context.get_position(instrument_id)
            if not position:
                return
            # Skip if an order is already in-flight
            if position.get("phase") in (TradePhase.EXIT_PENDING, TradePhase.PARTIAL_EXIT_PENDING):
                return
                
            last_price = shm.get_latest_price()
            if last_price is None:
                return

            updates = {"current_price": last_price}
            
            # 1. Update Trailing Peak
            peak_price = position.get("peak_price", last_price)
            side = position.get("side")
            if side == Side.BUY and last_price > peak_price:
                updates["peak_price"] = last_price
            elif side == Side.SELL and last_price < peak_price:
                updates["peak_price"] = last_price
            context.update_runtime_state(instrument_id, updates)
                
            # 2. Check Static Stop Loss / Target
            stop_price = position.get("protected_stop_price")
            target_price = position.get("protected_target_price")
            
            hit = False
            reason = None
            if stop_price is not None:
                if side == Side.BUY and last_price <= stop_price:
                    hit, reason = True, "Stop Loss Hit"
                elif side == Side.SELL and last_price >= stop_price:
                    hit, reason = True, "Stop Loss Hit"
                    
            if target_price is not None:
                if side == Side.BUY and last_price >= target_price:
                    hit, reason = True, "Target Hit"
                elif side == Side.SELL and last_price <= target_price:
                    hit, reason = True, "Target Hit"
                    
            if hit:
                logger.info(f"Fast-path exit triggered: {reason} at {last_price}")
                OrderDispatcher.dispatch_exit(
                    context, self.session_id, self.strategy_id, self.scope.upper(),
                    instrument_id, position, 'EXIT_ALL', {}, reason
                )
        except (ValueError, TypeError, KeyError) as e:
            # Data corruption or type errors - critical
            logger.error(f"Data corruption in fast path for instrument {instrument_id}: {e}")
            raise
        except Exception as e:
            # Transient errors - log but continue
            logger.warning(f"Transient error in fast path for instrument {instrument_id}: {e}")
            # Don't raise for transient errors

            
    def _process_exits(self, context, executor, instrument_id, base_df):
        if base_df is not None and not base_df.empty:
            context.update_runtime_state(instrument_id, {"current_price": float(base_df.iloc[-1]["close"])})
        position = context.get_position(instrument_id, config=executor.config)
        if not position:
            return None
            
        if position.get("phase") in (TradePhase.EXIT_PENDING, TradePhase.PARTIAL_EXIT_PENDING):
            return position

        should_exit, reason, action, params = executor.evaluate_exit_logic(position, base_df)
        
        if should_exit:
            logger.info(f"Slow-path exit triggered: {reason} with action {action}")
            OrderDispatcher.dispatch_exit(
                context, self.session_id, self.strategy_id, self.scope.upper(),
                instrument_id, position, action, params, reason
            )
                
        return position


    def _process_entries(self, context, executor, instrument_id, base_df, timestamp, watch_map, execution_price_reader):
        state = context.get_runtime_state(instrument_id)
        if state.get("phase") in (TradePhase.ENTRY_PENDING, TradePhase.EXIT_PENDING, TradePhase.PARTIAL_EXIT_PENDING):
            return
            
        capital = context.get_available_capital()
        if capital <= 0:
            return
            
        risk_evaluator = context.get_risk_evaluator()
        risk_stats = context.get_risk_stats()
      
        should_enter, side, reason = executor.evaluate_entry_logic(base_df, timestamp, state, risk_stats=risk_stats)
        if should_enter:
            logger.info(f"Slow-path entry triggered: {side} - {reason}")
            spot_price = float(base_df.iloc[-1]["close"])
            OrderDispatcher.dispatch_entry(
                context, risk_evaluator, executor, self.session_id, self.strategy_id, self.scope.upper(),
                instrument_id, side, reason, watch_map, spot_price, execution_price_reader
            )


    def _evaluate_slow_path(self, executor, context, instrument_id, shm, watch_map, user_id, shm_managers):
        """
        Evaluates heavy Pandas-TA / Numba indicators on candle close.
        """
        try:
            base_df, timestamp = DataPreprocessor.build_mtf_data(shm, executor)
            if base_df is None or base_df.empty: 
                return

            position = self._process_exits(context, executor, instrument_id, base_df)

            if not position:
                def execution_price_reader(execution_id):
                    execution_shm = shm_managers.get(execution_id)
                    return execution_shm.get_latest_price() if execution_shm else None

                if not self.paused:
                    self._process_entries(context, executor, instrument_id, base_df, timestamp, watch_map, execution_price_reader)
                
        except Exception as e:
            logger.exception(f"Error evaluating slow path for {shm.symbol}: {e}")
            from notifications.services import NotificationService
            from common.enums import NotificationType
            NotificationService.notify(
                user_id=user_id,
                notification_type=NotificationType.STRATEGY_ERROR,
                message=f"Strategy slow path execution error on {shm.symbol}: {str(e)}",
                metadata={"strategy_id": self.strategy_id, "session_id": self.session_id}
            )
