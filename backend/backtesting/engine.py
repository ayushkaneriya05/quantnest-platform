import copy
import logging
from datetime import datetime, time

import numpy as np
import pandas as pd
from django.utils import timezone

from common.enums import BacktestStatus, OrderType, Side
from common.trading_utils import (
    minutes_since_session_open,
    get_exchange_times,
)
from rules_engine.utils import compute_sl_distance_from_config
from marketdata.calendar_service import EventCalendarService
from marketdata.access import StrategyMarketDataService
from marketdata.services import MarketDataService
from risk_management.evaluator import RiskEvaluator
from rules_engine.evaluator import RuleEvaluator
from rules_engine.metadata import IndicatorRequirementAnalyzer
from strategy_engine.executor import StrategyExecutor
from common.costs import TradingCostCalculator
from .models import BacktestMetrics, BacktestRun, BacktestTrade, EquityCurvePoint

logger = logging.getLogger(__name__)


class BacktestCancelled(Exception):
    pass


class BacktestEngine:
    """
    Core engine for simulating strategy performance against historical data.
    """

    def __init__(self, run_id=None, run_instance=None):
        if run_instance:
            self.run = run_instance
        else:
            self.run = BacktestRun.objects.select_related("strategy").get(id=run_id)

        self.strategy = self.run.strategy
        self.user = self.run.user

        if getattr(self.run, "strategy_version", None):
            self.config = copy.deepcopy(self.run.strategy_version.config_snapshot or {})
        else:
            self.config = copy.deepcopy(self.run.config_snapshot or {})

        if self.run.parameters:
            self._deep_merge(self.config, self.run.parameters)

        self.initial_capital = float(self.run.initial_capital)

        self.data_resolution = MarketDataService.normalize_timeframe(self.config.get("time_rule", {}).get("candle_timeframe", "5m"))

        self.risk_evaluator = RiskEvaluator(self.initial_capital)

        # Get charge profile from BacktestRun
        self.charge_profile = None
        if self.run.include_charges and self.run.charge_profile:
            self.charge_profile = self.run.charge_profile

        # Add charge profile to config for execution service
        if self.charge_profile:
            self.config['charge_profile'] = self.charge_profile

        # Create backtest context (using BacktestRun as session)
        from .context import BacktestContext
        self.context = BacktestContext(
            run_id=str(self.run.id),
            strategy_id=str(self.strategy.id),
            config=self.config,
            initial_capital=self.initial_capital,
            charge_profile=self.charge_profile,
            include_charges=self.run.include_charges,
        )

        self.equity_curve = []
        self.trades_to_create = []
        self.instrument_states = {}
        self.max_equity = self.initial_capital
        self.max_drawdown = 0
        self.halt_state = {"active_until": None, "reason": None}
        self.market_data_cache = {}
        self.rule_evaluators = {}
        self.rule_evaluator = None

    def _broadcast_progress_update(self, progress_pct, message="Processing candles..."):
        """
        Broadcast backtest progress via WebSocket and save to database.
        Uses time-based throttling to avoid database hammering.
        """
        import time
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from django.utils import timezone as dj_timezone

        # Throttle database updates to avoid excessive writes
        if not hasattr(self, '_last_progress_update_time'):
            self._last_progress_update_time = 0

        current_time = time.time()
        # Only update database every 0.5 seconds or on significant progress changes
        should_update_db = (
            (current_time - self._last_progress_update_time >= 0.5) or
            (progress_pct % 10 == 0) or
            (progress_pct == 100)
        )

        if should_update_db:
            self.run.progress_pct = min(progress_pct, 99 if progress_pct < 100 else 100)
            self.run.save(update_fields=["progress_pct"])
            self._last_progress_update_time = current_time

        # Broadcast via WebSocket
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                group_name = f"user_{self.user.id}_backtest"
                message_data = {
                    "type": "backtest.progress",
                    "message": {
                        "run_id": self.run.id,
                        "status": self.run.status,
                        "progress_pct": self.run.progress_pct,
                        "message": message,
                        "timestamp": dj_timezone.now().isoformat(),
                    }
                }
                async_to_sync(channel_layer.group_send)(group_name, message_data)
        except Exception as e:
            logger.warning(f"Failed to broadcast progress update: {e}")

    def load_data(self):
        watchlist = self.strategy.watchlist_instruments.all()
        if not watchlist:
            raise ValueError("Strategy has no instruments in watchlist")
        start_dt = datetime.combine(self.run.start_date, datetime.min.time())
        end_dt = datetime.combine(self.run.end_date, datetime.max.time())

        from datetime import timedelta
        warmup_days = IndicatorRequirementAnalyzer.get_max_warmup_days(self.config)
        fetch_start_dt = start_dt - timedelta(days=warmup_days)

        time_rule = self.config.get("time_rule") or {}
        timezone_str = time_rule.get("timezone", "Asia/Kolkata")
        datasets = {}

        instruments_to_fetch = set()
        instruments_list = list(watchlist.select_related("instrument").prefetch_related("execution_routes", "execution_routes__target_underlying_instrument"))

        for watch in instruments_list:
            instruments_to_fetch.add(watch.instrument)
            # for route in watch.execution_routes.all():
            #     if route.route_type in ['FUTURES', 'OPTIONS'] and route.target_underlying_instrument:
            #         instruments_to_fetch.add(route.target_underlying_instrument)

        total_instruments = len(instruments_to_fetch)

        for idx, instrument in enumerate(instruments_to_fetch):
            if getattr(self, "run", None) and total_instruments > 0:
                # Progress ranges from 1% to 15% during data load
                load_progress = max(1, int((idx / total_instruments) * 15))
                self.run.progress_pct = load_progress
                self.run.save(update_fields=["progress_pct"])

            base_timeframe, mtf_data = StrategyMarketDataService.get_backtest_multi_timeframe_data(
                self.config,
                instrument,
                start_dt=fetch_start_dt,
                end_dt=end_dt,
                fetch_missing=True,
            )
            df = mtf_data.get(base_timeframe)

            if df is None or df.empty:
                logger.warning("No historical data found for %s", instrument.sym_ticker)
                continue

            try:
                import pytz
                local_tz = pytz.timezone(timezone_str)
                if df.index.tz is None:
                    df.index = df.index.tz_localize("UTC").tz_convert(local_tz)
                else:
                    df.index = df.index.tz_convert(local_tz)
            except Exception as e:
                logger.warning(f"Timezone conversion error for {instrument}: {e}")

            for timeframe, timeframe_df in list(mtf_data.items()):
                try:
                    if timeframe_df.index.tz is None:
                        timeframe_df.index = timeframe_df.index.tz_localize("UTC").tz_convert(local_tz)
                    else:
                        timeframe_df.index = timeframe_df.index.tz_convert(local_tz)
                except Exception as e:
                    logger.warning(f"Timezone conversion error for MTF {timeframe} for {instrument}: {e}")

            datasets[instrument.id] = {
                "instrument": instrument,
                "df": df,
                "df_dict": df.to_dict("index"),
                "base_timeframe": base_timeframe,
                "mtf_data": mtf_data,
            }

        if not datasets:
            raise ValueError("No historical data found for any watchlist instrument")

        return datasets

    def run_simulation(self, datasets=None):
        try:
            if datasets is None:
                datasets = self.load_data()

            self.datasets = datasets

            self.run.status = BacktestStatus.RUNNING
            self.run.started_at = timezone.now()
            self.run.error_message = ""
            self.run.save(update_fields=["status", "started_at", "error_message"])

            contexts = {}
            all_timestamps = set()
            for instrument_id, payload in datasets.items():
                instrument = payload["instrument"]
                df = payload["df"]
                mtf_data = payload.get("mtf_data", {})
                base_timeframe = payload.get("base_timeframe") or self.data_resolution
                self.market_data_cache[(instrument.id, base_timeframe)] = df

                from rules_engine.evaluator import IndicatorEngine
                mtf_indicator_engines = {}
                for tf, tdf in mtf_data.items():
                    mtf_indicator_engines[tf] = IndicatorEngine(tdf)

                base_evaluator = RuleEvaluator(
                    df,
                    mtf_data=mtf_data,
                    mtf_indicator_engines=mtf_indicator_engines
                )
                self.rule_evaluators[(instrument.id, base_timeframe)] = base_evaluator
                executor = StrategyExecutor(
                    self.config,
                    mtf_data=mtf_data,
                    indicator_engine=base_evaluator.indicator_engine,
                    mtf_indicator_engines=mtf_indicator_engines
                )
                contexts[instrument_id] = {
                    "instrument": instrument,
                    "df": df,
                    "df_dict": payload.get("df_dict") or df.to_dict("index"),
                    "mtf_data": mtf_data,
                    "base_timeframe": base_timeframe,
                    "executor": executor,
                    "entry_signals": executor.evaluate_entry_signals(df),
                }
                self.instrument_states[instrument_id] = {
                    "instrument_daily_trades": 0,
                    "last_exit_time": None,
                    "last_candle": None,
                }
                all_timestamps.update(df.index.tolist())

            daily_stats = {"trades": 0, "pnl": 0.0}
            current_day = None

            sorted_timestamps = sorted(all_timestamps)

            # Filter warmup candles using the same timezone as the loaded data.
            # A UTC midnight boundary would discard the first local-session candles.
            import pytz
            configured_timezone = self.config.get("time_rule", {}).get("timezone", "Asia/Kolkata")
            start_dt_tz_aware = pytz.timezone(configured_timezone).localize(
                datetime.combine(self.run.start_date, datetime.min.time())
            )

            total_timestamps = len(sorted_timestamps)
            last_progress_pct = 0

            for ts_idx, timestamp in enumerate(sorted_timestamps):
                if timestamp < start_dt_tz_aware:
                    continue

                self._check_cancelled()

                if total_timestamps > 0:
                    current_pct = int((ts_idx / total_timestamps) * 100)
                    if current_pct >= last_progress_pct + 1:
                        last_progress_pct = current_pct
                        self._broadcast_progress_update(current_pct, f"Processing candles... {current_pct}%")

                if current_day != timestamp.date():
                    current_day = timestamp.date()
                    daily_stats = {"trades": 0, "pnl": 0.0}
                    self.halt_state = {"active_until": None, "reason": None}
                    for state in self.instrument_states.values():
                        state["instrument_daily_trades"] = 0
                        state["last_exit_time"] = None
                    self.context.reset_daily_metrics()

                    self._populate_active_events(current_day)

                # STEP 1: NEW CANDLE OPEN - Retrieve execution instrument candles
                instrument_candles = {}
                for instrument_id, context in contexts.items():
                    df_dict = context["df_dict"]
                    candle = df_dict.get(timestamp)
                    if candle is None:
                        continue
                    instrument_candles[instrument_id] = candle
                    state = self.instrument_states[instrument_id]
                    state["last_candle"] = candle

                if not instrument_candles:
                    continue

                # STEP 2: EXECUTE PENDING MARKET ORDERS at current candle OPEN
                from .execution_service import BacktestExecutionService
                BacktestExecutionService.execute_pending_orders(self.context, datasets, timestamp)

                # STEP 3: POSITION INTRABAR CHECKS (SL/Target)
                # STEP 4: UPDATE POSITION STATE
                for instrument_id, candle in instrument_candles.items():
                    open_pos = self._get_position_for_signal(instrument_id)
                    if open_pos:
                        # Update MAE/MFE
                        self._update_mae_mfe(
                            open_pos,
                            self._get_execution_candle(open_pos, timestamp) or candle,
                        )
                        # Check SL/Target (intrabar)
                        pos_state = {
                            "avg_price": open_pos['avg_price'],
                            "side": open_pos['side'],
                            "current_price": float(candle["close"]),
                            "peak_price": open_pos['peak_price'],
                            "protected_stop_price": open_pos['protected_stop_price'],
                            "protected_target_price": open_pos['protected_target_price'],
                        }

                        # Update peak price
                        from common.enums import Side
                        if open_pos['side'] == Side.BUY:
                            pos_state["peak_price"] = max(pos_state["peak_price"], float(candle["high"]))
                        else:
                            pos_state["peak_price"] = min(pos_state["peak_price"], float(candle["low"]))

                        # Check SL/Target with SAME CANDLE POLICY: STOP LOSS FIRST
                        execution_candle = self._get_execution_candle(open_pos, timestamp) or candle
                        stop_price = open_pos.get('protected_stop_price')
                        target_price = open_pos.get('protected_target_price')
                        fast_hit = False
                        exit_price = float(execution_candle["close"])
                        reason = None

                        # Check Stop Loss FIRST
                        if stop_price is not None:
                            if open_pos['side'] == Side.BUY and float(execution_candle["low"]) <= stop_price:
                                fast_hit, reason, exit_price = True, "Stop Loss Hit", stop_price
                            elif open_pos['side'] == Side.SELL and float(execution_candle["high"]) >= stop_price:
                                fast_hit, reason, exit_price = True, "Stop Loss Hit", stop_price

                        # Check Target only if Stop Loss not hit
                        if not fast_hit and target_price is not None:
                            if open_pos['side'] == Side.BUY and float(execution_candle["high"]) >= target_price:
                                fast_hit, reason, exit_price = True, "Target Hit", target_price
                            elif open_pos['side'] == Side.SELL and float(execution_candle["low"]) <= target_price:
                                fast_hit, reason, exit_price = True, "Target Hit", target_price

                        if fast_hit:
                            BacktestExecutionService.execute_market_order(
                                self.context,
                                open_pos['instrument'],
                                Side.SELL if open_pos['side'] == Side.BUY else Side.BUY,
                                open_pos['quantity'],
                                exit_price,
                                timestamp,
                                self.config,
                                exit_reason=reason,
                                slippage_pct=self.run.slippage_pct,
                                execute_immediately=True,  # SL/Target execute immediately
                            )

                # STEP 5: CANDLE CLOSE - Now candle data is considered completed
                # STEP 6: EVALUATE EXIT RULES
                for instrument_id, context in contexts.items():
                    candle = instrument_candles.get(instrument_id)
                    if candle is None:
                        continue

                    state = self.instrument_states[instrument_id]
                    is_in_no_trade_zone = context["executor"].is_in_no_trade_zone(timestamp)

                    open_pos = self._get_position_for_signal(instrument_id)
                    stats = self._build_runtime_stats(candle, daily_stats, context["instrument"], timestamp)

                    # Auto-disable check
                    auto_disable_eval = self.risk_evaluator.evaluate_auto_disable_rules(
                        self.config.get("auto_disable_rules", []),
                        stats,
                    )
                    if auto_disable_eval.get("should_disable"):
                        if open_pos:
                            BacktestExecutionService.execute_market_order(
                                self.context,
                                open_pos['instrument'],
                                Side.SELL if open_pos['side'] == Side.BUY else Side.BUY,
                                open_pos['quantity'],
                                float(candle["close"]),
                                timestamp,
                                self.config,
                                exit_reason="Auto-Disable Triggered",
                                execute_immediately=True,  # Auto-disable executes immediately
                            )
                            state["last_exit_time"] = timestamp
                            state["instrument_daily_trades"] += 1
                            daily_stats["trades"] = self.context.get_risk_metrics().get("daily_trades", 0)
                            daily_stats["pnl"] = self.context.get_risk_metrics().get("daily_pnl", 0.0)
                            open_pos = None
                        self.halt_state = {
                            "active_until": datetime.combine(timestamp.date(), time(23, 59, 59)),
                            "reason": auto_disable_eval.get("matches", [{}])[0].get("message", "Auto-disable triggered"),
                        }

                    # Evaluate exit rules (normal exits)
                    if open_pos:
                        executor = context["executor"]
                        execution_candle = self._get_execution_candle(open_pos, timestamp) or candle

                        pos_state = {
                            "avg_price": open_pos['avg_price'],
                            "side": open_pos['side'],
                            "current_price": float(execution_candle["close"]),
                            "peak_price": open_pos['peak_price'],
                            "protected_stop_price": open_pos['protected_stop_price'],
                            "protected_target_price": open_pos['protected_target_price'],
                        }

                        # Build df slice for exit rule evaluation
                        instrument_id_for_df = open_pos['instrument_id']
                        df_dict = None
                        for payload in self.datasets.values():
                            if payload['instrument'].id == instrument_id_for_df:
                                df_dict = payload['df_dict']
                                break

                        if df_dict:
                            df_list = []
                            for ts in sorted(df_dict.keys()):
                                if ts <= timestamp:
                                    df_list.append(df_dict[ts])

                            if df_list:
                                df = pd.DataFrame(df_list)
                                df.index = pd.to_datetime([ts for ts in sorted(df_dict.keys()) if ts <= timestamp])

                                should_exit, reason, action, action_params = executor.evaluate_exit_logic(
                                    pos_state, df
                                )

                                if should_exit:
                                    from strategy_engine.exit_actions import process_exit_action
                                    decision = process_exit_action(
                                        action=action,
                                        params=action_params,
                                        position=open_pos,
                                        reason=reason,
                                    )

                                    if decision.should_send_order:
                                        # Queue exit for NEXT candle open
                                        BacktestExecutionService.execute_market_order(
                                            self.context,
                                            open_pos['instrument'],
                                            Side.SELL if open_pos['side'] == Side.BUY else Side.BUY,
                                            decision.quantity,
                                            float(candle["close"]),  # Will be replaced with next candle open
                                            timestamp,
                                            self.config,
                                            exit_reason=decision.reason,
                                            slippage_pct=self.run.slippage_pct,
                                            execute_immediately=False,  # Queue for next candle
                                        )

                # STEP 7: EVALUATE ENTRY RULES
                for instrument_id, context in contexts.items():
                    candle = instrument_candles.get(instrument_id)
                    if candle is None:
                        continue

                    state = self.instrument_states[instrument_id]
                    is_in_no_trade_zone = context["executor"].is_in_no_trade_zone(timestamp)

                    open_pos = self._get_position_for_signal(instrument_id)
                    stats = self._build_runtime_stats(candle, daily_stats, context["instrument"], timestamp)

                    if not open_pos:
                        executor = context["executor"]

                        if self._is_halted(timestamp) or is_in_no_trade_zone:
                            continue

                        # Check for New Entries via StrategyExecutor
                        can_enter, reason = executor.can_enter(stats, timestamp)
                        if can_enter and bool(context["entry_signals"].get(timestamp, False)):
                            # Queue entry for NEXT candle open
                            self._process_entry(
                                self.context,
                                context["instrument"],
                                candle,
                                timestamp,
                                executor,
                                stats,
                                queue_for_next_candle=True,
                            )

                    daily_stats["trades"] = self.context.get_risk_metrics().get("daily_trades", 0)
                    daily_stats["pnl"] = self.context.get_risk_metrics().get("daily_pnl", 0.0)

                total_value = self.context.current_capital + self._calculate_total_unrealized_pnl()

                self.equity_curve.append(
                    EquityCurvePoint(
                        run=self.run,
                        timestamp=timestamp,
                        equity_value=total_value,
                        drawdown_pct=self._calculate_drawdown(total_value),
                    )
                )

            if sorted_timestamps:
                self._force_close_open_positions(sorted_timestamps[-1])
            return self._finalize_run()
        except BacktestCancelled:
            from django.core.exceptions import ObjectDoesNotExist
            from django.db.utils import DatabaseError
            try:
                self.run.refresh_from_db(fields=["status"])
                self.run.completed_at = timezone.now()
                self.run.save(update_fields=["completed_at"])
            except (ObjectDoesNotExist, self.run.DoesNotExist, DatabaseError):
                pass
            return None
        except Exception as exc:
            logger.exception("Backtest failed: %s", exc)
            from django.core.exceptions import ObjectDoesNotExist
            from django.db.utils import DatabaseError
            try:
                self.run.status = BacktestStatus.FAILED
                self.run.error_message = str(exc)
                self.run.completed_at = timezone.now()
                self.run.save(update_fields=["status", "error_message", "completed_at"])

                # Broadcast error via WebSocket
                try:
                    from asgiref.sync import async_to_sync
                    from channels.layers import get_channel_layer

                    channel_layer = get_channel_layer()
                    if channel_layer:
                        group_name = f"user_{self.user.id}_backtest"
                        message_data = {
                            "type": "backtest.error",
                            "message": {
                                "run_id": self.run.id,
                                "status": "FAILED",
                                "error": str(exc),
                                "message": f"Backtest failed: {str(exc)}",
                                "timestamp": timezone.now().isoformat(),
                            }
                        }
                        async_to_sync(channel_layer.group_send)(group_name, message_data)
                except Exception as e:
                    logger.warning(f"Failed to broadcast error message: {e}")
            except (ObjectDoesNotExist, self.run.DoesNotExist, DatabaseError):
                pass
            return None




    def _update_mae_mfe(self, position, candle):
        """
        Update MAE/MFE using execution instrument candle only.
        For MANUAL routing, this uses the execution instrument data.
        """
        high = float(candle["high"])
        low = float(candle["low"])
        entry = position.get("avg_price")  # Use canonical avg_price field

        if position["side"] == Side.BUY:
            # MFE is highest point reached - entry
            position["max_profit"] = max(position.get("max_profit", 0), high - entry)
            # MAE is entry - lowest point reached
            position["max_loss"] = max(position.get("max_loss", 0), entry - low)
        else:
            # MFE is entry - lowest point reached
            position["max_profit"] = max(position.get("max_profit", 0), entry - low)
            # MAE is highest point reached - entry
            position["max_loss"] = max(position.get("max_loss", 0), high - entry)


    def _calculate_drawdown(self, current_value):
        if current_value > self.max_equity:
            self.max_equity = current_value
            return 0
        return ((self.max_equity - current_value) / self.max_equity) * 100 if self.max_equity > 0 else 0

    def _calculate_unrealized_pnl(self, candle, instrument_id):
        """
        Calculate unrealized PnL for a single position.
        This is used for equity curve calculation.
        """
        pos = self._get_position_for_signal(instrument_id)
        if not pos:
            return 0
        price = float(candle["close"])
        return (price - pos["avg_price"]) * pos["quantity"] if pos["side"] == Side.BUY else (pos["avg_price"] - price) * pos["quantity"]

    def _calculate_total_unrealized_pnl(self):
        total = 0.0
        for instrument_id, position in self.context.positions.items():
            if position is None:
                continue
            candle = self.instrument_states.get(instrument_id, {}).get("last_candle")
            if candle is None:
                continue
            total += self._calculate_unrealized_pnl(candle, instrument_id)
        return total

    def _force_close_open_positions(self, timestamp):
        """Force close any open positions at the end of the simulation."""
        from .execution_service import BacktestExecutionService
        from common.enums import Side

        for instrument_id, position in list(self.context.positions.items()):
            if position is None:
                continue

            # CRITICAL: Use execution instrument candle, not signal instrument candle
            # For MANUAL routing, signal and execution instruments are different
            execution_candle = self._get_execution_candle(position, timestamp)

            if execution_candle is not None:
                BacktestExecutionService.execute_market_order(
                    self.context,
                    position['instrument'],
                    Side.SELL if position['side'] == Side.BUY else Side.BUY,
                    position['quantity'],
                    float(execution_candle["close"]),
                    timestamp,
                    self.config,
                    exit_reason="End of Backtest Square-off",
                    execute_immediately=True,  # Force close executes immediately
                )
            else:
                # Missing execution instrument data - log and skip
                logger.warning(f"Missing execution candle for force close: instrument {instrument_id} at {timestamp}")

    def _finalize_run(self):
        self._save_trades_from_context()
        self._calculate_metrics()

        self.run.refresh_from_db(fields=["status"])
        if self.run.status == BacktestStatus.CANCELLED:
            return

        self.run.status = BacktestStatus.COMPLETED
        self.run.completed_at = timezone.now()
        self.run.progress_pct = 100
        self.run.save(update_fields=["status", "completed_at", "progress_pct"])

        # Broadcast completion via WebSocket
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            if channel_layer:
                group_name = f"user_{self.user.id}_backtest"
                trades_count = BacktestTrade.objects.filter(run=self.run).count()
                message_data = {
                    "type": "backtest.completed",
                    "message": {
                        "run_id": self.run.id,
                        "status": "COMPLETED",
                        "progress_pct": 100,
                        "trades_count": trades_count,
                        "message": "Backtest completed successfully",
                        "timestamp": timezone.now().isoformat(),
                    }
                }
                async_to_sync(channel_layer.group_send)(group_name, message_data)
        except Exception as e:
            logger.warning(f"Failed to broadcast completion message: {e}")

    def _calculate_metrics(self, trades_list=None):
        metrics, _ = BacktestMetrics.objects.get_or_create(run=self.run)

        if trades_list is not None:
            trades = sorted(trades_list, key=lambda t: t.entry_time or timezone.now())
        else:
            trades = list(BacktestTrade.objects.filter(run=self.run).order_by("entry_time"))

        if not trades:
            metrics.final_capital = self.context.current_capital
            metrics.total_return_pct = ((self.context.current_capital - self.initial_capital) / self.initial_capital) * 100 if self.initial_capital else 0
            metrics.total_trades = 0
            metrics.save()
            return None

        pnl_series = [float(trade.net_pnl) for trade in trades]
        holding_times = [int(trade.holding_duration_minutes or 0) for trade in trades]
        win_pnls = [p for p in pnl_series if p > 0]
        loss_pnls = [p for p in pnl_series if p < 0]
        breakeven = [p for p in pnl_series if p == 0]

        metrics.total_trades = len(trades)
        metrics.winning_trades = len(win_pnls)
        metrics.losing_trades = len(loss_pnls)
        metrics.breakeven_trades = len(breakeven)
        metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100 if metrics.total_trades else 0

        metrics.avg_win = np.mean(win_pnls) if win_pnls else 0
        metrics.avg_loss = np.mean(loss_pnls) if loss_pnls else 0
        metrics.largest_win = max(win_pnls) if win_pnls else 0
        metrics.largest_loss = min(loss_pnls) if loss_pnls else 0
        metrics.avg_trade_pnl = np.mean(pnl_series) if pnl_series else 0

        metrics.avg_holding_time_minutes = int(np.mean(holding_times)) if holding_times else 0
        winning_holds = [int(t.holding_duration_minutes or 0) for t in trades if float(t.net_pnl) > 0]
        losing_holds = [int(t.holding_duration_minutes or 0) for t in trades if float(t.net_pnl) < 0]
        metrics.avg_winning_hold_time = int(np.mean(winning_holds)) if winning_holds else 0
        metrics.avg_losing_hold_time = int(np.mean(losing_holds)) if losing_holds else 0

        gross_profit = sum(win_pnls)
        gross_loss = abs(sum(loss_pnls))
        metrics.profit_factor = (gross_profit / gross_loss) if gross_loss else (gross_profit if gross_profit else 0)
        loss_rate = 1 - (metrics.win_rate / 100)
        metrics.expectancy = ((metrics.win_rate / 100) * float(metrics.avg_win)) + (loss_rate * float(metrics.avg_loss))
        metrics.payoff_ratio = (float(metrics.avg_win) / abs(float(metrics.avg_loss))) if metrics.avg_loss else 0

        metrics.final_capital = self.context.current_capital
        metrics.total_return_pct = ((self.context.current_capital - self.initial_capital) / self.initial_capital) * 100 if self.initial_capital else 0
        metrics.total_brokerage = sum(float(t.brokerage) for t in trades)
        metrics.total_slippage = sum(float(t.slippage) for t in trades)
        metrics.total_charges = sum(float((t.charges_json or {}).get("total_charges", 0) or 0) for t in trades)
        metrics.avg_mae = np.mean([float(t.mae or 0) for t in trades]) if trades else 0
        metrics.avg_mfe = np.mean([float(t.mfe or 0) for t in trades]) if trades else 0
        efficiencies = [
            (float(trade.net_pnl) / float(trade.mfe))
            for trade in trades
            if float(trade.mfe or 0) != 0
        ]
        metrics.trade_efficiency = np.mean(efficiencies) if efficiencies else 0
        metrics.monthly_returns_json = self._calculate_monthly_returns()

        drawdown_series = [float(point.drawdown_pct) for point in self.equity_curve]
        metrics.max_drawdown_pct = max(drawdown_series) if drawdown_series else 0
        metrics.max_drawdown_amount = (float(metrics.max_drawdown_pct) / 100) * self.max_equity if self.max_equity else 0
        metrics.recovery_factor = (float(metrics.total_return_pct) / float(metrics.max_drawdown_pct)) if metrics.max_drawdown_pct else 0

        # Calculate Sharpe, Sortino, and Volatility from periodic equity returns (not trade PnL)
        if len(self.equity_curve) > 1:
            # Build equity DataFrame
            equity_df = pd.DataFrame(
                [{"timestamp": point.timestamp, "equity": float(point.equity_value)} for point in self.equity_curve]
            )
            equity_df["timestamp"] = pd.to_datetime(equity_df["timestamp"])
            equity_df = equity_df.set_index("timestamp").sort_index()

            # Calculate daily returns
            daily_equity = equity_df["equity"].resample("D").last().dropna()
            daily_returns = daily_equity.pct_change().dropna()

            if len(daily_returns) > 1:
                # Sharpe Ratio using daily returns
                mean_return = np.mean(daily_returns)
                std_return = np.std(daily_returns)
                if std_return > 0:
                    # Annualize: multiply by sqrt(252) for daily returns
                    metrics.sharpe_ratio = (mean_return / std_return) * np.sqrt(252)
                    metrics.volatility_pct = (std_return * np.sqrt(252)) * 100

                # Sortino Ratio using downside deviation
                downside_returns = daily_returns[daily_returns < 0]
                if len(downside_returns) > 0:
                    downside_deviation = np.std(downside_returns)
                    if downside_deviation > 0:
                        metrics.sortino_ratio = (mean_return / downside_deviation) * np.sqrt(252)

            if metrics.max_drawdown_pct:
                metrics.calmar_ratio = float(metrics.total_return_pct) / float(metrics.max_drawdown_pct)

        metrics.max_consecutive_wins, metrics.max_consecutive_losses = self._consecutive_streaks(pnl_series)
        metrics.cagr = self._calculate_cagr()
        metrics.max_drawdown_duration_days = self._calculate_drawdown_duration_days()

        metrics.save()
        return None

    def _build_runtime_stats(self, candle, daily_stats, instrument, timestamp):
        state = self.instrument_states.get(instrument.id, {})
        open_pos = self.context.get_position(instrument.id)

        atr_value = 0.0
        base_timeframe = MarketDataService.normalize_timeframe(self.data_resolution)
        evaluator = self.rule_evaluators.get((instrument.id, base_timeframe))

        if evaluator and getattr(evaluator, "indicator_engine", None):
            from common.enums import OperandType
            atr_series = evaluator.indicator_engine.get_series(OperandType.ATR, {"period": 14})
            if atr_series is not None and not atr_series.empty:
                if timestamp in atr_series.index:
                    atr_value = float(atr_series.loc[timestamp])
                else:
                    atr_value = float(atr_series.iloc[-1])

        return {
            "daily_pnl": daily_stats.get("pnl", 0.0),
            "daily_trades": daily_stats.get("trades", 0),
            "instrument_daily_trades": state.get("instrument_daily_trades", 0),
            "last_exit_time": state.get("last_exit_time"),
            "open_positions": len(self.context.positions),
            "drawdown": self._calculate_drawdown(self.context.current_capital),
            "atr": atr_value,
            "consecutive_losses": self._current_consecutive_losses(),
            "consecutive_wins": self._current_consecutive_wins(),
            "win_rate": self._current_win_rate(),
            "weekly_pnl": self._pnl_over_window(timestamp, 7),
            "monthly_pnl": self._pnl_over_window(timestamp, 30),
            "time_minutes": minutes_since_session_open(timestamp.time()),
            "minutes_since_open": minutes_since_session_open(timestamp.time()),
            "custom_value": daily_stats.get("custom_value", 0),
        }

    def _is_halted(self, timestamp):
        """Check if trading is currently halted."""
        if self.halt_state.get("active_until") is None:
            return False
        active_until = self.halt_state["active_until"]
        # Handle both tz-aware and tz-naive comparisons
        try:
            return timestamp <= active_until
        except TypeError:
            # Timezone mismatch — compare dates as fallback
            return timestamp.date() <= getattr(active_until, "date", lambda: active_until)()

    def _populate_active_events(self, current_date):
        """Populate active_events_today in config for special event filter checks."""
        special = self.config.get("special_event_filter") or {}
        if not special:
            return

        active_events = []
        try:
            if special.get("avoid_earnings") and EventCalendarService.is_event_day(current_date, "EARNINGS"):
                active_events.append("EARNINGS")
            if special.get("avoid_news") and EventCalendarService.is_event_day(current_date, "NEWS"):
                active_events.append("NEWS")
            if special.get("avoid_rbi_policy") and EventCalendarService.is_event_day(current_date, "RBI_POLICY"):
                active_events.append("RBI_POLICY")
        except Exception as exc:
            logger.debug("EventCalendarService query failed for %s: %s", current_date, exc)

        self.config.setdefault("special_event_filter", {})["active_events_today"] = active_events

    def _check_cancelled(self):

        from django.core.exceptions import ObjectDoesNotExist
        try:
            self.run.refresh_from_db(fields=["status"])
            if self.run.status == BacktestStatus.CANCELLED:
                raise BacktestCancelled()
        except (ObjectDoesNotExist, self.run.DoesNotExist):
            raise BacktestCancelled()


    def _current_consecutive_losses(self):
        return self.context.get_risk_metrics().get("consecutive_losses", 0)

    def _current_consecutive_wins(self):
        return self.context.get_risk_metrics().get("consecutive_wins", 0)

    def _current_win_rate(self):
        return self.context.get_risk_metrics().get("win_rate", 0)

    def _pnl_over_window(self, timestamp, days):
        # Use context risk metrics for simplified implementation
        if days == 7:
            return self.context.get_risk_metrics().get("weekly_pnl", 0)
        elif days == 30:
            return self.context.get_risk_metrics().get("monthly_pnl", 0)
        return 0


    def _calculate_position_unrealized_pnl(self, position, candle):
        price = float(candle["close"])
        entry_price = position.get("entry_price") or position["avg_price"]
        return (price - entry_price) * position["quantity"] if position["side"] == Side.BUY else (entry_price - price) * position["quantity"]

    def _get_position_for_signal(self, instrument_id):
        """V1 DIRECT ONLY: Direct position lookup."""
        return self.context.get_position(instrument_id)

    def _calculate_monthly_returns(self):
        if not self.equity_curve:
            return {}
        df = pd.DataFrame(
            [{"timestamp": point.timestamp, "equity": float(point.equity_value)} for point in self.equity_curve]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        monthly = df["equity"].resample("ME").last().pct_change().fillna(0) * 100
        return {index.strftime("%Y-%m"): float(value) for index, value in monthly.items()}



    def _consecutive_streaks(self, pnl_series):
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        for pnl in pnl_series:
            if pnl > 0:
                current_wins += 1
                current_losses = 0
            elif pnl < 0:
                current_losses += 1
                current_wins = 0
            else:
                current_wins = 0
                current_losses = 0
            max_wins = max(max_wins, current_wins)
            max_losses = max(max_losses, current_losses)
        return max_wins, max_losses

    def _calculate_cagr(self):
        duration_days = max((self.run.end_date - self.run.start_date).days, 1)
        years = duration_days / 365.25
        if years <= 0 or self.initial_capital <= 0 or self.context.current_capital <= 0:
            return 0
        return ((self.context.current_capital / self.initial_capital) ** (1 / years) - 1) * 100

    def _calculate_drawdown_duration_days(self):
        """
        Calculate maximum drawdown duration in days using timestamps.
        Duration is measured from peak timestamp to recovery timestamp.
        """
        if not self.equity_curve:
            return 0

        longest_duration_days = 0
        peak_timestamp = None
        peak_equity = 0

        for point in self.equity_curve:
            current_equity = float(point.equity_value)
            current_drawdown = float(point.drawdown_pct)

            # New peak detected
            if current_equity > peak_equity:
                # If we were in drawdown, calculate duration
                if peak_timestamp is not None and current_drawdown == 0:
                    duration_days = (point.timestamp - peak_timestamp).days
                    longest_duration_days = max(longest_duration_days, duration_days)

                peak_equity = current_equity
                peak_timestamp = point.timestamp

            # Currently in drawdown
            elif current_drawdown > 0 and peak_timestamp is not None:
                # Calculate ongoing duration (not yet recovered)
                duration_days = (point.timestamp - peak_timestamp).days
                longest_duration_days = max(longest_duration_days, duration_days)

        # If still in drawdown at end, count to final point
        if peak_timestamp is not None and float(self.equity_curve[-1].drawdown_pct) > 0:
            duration_days = (self.equity_curve[-1].timestamp - peak_timestamp).days
            longest_duration_days = max(longest_duration_days, duration_days)

        return longest_duration_days


    def _deep_merge(self, base, updates):
        for key, value in (updates or {}).items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value


    def _process_entry(self, context, instrument, candle, timestamp, executor, stats, queue_for_next_candle=False):
        """
        Process entry logic using BacktestExecutionService.
        If queue_for_next_candle=True, queues order for next candle open.
        """
        from .execution_service import BacktestExecutionService
        from common.enums import Side
        from instruments.services import InstrumentResolver
        from instruments.models import WatchlistInstrument
        from strategy_engine.sizing import compute_position_size
        from risk_management.evaluator import RiskEvaluator

        # Resolve execution instrument
        watch = WatchlistInstrument.objects.filter(
            strategy_id=self.strategy.id, instrument=instrument
        ).first()

        if not watch:
            return

        spot_price = float(candle["close"])
        entry_side = self.config.get("entry_order_config", {}).get("entry_side", Side.BUY)
        resolutions = InstrumentResolver.resolve(watch, entry_side, spot_price=spot_price)

        # Calculate position size
        risk_evaluator = RiskEvaluator(context.current_capital)

        for exec_instrument, exec_side, sizing_config in resolutions:
            execution_candle = self._get_candle_for_instrument(exec_instrument.id, timestamp)
            execution_price = float(execution_candle["close"]) if execution_candle is not None else spot_price
            lot_size = getattr(exec_instrument, 'lot_size', 1) or 1
            quantity = compute_position_size(
                risk_evaluator=risk_evaluator,
                sizing_config=sizing_config,
                price=execution_price,
                sl_distance=None,
                lot_size=lot_size,
                strategy_config=self.config
            )

            if quantity <= 0:
                continue

            # Execute order (queue or immediate)
            BacktestExecutionService.execute_market_order(
                context,
                exec_instrument,
                exec_side,
                quantity,
                execution_price,
                timestamp,
                self.config,
                exit_reason="strategy_entry",
                slippage_pct=self.run.slippage_pct,
                execute_immediately=not queue_for_next_candle,
            )

    def _get_candle_for_instrument(self, instrument_id, timestamp):
        for payload in getattr(self, "datasets", {}).values():
            if payload["instrument"].id == instrument_id:
                return payload["df_dict"].get(timestamp)
        return None

    def _get_execution_candle(self, position, timestamp):
        return self._get_candle_for_instrument(position["instrument_id"], timestamp)

    def _save_trades_from_context(self):
        """
        Save trades from context to BacktestTrade model.
        """
        for trade_data in self.context.closed_trades:
            charges_json = trade_data.get('charges_json') or {}
            entry_charges = charges_json.get('entry_charges', {}) or {}
            exit_charges = charges_json.get('exit_charges', {}) or {}
            entry_price = float(trade_data['entry_price'])
            quantity = int(trade_data['quantity'])
            trade = BacktestTrade(
                run=self.run,
                instrument=trade_data['instrument'],
                side=trade_data['side'],
                entry_time=trade_data['entry_time'],
                exit_time=trade_data['exit_time'],
                entry_price=entry_price,
                exit_price=trade_data['exit_price'],
                quantity=quantity,
                gross_pnl=trade_data['gross_pnl'],
                net_pnl=trade_data['net_pnl'],
                charges_json=charges_json,
                exit_reason=trade_data['exit_reason'],
                brokerage=float(entry_charges.get('brokerage', 0) or 0) + float(exit_charges.get('brokerage', 0) or 0),
                slippage=float(trade_data.get('slippage', 0)),  # Use actual slippage from trade data
                pnl_pct=(float(trade_data['net_pnl']) / (entry_price * quantity)) * 100 if entry_price > 0 and quantity > 0 else 0,
                mae=trade_data.get('mae', 0),
                mfe=trade_data.get('mfe', 0),
                holding_duration_minutes=int((trade_data['exit_time'] - trade_data['entry_time']).total_seconds() / 60) if trade_data['exit_time'] and trade_data['entry_time'] else 0,
            )
            self.trades_to_create.append(trade)

        if self.trades_to_create:
            BacktestTrade.objects.bulk_create(self.trades_to_create)

        if self.equity_curve:
            EquityCurvePoint.objects.bulk_create(self.equity_curve, ignore_conflicts=True)
