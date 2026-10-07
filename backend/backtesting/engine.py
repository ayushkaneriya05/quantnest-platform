import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from django.utils import timezone

from common.enums import BacktestStatus, Side
from instruments.models import Instrument
from instruments.services import InstrumentResolver
from marketdata.access import StrategyMarketDataService
from marketdata.services import MarketDataService
from rules_engine.evaluator import IndicatorEngine
from risk_management.evaluator import RiskEvaluator
from marketdata.calendar import MarketSessionCalendar
from .context import BacktestContext
from .execution_service import BacktestExecutionService
from .executor import BacktestStrategyExecutor, process_exit_action
from .models import BacktestMetrics, BacktestRun, BacktestTrade, EquityCurvePoint
from .services import backtest_configuration

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

        self.config = backtest_configuration(self.run)

        self.watchlist_by_instrument_id = {
            int(item["instrument_id"]): item
            for item in (self.config.get("watchlist_instruments") or [])
            if isinstance(item, dict) and item.get("instrument_id") is not None
        }

        self.initial_capital = float(self.run.initial_capital)

        # Get charge profile from BacktestRun
        self.charge_profile = None
        if self.run.include_charges and self.run.charge_profile:
            self.charge_profile = self.run.charge_profile

        # Add charge profile to config for execution service
        if self.charge_profile:
            self.config['charge_profile'] = self.charge_profile

        # Create backtest context (using BacktestRun as session)
        self.context = BacktestContext(
            initial_capital=self.initial_capital,
            charge_profile=self.charge_profile,
            include_charges=self.run.include_charges,
            strategy_config=self.config,
        )

        self.equity_curve = []
        self.trades_to_create = []
        self.instrument_states = {}
        self.instruments_by_id = {}
        self.max_equity = self.initial_capital
        self._last_progress_update_time = 0
        self._last_progress_message = None

    def _broadcast_progress_update(self, progress_pct, message="Processing candles..."):
        """
        Broadcast backtest progress via WebSocket and save to database.
        Uses time-based throttling to avoid database hammering.
        """
        import time
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from django.utils import timezone as dj_timezone

        current_time = time.time()
        progress_pct = min(max(int(progress_pct), self.run.progress_pct), 100)
        self.run.progress_pct = progress_pct
        self.run.progress_message = message
        # Only update database every 0.5 seconds or on significant progress changes
        message_changed = message != self._last_progress_message
        should_update_db = (
            (current_time - self._last_progress_update_time >= 0.5) or
            (progress_pct % 10 == 0) or
            (progress_pct == 100)
            or message_changed
        )

        if should_update_db:
            self.run.save(update_fields=["progress_pct", "progress_message"])
            self._last_progress_update_time = current_time
            self._last_progress_message = message

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
                        "progress_pct": progress_pct,
                        "message": message,
                        "timestamp": dj_timezone.now().isoformat(),
                    }
                }
                async_to_sync(channel_layer.group_send)(group_name, message_data)
        except Exception as e:
            logger.warning(f"Failed to broadcast progress update: {e}")

    def load_data(self):
        watchlist = self.watchlist_by_instrument_id
        if not watchlist:
            raise ValueError("Backtest config snapshot has no watchlist instruments")
        datasets = {}
        data_quality = {"complete": True, "instruments": [], "warnings": []}

        instruments = Instrument.objects.in_bulk(watchlist)
        missing_ids = sorted(set(watchlist) - set(instruments))
        if missing_ids:
            raise ValueError(f"Backtest snapshot instruments no longer exist: {missing_ids}")

        unsupported_routes = [
            f"{instruments[instrument_id].sym_ticker}: {route.get('route_type')}"
            for instrument_id, watch in watchlist.items()
            for route in (watch.get("execution_routes") or [])
            if route.get("route_type") != "DIRECT"
        ]
        if unsupported_routes:
            raise ValueError("Backtests currently support Direct instrument routing only: " + ", ".join(unsupported_routes))

        _, required_timeframes = StrategyMarketDataService.required_timeframes(self.config)
        include_weekly_warmup = "1W" in required_timeframes

        instruments_to_fetch = [instruments[instrument_id] for instrument_id in watchlist]
        total_instruments = len(instruments_to_fetch)

        for idx, instrument in enumerate(instruments_to_fetch):
            load_progress = 1 + int(idx / max(total_instruments, 1) * 13)
            self._broadcast_progress_update(load_progress, f"Loading historical candles for {instrument.sym_ticker}...")
            
            calendar = MarketSessionCalendar.for_instrument(instrument)
            required_1m_candles = MarketDataService.required_1m_candles(self.config, session_minutes=calendar.session_minutes)
            start_dt = datetime.combine(self.run.start_date, datetime.min.time(), tzinfo=calendar.zone)
            end_dt = datetime.combine(self.run.end_date, datetime.max.time(), tzinfo=calendar.zone)
            fetch_start_dt = calendar.warmup_start(start_dt, required_1m_candles, include_weekly=include_weekly_warmup)
            local_tz = calendar.zone
            calendar.load_holidays(
                fetch_start_dt.astimezone(calendar.zone).date() - timedelta(days=7),
                end_dt.astimezone(calendar.zone).date() + timedelta(days=7),
            )
            base_timeframe, mtf_data, quality = StrategyMarketDataService.get_backtest_multi_timeframe_data(
                self.config,
                instrument,
                start_dt=fetch_start_dt,
                end_dt=end_dt,
                fetch_missing=True,
                calendar=calendar,
            )
            data_quality["instruments"].append(quality)
            data_quality["complete"] = data_quality["complete"] and quality["complete"]
            df = mtf_data.get(base_timeframe)

            if df is None or df.empty:
                logger.warning("No historical data found for %s", instrument.sym_ticker)
                quality["complete"] = False
                data_quality["complete"] = False
                data_quality["warnings"].append(f"No candles available for {instrument.sym_ticker}.")
                continue

            try:
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

                if timeframe != base_timeframe:
                    mtf_data[timeframe] = self._index_mtf_candles_by_availability(timeframe_df, timeframe, calendar, local_tz)

            if not quality["complete"]:
                data_quality["warnings"].append(f"Historical candles remain missing for {instrument.sym_ticker}; results may be incomplete.")

            datasets[instrument.id] = {
                "instrument": instrument,
                "df": df,
                "df_dict": df.to_dict("index"),
                "mtf_data": mtf_data,
            }
            if total_instruments:
                load_progress = 2 + int(((idx + 1) / total_instruments) * 13)
                self._broadcast_progress_update(load_progress, f"Historical candles loaded for {instrument.sym_ticker}.")

        self.run.data_quality = data_quality
        self.run.save(update_fields=["data_quality"])

        if not datasets:
            raise ValueError("No historical data found for any watchlist instrument")

        return datasets

    @staticmethod
    def _index_mtf_candles_by_availability(frame, timeframe, calendar, output_timezone):
        """Make each MTF candle visible only at its scheduled completion time."""
        result = frame.copy()
        result.index = [
            calendar.candle_close(value.to_pydatetime(), timeframe).astimezone(output_timezone) for value in result.index
        ]
        return result

    def run_simulation(self, datasets=None):
        try:
            self.run.refresh_from_db(fields=["status"])
            if self.run.status == BacktestStatus.CANCELLED:
                return None
            if datasets is None:
                self._broadcast_progress_update(1, "Starting backtest and loading historical candles...")
                datasets = self.load_data()
                self._broadcast_progress_update(15, "Historical data loaded; preparing strategy signals...")

            self.run.refresh_from_db(fields=["status"])
            if self.run.status == BacktestStatus.CANCELLED:
                return None

            self.run.status = BacktestStatus.RUNNING
            self.run.started_at = timezone.now()
            self.run.error_message = ""
            self.run.save(update_fields=["status", "started_at", "error_message"])

            contexts = {}
            self.instruments_by_id = {
                int(instrument_id): payload["instrument"]
                for instrument_id, payload in datasets.items()
            }
            active_event_cache = {}
            all_timestamps = set()
            for instrument_id, payload in datasets.items():
                instrument = payload["instrument"]
                df = payload["df"]
                mtf_data = payload.get("mtf_data", {})
                mtf_indicator_engines = {}
                for tf, tdf in mtf_data.items():
                    mtf_indicator_engines[tf] = IndicatorEngine(tdf)

                base_indicator_engine = IndicatorEngine(df)
                executor = BacktestStrategyExecutor(
                    self.config,
                    mtf_data=mtf_data,
                    indicator_engine=base_indicator_engine,
                    mtf_indicator_engines=mtf_indicator_engines,
                    active_event_cache=active_event_cache,
                )
                preparation_progress = 15 + int((len(contexts) + 1) / max(len(datasets), 1) * 10)
                self._broadcast_progress_update(preparation_progress, f"Preparing indicators and entry signals for {instrument.sym_ticker}...")
                
                contexts[instrument_id] = {
                    "instrument": instrument,
                    "df": df,
                    "df_dict": payload.get("df_dict") or df.to_dict("index"),
                    "executor": executor,
                    "entry_signals": executor.evaluate_entry_signals(df),
                }
                self.instrument_states[instrument_id] = {
                    "last_exit_time": None,
                    "last_candle": None,
                }
                all_timestamps.update(df.index.tolist())

            sorted_timestamps = sorted(all_timestamps)

            # Interpret run dates in the exchange timezone used by the loaded bars.
            from zoneinfo import ZoneInfo
            configured_timezone = self.config.get("time_rule", {}).get("timezone", "Asia/Kolkata")
            start_dt_tz_aware = datetime.combine(self.run.start_date, datetime.min.time(), tzinfo=ZoneInfo(configured_timezone))

            simulation_timestamps = [timestamp for timestamp in sorted_timestamps if timestamp >= start_dt_tz_aware]
            total_timestamps = len(simulation_timestamps)
            last_progress_pct = 25
            self._broadcast_progress_update(25, "Starting historical trade simulation...")

            for ts_idx, timestamp in enumerate(simulation_timestamps):

                self._check_cancelled()

                if total_timestamps > 0:
                    current_pct = 25 + int(((ts_idx + 1) / total_timestamps) * 69)
                    if current_pct >= last_progress_pct + 1:
                        last_progress_pct = current_pct
                        self._broadcast_progress_update(current_pct, "Simulating strategy across historical candles...")

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
                positions_before_fill = set(self.context.positions)
                BacktestExecutionService.execute_pending_orders(self.context, instrument_candles, timestamp)
                positions_at_open = positions_before_fill | set(self.context.positions)

                # STEP 3: POSITION INTRABAR CHECKS (SL/Target)
                # STEP 4: UPDATE POSITION STATE
                for instrument_id, candle in instrument_candles.items():
                    open_pos = self.context.get_position(instrument_id)
                    if open_pos:
                        # Update MAE/MFE
                        self._update_mae_mfe(open_pos, candle)
                        # Update peak price before checking protected exits.
                        if open_pos['side'] == Side.BUY:
                            open_pos["peak_price"] = max(open_pos["peak_price"], float(candle["high"]))
                        else:
                            open_pos["peak_price"] = min(open_pos["peak_price"], float(candle["low"]))

                        # Check SL/Target with SAME CANDLE POLICY: STOP LOSS FIRST
                        stop_price = open_pos.get('protected_stop_price')
                        target_price = open_pos.get('protected_target_price')
                        fast_hit = False
                        exit_price = float(candle["close"])
                        reason = None

                        # Check Stop Loss FIRST
                        if stop_price is not None:
                            if open_pos['side'] == Side.BUY and float(candle["low"]) <= stop_price:
                                fast_hit, reason, exit_price = True, "Stop Loss Hit", stop_price
                            elif open_pos['side'] == Side.SELL and float(candle["high"]) >= stop_price:
                                fast_hit, reason, exit_price = True, "Stop Loss Hit", stop_price

                        # Check Target only if Stop Loss not hit
                        if not fast_hit and target_price is not None:
                            if open_pos['side'] == Side.BUY and float(candle["high"]) >= target_price:
                                fast_hit, reason, exit_price = True, "Target Hit", target_price
                            elif open_pos['side'] == Side.SELL and float(candle["low"]) <= target_price:
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

                    open_pos = self.context.get_position(instrument_id)
                    # Evaluate exit rules (normal exits)
                    if open_pos:
                        executor = context["executor"]
                        pos_state = {
                            "avg_price": open_pos['avg_price'],
                            "side": open_pos['side'],
                            "current_price": float(candle["close"]),
                            "peak_price": open_pos['peak_price'],
                            "protected_stop_price": open_pos['protected_stop_price'],
                            "protected_target_price": open_pos['protected_target_price'],
                        }

                        bars = context["df"].loc[:timestamp]
                        should_exit, reason, action, action_params = executor.evaluate_exit_logic(pos_state, bars)

                        if should_exit:
                            decision = process_exit_action(action=action, params=action_params, position=open_pos, reason=reason)
                            open_pos.update(decision.state_updates)

                            if decision.should_send_order:
                                BacktestExecutionService.execute_market_order(
                                    self.context,
                                    open_pos['instrument'],
                                    Side.SELL if open_pos['side'] == Side.BUY else Side.BUY,
                                    decision.quantity,
                                    float(candle["close"]),
                                    timestamp,
                                    self.config,
                                    exit_reason=decision.reason,
                                    slippage_pct=self.run.slippage_pct,
                                    execute_immediately=False,
                                )

                # STEP 7: EVALUATE ENTRY RULES
                is_in_no_trade_zone = next(iter(contexts.values()))["executor"].is_in_no_trade_zone(timestamp)
                for instrument_id, context in contexts.items():
                    candle = instrument_candles.get(instrument_id)
                    if candle is None:
                        continue

                    open_pos = self.context.get_position(instrument_id)
                    instrument_state = self.instrument_states[instrument_id]

                    if not bool(context["entry_signals"].get(timestamp, False)):
                        continue
                    self.context.diagnostics["entry_signals"] += 1
                    if open_pos:
                        self.context.diagnostics["existing_positions"] += 1

                    if not open_pos:
                        executor = context["executor"]

                        if not self.context.can_enter(timestamp):
                            self.context.diagnostics["auto_disable_restrictions"] += 1
                            continue

                        if is_in_no_trade_zone:
                            self.context.diagnostics["time_event_restrictions"] += 1
                            continue

                        # Check for new entries using the backtest-local executor.
                        can_enter, _ = executor.can_enter(
                            {"last_exit_time": instrument_state["last_exit_time"]}, timestamp
                        )
                        if not can_enter:
                            self.context.diagnostics["cooldown_restrictions"] += 1
                        if can_enter:
                            # Queue entry for NEXT candle open
                            self._process_entry(
                                context["instrument"],
                                candle,
                                timestamp,
                                executor,
                                instrument_candles,
                            )

                total_value = self.context.current_capital + self._calculate_total_unrealized_pnl()

                self.equity_curve.append(
                    EquityCurvePoint(run=self.run, timestamp=timestamp, equity_value=total_value, drawdown_pct=self._calculate_drawdown(total_value))
                )

                for closed_id in positions_at_open - set(self.context.positions):
                    state = self.instrument_states.get(closed_id)
                    if state is not None:
                        state["last_exit_time"] = timestamp

            BacktestExecutionService.finalize_open_positions(self.context)
            if self.equity_curve:
                final_point = self.equity_curve[-1]
                final_point.equity_value = self.context.current_capital
                final_point.drawdown_pct = self._calculate_drawdown(self.context.current_capital)

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
                self.run.progress_message = f"Backtest failed: {exc}"[:255]
                self.run.completed_at = timezone.now()
                self.run.save(update_fields=["status", "error_message", "progress_message", "completed_at"])

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
                                "progress_pct": self.run.progress_pct,
                                "error": str(exc),
                                "message": self.run.progress_message,
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
        Backtests currently use direct instrument routing.
        """
        high = float(candle["high"])
        low = float(candle["low"])
        entry = position.get("avg_price")
        quantity = position.get("initial_quantity", position.get("quantity", 0))

        if position["side"] == Side.BUY:
            # MFE is highest point reached - entry
            position["max_profit"] = max(position.get("max_profit", 0), (high - entry) * quantity)
            # MAE is entry - lowest point reached
            position["max_loss"] = max(position.get("max_loss", 0), (entry - low) * quantity)
        else:
            # MFE is entry - lowest point reached
            position["max_profit"] = max(position.get("max_profit", 0), (entry - low) * quantity)
            # MAE is highest point reached - entry
            position["max_loss"] = max(position.get("max_loss", 0), (high - entry) * quantity)


    def _calculate_drawdown(self, current_value):
        if current_value >= self.max_equity:
            self.max_equity = current_value
            return 0
        return ((self.max_equity - current_value) / self.max_equity) * 100 if self.max_equity > 0 else 0

    @staticmethod
    def _calculate_unrealized_pnl(position, candle):
        price = float(candle["close"])
        return (
            (price - position["avg_price"]) * position["quantity"]
            if position["side"] == Side.BUY
            else (position["avg_price"] - price) * position["quantity"]
        )

    def _calculate_total_unrealized_pnl(self):
        total = 0.0
        for instrument_id, position in self.context.positions.items():
            candle = self.instrument_states.get(instrument_id, {}).get("last_candle")
            if candle is None:
                continue
            total += self._calculate_unrealized_pnl(position, candle)
        return total

    def _finalize_run(self):
        self._broadcast_progress_update(95, "Saving completed trades...")
        self._save_trades_from_context()
        self._broadcast_progress_update(98, "Calculating performance metrics...")
        self._calculate_metrics()

        self.run.refresh_from_db(fields=["status"])
        if self.run.status == BacktestStatus.CANCELLED:
            return

        self.run.status = BacktestStatus.COMPLETED
        self.run.completed_at = timezone.now()
        self.run.progress_pct = 100
        self.run.progress_message = "Backtest completed successfully."
        self.run.diagnostics = dict(self.context.diagnostics)
        self.run.save(update_fields=["status", "completed_at", "progress_pct", "progress_message", "diagnostics"])

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
                        "message": self.run.progress_message,
                        "timestamp": timezone.now().isoformat(),
                    }
                }
                async_to_sync(channel_layer.group_send)(group_name, message_data)
        except Exception as e:
            logger.warning(f"Failed to broadcast completion message: {e}")

    def _calculate_metrics(self):
        metrics, _ = BacktestMetrics.objects.get_or_create(run=self.run)
        for field in metrics._meta.concrete_fields:
            if field.name not in {"id", "run", "created_at", "updated_at"}:
                setattr(metrics, field.name, field.get_default())

        trades = list(BacktestTrade.objects.filter(run=self.run).order_by("entry_time"))

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
        metrics.profit_factor = gross_profit / gross_loss if gross_loss else None
        metrics.expectancy = float(np.mean(pnl_series)) if pnl_series else 0
        metrics.payoff_ratio = float(metrics.avg_win) / abs(float(metrics.avg_loss)) if metrics.avg_loss else None

        metrics.final_capital = self.context.current_capital
        metrics.total_return_pct = ((self.context.current_capital - self.initial_capital) / self.initial_capital) * 100 if self.initial_capital else 0
        metrics.total_brokerage = sum(float(t.brokerage) for t in trades)
        metrics.total_slippage = sum(float(t.slippage) for t in trades)
        metrics.total_charges = sum(float((t.charges_json or {}).get("total_charges", 0) or 0) for t in trades)
        metrics.avg_mae = np.mean([float(t.mae or 0) for t in trades]) if trades else 0
        metrics.avg_mfe = np.mean([float(t.mfe or 0) for t in trades]) if trades else 0
        instrument_breakdown = {}
        for trade in trades:
            symbol = trade.instrument.symbol if trade.instrument else "Unknown"
            summary = instrument_breakdown.setdefault(symbol, {"trades": 0, "pnl": 0.0, "wins": 0})
            pnl = float(trade.net_pnl)
            summary["trades"] += 1
            summary["pnl"] += pnl
            summary["wins"] += int(pnl > 0)
        metrics.instrument_breakdown_json = {
            symbol: {
                "trades": summary["trades"],
                "pnl": round(summary["pnl"], 2),
                "win_rate": summary["wins"] / summary["trades"] * 100,
            }
            for symbol, summary in sorted(instrument_breakdown.items())
        }
        efficiencies = [
            (float(trade.net_pnl) / float(trade.mfe))
            for trade in trades
            if float(trade.mfe or 0) != 0
        ]
        metrics.trade_efficiency = np.mean(efficiencies) if efficiencies else 0
        metrics.monthly_returns_json = self._calculate_monthly_returns()

        drawdown_series = [float(point.drawdown_pct) for point in self.equity_curve]
        metrics.max_drawdown_pct = max(drawdown_series) if drawdown_series else 0
        peak = self.initial_capital
        max_drawdown_amount = 0.0
        for point in self.equity_curve:
            equity = float(point.equity_value)
            peak = max(peak, equity)
            max_drawdown_amount = max(max_drawdown_amount, peak - equity)
        metrics.max_drawdown_amount = max_drawdown_amount
        net_profit = float(metrics.final_capital) - self.initial_capital
        metrics.recovery_factor = net_profit / max_drawdown_amount if max_drawdown_amount else None

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
            daily_returns = daily_equity.pct_change(fill_method=None)
            if len(daily_returns):
                daily_returns.iloc[0] = (daily_equity.iloc[0] / self.initial_capital - 1) if self.initial_capital else 0
            daily_returns = daily_returns.dropna()

            if len(daily_returns) > 1:
                # Sharpe Ratio using daily returns
                mean_return = np.mean(daily_returns)
                std_return = np.std(daily_returns)
                if std_return > 0:
                    # Annualize: multiply by sqrt(252) for daily returns
                    metrics.sharpe_ratio = (mean_return / std_return) * np.sqrt(252)
                    metrics.volatility_pct = (std_return * np.sqrt(252)) * 100

                # Sortino Ratio using downside deviation
                downside_deviation = float(np.sqrt(np.mean(np.minimum(daily_returns.to_numpy(), 0) ** 2)))
                if downside_deviation > 0:
                    metrics.sortino_ratio = (mean_return / downside_deviation) * np.sqrt(252)

        metrics.max_consecutive_wins, metrics.max_consecutive_losses = self._consecutive_streaks(pnl_series)
        metrics.cagr = self._calculate_cagr()
        if metrics.max_drawdown_pct:
            metrics.calmar_ratio = float(metrics.cagr) / float(metrics.max_drawdown_pct)
        metrics.max_drawdown_duration_days = self._calculate_drawdown_duration_days()

        metrics.save()
        return None

    def _check_cancelled(self):
        import time
        now = time.monotonic()
        if now - getattr(self, "_last_cancel_check", 0) < 5.0:
            return
        self._last_cancel_check = now
        status = BacktestRun.objects.filter(pk=self.run.pk).values_list("status", flat=True).first()
        if status is None or status == BacktestStatus.CANCELLED:
            raise BacktestCancelled()
        self.run.status = status


    def _calculate_monthly_returns(self):
        if not self.equity_curve:
            return {}
        df = pd.DataFrame(
            [{"timestamp": point.timestamp, "equity": float(point.equity_value)} for point in self.equity_curve]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        monthly_equity = df["equity"].resample("ME").last().dropna()
        returns = {}
        previous_equity = self.initial_capital
        for index, equity in monthly_equity.items():
            returns[index.strftime("%Y-%m")] = ((float(equity) / previous_equity) - 1) * 100 if previous_equity else 0.0
            previous_equity = float(equity)
        return returns

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
        duration_days = max((self.run.end_date - self.run.start_date).days + 1, 1)
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

        points = sorted(self.equity_curve, key=lambda point: point.timestamp)
        peak_equity = self.initial_capital
        peak_timestamp = points[0].timestamp
        drawdown_start = None
        longest = 0
        for point in points:
            equity = float(point.equity_value)
            if equity >= peak_equity:
                if drawdown_start is not None:
                    longest = max(longest, (point.timestamp - drawdown_start).days)
                    drawdown_start = None
                peak_equity = equity
                peak_timestamp = point.timestamp
            elif drawdown_start is None:
                drawdown_start = peak_timestamp
        if drawdown_start is not None:
            longest = max(longest, (points[-1].timestamp - drawdown_start).days)
        return longest


    def _process_entry(self, instrument, candle, timestamp, executor, current_candles):
        """Resolve and size configured entry routes, then queue next-open fills."""
        spot_price = float(candle["close"])
        entry_side = executor.entry_config.get("entry_side", Side.BUY)
        watch = self.watchlist_by_instrument_id.get(instrument.id)
        if watch is None:
            self.context.diagnostics["route_rejections"] += 1
            logger.warning("No watchlist config for backtest instrument %s", instrument.id)
            return

        routes = [dict(route) for route in (watch.get("execution_routes") or [])]
        resolutions = InstrumentResolver.resolve(watch, entry_side, spot_price=spot_price, routes_data=routes)
        available_capital = self.context.get_available_capital()
        for execution_instrument, execution_side, sizing in resolutions:
            execution_instrument_id = execution_instrument if isinstance(execution_instrument, int) else getattr(execution_instrument, "id", None)
            routed_instrument = execution_instrument if not isinstance(execution_instrument, int) else self.instruments_by_id.get(execution_instrument_id)
            execution_candle = current_candles.get(execution_instrument_id)

            if routed_instrument is None or execution_candle is None:
                self.context.diagnostics["route_rejections"] += 1
                logger.warning("Skipping backtest route for instrument %s: instrument or candle is unavailable", execution_instrument_id)
                continue

            execution_price = float(execution_candle["close"])
            lot_size = getattr(routed_instrument, "lot_size", 1) or 1
            risk_evaluator = RiskEvaluator(available_capital)
            try:
                quantity = max(int(risk_evaluator.calculate_quantity(
                    sizing_config=sizing if sizing is not None else self.config,
                    entry_price=execution_price,
                    lot_size=lot_size,
                ) or 0), 0)
            except Exception:
                self.context.diagnostics["sizing_rejections"] += 1
                logger.exception("Backtest position sizing failed for execution instrument %s", execution_instrument_id)
                continue

            if quantity <= 0:
                self.context.diagnostics["sizing_rejections"] += 1
                continue

            BacktestExecutionService.execute_market_order(
                self.context,
                routed_instrument,
                execution_side,
                quantity,
                execution_price,
                timestamp,
                self.config,
                exit_reason="strategy_entry",
                slippage_pct=self.run.slippage_pct,
                execute_immediately=False,
            )
            available_capital = max(available_capital - execution_price * quantity, 0.0)
            self.context.diagnostics["queued_entries"] += 1

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
                slippage=float(trade_data.get('slippage', 0)),
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
