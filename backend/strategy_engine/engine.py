import time
import logging
import django
from typing import List, Dict

from strategy_engine.context import LiveSessionContext, PaperSessionContext
from strategy_engine.executor import StrategyExecutor
from marketdata.shared_memory import SharedMemoryManager
from strategy_engine.data_feed import DataPreprocessor
from strategy_engine.dispatcher import OrderDispatcher

from common.enums import Side, TradePhase

logger = logging.getLogger(__name__)

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
        
        from concurrent.futures import ThreadPoolExecutor
        # Scale thread pool dynamically based on instrument count (cap at 32 to avoid GIL thrashing)
        pool_size = max(5, min(32, len(instrument_ids)))
        self.slow_path_executor = ThreadPoolExecutor(max_workers=pool_size)

      
    def _init_context(self):
        if self.scope == "live":
            return LiveSessionContext(self.session_id, self.strategy_id)
        else:
            return PaperSessionContext(self.session_id, self.strategy_id)

          
    def run(self):
        """
        Main actor loop. Runs inside a dedicated multiprocessing.Process.
        """
        self.is_running = True
        django.setup() # Ensure Django ORM is available in the new process
        
        context = self._init_context()
        
        shm_managers: Dict[int, SharedMemoryManager] = {}
        last_ticks: Dict[int, int] = {}
        last_indices: Dict[int, int] = {}
        
        from instruments.models import Instrument
        instruments = {inst.id: inst.sym_ticker for inst in Instrument.objects.filter(id__in=self.instrument_ids)}
        
        for inst_id, symbol in instruments.items():
            try:
                shm = SharedMemoryManager(symbol, "1m", create=False)
                shm_managers[inst_id] = shm
                last_ticks[inst_id] = shm.tick_counter
                last_indices[inst_id] = shm.current_index
            except Exception as e:
                logger.error(f"Failed to attach to SHM for {symbol}: {e}")
                
        from strategies.models import Strategy
        strategy = Strategy.objects.prefetch_related(
            'rule_groups__rules', 
            'watchlist_instruments__instrument', 
            'watchlist_instruments__execution_routes__target_underlying_instrument'
        ).get(id=self.strategy_id)
        
        watch_map = {w.instrument.id: w for w in strategy.watchlist_instruments.all() if w.instrument}
        
        config = context.get_strategy_config()
                
        executor = StrategyExecutor(config)

        pending_slow_tasks = {inst_id: False for inst_id in instruments.keys()}
        pending_slow_task_times = {inst_id: 0.0 for inst_id in instruments.keys()}
        SLOW_TASK_TIMEOUT = 30.0  # Auto-reset stuck tasks after 30 seconds
        
        def _on_slow_task_done(fut, i_id):
            pending_slow_tasks[i_id] = False
            pending_slow_task_times[i_id] = 0.0
            exc = fut.exception()
            if exc:
                logger.error(f"Slow path task for instrument {i_id} failed: {exc}")

        logger.info(f"Worker {self.scope}-{self.session_id} entering close-only execution loop.")
        
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
                                    strategy.user_id,
                                    shm_managers,
                                )
                                fut.add_done_callback(lambda f, i=inst_id: _on_slow_task_done(f, i))
                                
                            last_ticks[inst_id] = current_tick
                        except Exception as e:
                            logger.exception(f"Error evaluating tick for {shm.symbol}: {e}")
                            from notifications.services import NotificationService
                            from common.enums import NotificationType
                            NotificationService.notify(
                                user_id=strategy.user_id,
                                notification_type=NotificationType.STRATEGY_ERROR,
                                message=f"Strategy execution error on {shm.symbol}: {str(e)}",
                                metadata={"strategy_id": self.strategy_id, "session_id": self.session_id}
                            )
                        
                # Yield CPU slightly to avoid 100% core lockup
                time.sleep(0.001) 
        except KeyboardInterrupt:
            self.is_running = False
        except Exception as e:
            logger.exception(f"Fatal error in worker {self.session_id}: {e}")
        finally:
            self.slow_path_executor.shutdown(wait=False)
            for shm in shm_managers.values():
                shm.close()


    def _evaluate_fast_path(self, context, instrument_id, shm):
        """
        Microsecond-level check for stop-losses and trailing peaks.
        """
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
