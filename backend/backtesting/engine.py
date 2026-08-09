import copy
import logging
from datetime import datetime, time

import numpy as np
import pandas as pd
from django.utils import timezone

from common.enums import BacktestStatus, OrderType, Side
from common.trading_utils import (
    get_any_field,
    minutes_since_session_open,
    get_exchange_times,
)
from rules_engine.utils import compute_sl_distance_from_config
from marketdata.calendar_service import EventCalendarService
from marketdata.access import StrategyMarketDataService
from marketdata.services import FyersDataService
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

        self.risk_snapshot = copy.deepcopy(self.run.risk_profile_snapshot or {})
        self.initial_capital = float(self.run.initial_capital)
        self.current_capital = self.initial_capital

        self.data_resolution = MarketDataService.normalize_timeframe(self.config.get("time_rule", {}).get("candle_timeframe", "5m"))
        self.candle_completion_rule = self.config.get("time_rule", {}).get("candle_completion_rule", "ON_CLOSE")

        self.risk_evaluator = RiskEvaluator(self.initial_capital)

        self.equity_curve = []
        self.trades_to_create = []
        self.open_position = None
        self.open_positions = {}
        self.instrument_states = {}
        self.max_equity = self.initial_capital
        self.max_drawdown = 0
        self.last_entry_time = None
        self.last_trade = None
        self.halt_state = {"active_until": None, "reason": None}
        self.instrument = None
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
            for route in watch.execution_routes.all():
                if route.route_type in ['FUTURES', 'OPTIONS'] and route.target_underlying_instrument:
                    instruments_to_fetch.add(route.target_underlying_instrument)

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
                self.instrument = instrument
                mtf_data = payload.get("mtf_data", {})
                base_timeframe = payload.get("base_timeframe") or self.data_resolution
                self.market_data_cache[(instrument.id, base_timeframe)] = df

                from rules_engine.evaluator import IndicatorEngine
                mtf_indicator_engines = {}
                for tf, tdf in mtf_data.items():
                    mtf_indicator_engines[tf] = IndicatorEngine(tdf)

                base_evaluator = RuleEvaluator(
                    df,
                    candle_completion_rule=self.candle_completion_rule,
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
                    "entry_signals": executor.evaluate_entry_signals(executor.completed_signal_frame(df)),
                }
                self.instrument_states[instrument_id] = {
                    "reentry_count": 0,
                    "last_exit_time": None,
                    "last_entry_time": None,
                    "last_trade": None,
                    "last_candle": None,
                    "pending_entry_order": None,
                }
                all_timestamps.update(df.index.tolist())

            daily_stats = {"trades": 0, "pnl": 0.0}
            current_day = None

            sorted_timestamps = sorted(all_timestamps)

            # Filter timestamps to strictly start after the requested start_date
            # The earlier candles were only fetched for indicator warmup
            start_dt_tz_aware = timezone.make_aware(datetime.combine(self.run.start_date, datetime.min.time()))

            total_timestamps = len(sorted_timestamps)
            last_progress_pct = 0

            for ts_idx, timestamp in enumerate(sorted_timestamps):
                if timestamp < start_dt_tz_aware:
                    continue

                self._check_cancelled()

                # B19: Update progress more frequently (every 1%) and broadcast via WebSocket
                if total_timestamps > 0:
                    current_pct = int((ts_idx / total_timestamps) * 100)
                    if current_pct >= last_progress_pct + 1:  # Changed from 5 to 1 for better UX
                        last_progress_pct = current_pct
                        self._broadcast_progress_update(current_pct, f"Processing candles... {current_pct}%")

                if current_day != timestamp.date():
                    current_day = timestamp.date()
                    daily_stats = {"trades": 0, "pnl": 0.0}
                    self.halt_state = {"active_until": None, "reason": None}
                    for state in self.instrument_states.values():
                        state["reentry_count"] = 0
                        state["last_exit_time"] = None

                    # Bug #2 fix: Populate active_events_today for special event filters
                    self._populate_active_events(current_day)

                for instrument_id, context in contexts.items():
                    df = context["df"]
                    df_dict = context["df_dict"]

                    candle = df_dict.get(timestamp)
                    if candle is None:
                        continue
                    state = self.instrument_states[instrument_id]
                    state["last_candle"] = candle
                    self._set_active_context(instrument_id, context["instrument"])

                    # Phase 0: Add market hours check
                    ts_time = timestamp.time()
                    exchange = self.config.get("exchange") or getattr(self.run.strategy, "exchange", "NSE")
                    market_open, market_close = get_exchange_times(exchange)
                    is_in_no_trade_zone = context["executor"].is_in_no_trade_zone(timestamp) or (ts_time < market_open or ts_time >= market_close)

                    open_pos = self.open_positions.get(instrument_id)
                    stats = self._build_runtime_stats(candle, daily_stats, context["instrument"], timestamp)

                    # Portfolio risk evaluation (replaces non-existent evaluate_halt_conditions)
                    risk_profile = self.risk_snapshot.get("profile", {})
                    portfolio_eval = self.risk_evaluator.evaluate_portfolio_risk(risk_profile, stats)
                    if portfolio_eval.get("breached"):
                        self._apply_portfolio_halt(portfolio_eval, timestamp)
                        if open_pos:
                            self.open_position = open_pos
                            self.close_position(timestamp, float(candle["close"]), "Portfolio Risk Breach")
                            state["last_exit_time"] = timestamp
                            state["reentry_count"] += 1
                            daily_stats["trades"] += 1
                            daily_stats["pnl"] += float(self.trades_to_create[-1].net_pnl)
                            open_pos = None

                    # Bug #4 fix: Act on auto_disable_rules result
                    auto_disable_eval = self.risk_evaluator.evaluate_auto_disable_rules(
                        self.config.get("auto_disable_rules", []),
                        stats,
                    )
                    if auto_disable_eval.get("should_disable"):
                        if open_pos:
                            self.open_position = open_pos
                            self.close_position(timestamp, float(candle["close"]), "Auto-Disable Triggered")
                            state["last_exit_time"] = timestamp
                            state["reentry_count"] += 1
                            daily_stats["trades"] += 1
                            daily_stats["pnl"] += float(self.trades_to_create[-1].net_pnl)
                            open_pos = None
                        self.halt_state = {
                            "active_until": datetime.combine(timestamp.date(), time(23, 59, 59)),
                            "reason": auto_disable_eval.get("matches", [{}])[0].get("message", "Auto-disable triggered"),
                        }

                    if open_pos:
                        self.open_position = open_pos
                        self._update_mae_mfe(candle)

                        # Use StrategyExecutor for EXIT Logic
                        pos_state = {
                            "avg_price": float(open_pos["entry_price"]),
                            "side": open_pos["side"],
                            "peak_price": float(open_pos.get("peak_price", candle["high"] if open_pos["side"] == Side.BUY else candle["low"])),
                            "trailing_stop": open_pos.get("trailing_stop"),
                            "trailing_sl": open_pos.get("trailing_sl"),
                            "trailing_target": open_pos.get("trailing_target"),
                            "entry_time": open_pos["entry_time"],
                            "sl_distance": compute_sl_distance_from_config(self.config, open_pos["entry_price"]),
                            "instrument_expiry_date": getattr(open_pos.get("instrument"), "expiry_date", None),
                        }
                        # Update peak price tracking
                        if open_pos["side"] == Side.BUY:
                            pos_state["peak_price"] = max(pos_state["peak_price"], float(candle["high"]))
                        else:
                            pos_state["peak_price"] = min(pos_state["peak_price"], float(candle["low"]))

                        executor = context["executor"]
                        should_exit, reason, action, action_params = executor.evaluate_exit_logic(pos_state, df.iloc[:df.index.get_loc(timestamp)+1], timestamp)

                        reverse_enabled = self.config.get("reentry_rule", {}).get("allow_reverse_entry", False)
                        entry_side = executor.entry_config.get("entry_side", Side.BUY)
                        if (
                            not should_exit
                            and reverse_enabled
                            and not is_in_no_trade_zone
                            and entry_side != open_pos["side"]
                            and bool(context["entry_signals"].get(timestamp, False))
                        ):
                            should_exit = True
                            reason = "Reverse Entry Signal"
                            action = "EXIT_ALL"
                            action_params = {}

                        # Preserve trailing state for backtest persistence
                        open_pos["trailing_stop"] = pos_state.get("trailing_stop")
                        open_pos["trailing_sl"] = pos_state.get("trailing_sl")
                        open_pos["trailing_target"] = pos_state.get("trailing_target")
                        open_pos["peak_price"] = pos_state.get("peak_price")

                        if should_exit:
                            if action == 'MOVE_TO_BREAKEVEN':
                                if not open_pos.get(f'breakeven_{reason}'):
                                    open_pos['protected_stop_price'] = open_pos['entry_price']
                                    open_pos[f'breakeven_{reason}'] = True
                            elif action == 'PARTIAL_EXIT':
                                exit_pct = float(action_params.get('exit_pct', 50))
                                if not open_pos.get(f'partial_exit_{reason}'):
                                    exit_qty = int(open_pos["quantity"] * (exit_pct / 100.0))
                                    if exit_qty > 0:
                                        self.close_position(timestamp, float(candle["close"]), f"Partial Exit ({exit_pct}%): {reason}", exit_qty=exit_qty)
                                        daily_stats["trades"] += 1
                                        daily_stats["pnl"] += float(self.trades_to_create[-1].net_pnl)
                                        open_pos[f'partial_exit_{reason}'] = True
                            else:
                                self.close_position(timestamp, float(candle["close"]), reason)
                                state["last_exit_time"] = timestamp
                                state["reentry_count"] += 1
                                daily_stats["trades"] += 1
                                daily_stats["pnl"] += float(self.trades_to_create[-1].net_pnl)
                                open_pos = None

                    entry_side = context["executor"].entry_config.get("entry_side", Side.BUY)
                    allow_entry = not open_pos or (open_pos and open_pos["side"] == entry_side)

                    if allow_entry:
                        executor = context["executor"]

                        # 1. Handle Pending Entries (from ON_CLOSE/ON_OPEN signal in previous candle)
                        pending_orders = state.get("pending_entry_order")
                        if pending_orders:
                            if not isinstance(pending_orders, list):
                                pending_orders = [pending_orders]

                            if is_in_no_trade_zone:
                                state["pending_entry_order"] = None
                            else:
                                unfilled = []
                                expiry = self.config.get("entry_rule", {}).get("pending_order_expiry_candles", 5)
                                for p_order in pending_orders:
                                    p_order["candles_elapsed"] = p_order.get("candles_elapsed", 0) + 1
                                    if p_order["candles_elapsed"] > expiry:
                                        continue
                                    if not self._try_fill_entry_order(timestamp, candle, context["instrument"], p_order):
                                        unfilled.append(p_order)
                                state["pending_entry_order"] = unfilled if unfilled else None
                            continue

                        if self._is_halted(timestamp) or is_in_no_trade_zone:
                            continue

                        # 2. Check for New Entries via StrategyExecutor
                        can_enter, reason = executor.can_enter(stats, timestamp)
                        if can_enter and bool(context["entry_signals"].get(timestamp, False)):
                            orders = self.place_order(
                                timestamp, candle, context["instrument"], daily_stats, executor=executor,
                            )
                            if self.run.fill_model in ("NEXT_OPEN", "VWAP") and self.candle_completion_rule in ("ON_CLOSE", "ON_OPEN"):
                                state["pending_entry_order"] = orders or None
                                continue

                            unfilled = []
                            for order in orders:
                                if not self._try_fill_entry_order(timestamp, candle, context["instrument"], order):
                                    unfilled.append(order)
                            if unfilled:
                                state["pending_entry_order"] = unfilled

                    self._persist_active_context(instrument_id)

                total_value = self.current_capital + self._calculate_total_unrealized_pnl()

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

    def place_order(self, timestamp, candle, instrument, daily_stats, executor=None, signal_candle=None):
        """
        Build entry order intents using the same strategy/risk checks used by
        paper/live at order placement time. Returns a list of orders (one for each route).
        """
        executor = executor or self.executor
        sig = signal_candle if signal_candle is not None else candle
        otype, entry_price, trigger_price = executor.resolve_entry_order(sig, execution_candle=candle)
        entry_side = executor.entry_config.get("entry_side", Side.BUY)

        order_price = entry_price
        if order_price is None and trigger_price is not None:
            order_price = trigger_price
        if order_price is None:
            order_price = float(candle["close"])
        order_price = float(order_price)

        entry_price = float(entry_price) if entry_price is not None else None
        trigger_price = float(trigger_price) if trigger_price is not None else None
        if otype == OrderType.MARKET:
            entry_price = None

        stats = self._build_runtime_stats(candle, daily_stats, instrument, timestamp)

        ok, _ = self.risk_evaluator.check_strategy_limits(self.config, stats)
        if not ok:
            return []

        ok, _ = self.risk_evaluator.check_portfolio_risk(self.config.get("risk_profile", {}), stats)
        if not ok:
            return []

        # Step 1: Resolve execution instrument
        from instruments.models import WatchlistInstrument
        from instruments.services import InstrumentResolver
        watch = WatchlistInstrument.objects.filter(
            strategy_id=self.run.strategy_id, instrument=instrument
        ).first()

        spot_price = order_price
        if watch:
            for route in watch.execution_routes.all():
                if route.route_type in ['FUTURES', 'OPTIONS'] and route.target_underlying_instrument:
                    underlying_id = route.target_underlying_instrument.id
                    if underlying_id in self.datasets:
                        try:
                            # Try to get the underlying candle at the exact same timestamp
                            u_candle = self.datasets[underlying_id]["df_dict"][timestamp]
                            spot_price = float(u_candle["close"])
                        except KeyError:
                            pass
                    break

        resolutions = InstrumentResolver.resolve(
            watch, entry_side, spot_price=spot_price
        )

        # BACKTEST F&O LIMITATION: Force DIRECT execution since we don't have historical option prices.
        # Otherwise, sizing will use Index price (e.g. 45000) * Option Lot Size (15) = Massive incorrect capital.
        safe_resolutions = []
        for exec_instr, exec_side, sizing_config in resolutions:
            if exec_instr.instrument_type in ('OPTION', 'FUTURE'):
                safe_resolutions.append((instrument, exec_side, sizing_config))
            else:
                safe_resolutions.append((exec_instr, exec_side, sizing_config))

        orders = []
        for exec_instrument, exec_side, sizing_config in safe_resolutions:
            if not sizing_config:
                sizing_config = self.config

            # Step 4: Calculate quantity with lot size rounding
            lot_size = getattr(exec_instrument, 'lot_size', 1) or 1
            quantity = self.risk_evaluator.calculate_quantity(sizing_config, order_price, stats=stats, lot_size=lot_size)
            if quantity <= 0:
                continue

            orders.append({
                "order_type": otype,
                "entry_price": entry_price,
                "trigger_price": trigger_price,
                "signal_close": float(sig["close"]),
                "side": exec_side,
                "quantity": quantity,
                "created_at": timestamp,
                "instrument": exec_instrument,
            })

        return orders

    def _try_fill_entry_order(self, timestamp, candle, instrument, order):
        fill_price = self._entry_order_fill_price(order, candle)
        if fill_price is None:
            return False

        adjusted_fill = float(TradingCostCalculator.apply_slippage(fill_price, order["side"], self.run.slippage_pct))

        exec_instrument = order.get("instrument", instrument)
        self._open_position(timestamp, adjusted_fill, order["side"], exec_instrument, order["quantity"], signal_instrument_id=instrument.id)
        self.last_entry_time = timestamp
        return True

    def _entry_order_fill_price(self, order, candle):
        otype = order["order_type"]
        entry_side = order["side"]
        entry_price = order.get("entry_price")
        trigger_price = order.get("trigger_price")
        candle_high = float(candle["high"])
        candle_low = float(candle["low"])
        candle_open = float(candle["open"])

        if otype in (OrderType.STOP_LIMIT, OrderType.STOP_MARKET) and trigger_price is not None:
            trigger_price = float(trigger_price)
            if entry_side == Side.BUY and candle_high < trigger_price:
                return None
            if entry_side == Side.SELL and candle_low > trigger_price:
                return None
            if entry_side == Side.BUY and candle_open >= trigger_price:
                return candle_open
            if entry_side == Side.SELL and candle_open <= trigger_price:
                return candle_open
            return float(entry_price) if entry_price is not None else trigger_price

        if otype == OrderType.LIMIT and entry_price is not None:
            entry_price = float(entry_price)
            if entry_side == Side.BUY and candle_low > entry_price:
                return None
            if entry_side == Side.SELL and candle_high < entry_price:
                return None
            if entry_side == Side.BUY and candle_open <= entry_price:
                return candle_open
            if entry_side == Side.SELL and candle_open >= entry_price:
                return candle_open
            return entry_price

        if entry_price is not None:
            return float(entry_price)

        if otype == OrderType.MARKET:
            fill_model = self.run.fill_model
            if fill_model == 'SIGNAL_CLOSE':
                return order.get("signal_close", float(candle["close"]))
            elif fill_model == 'VWAP':
                return (float(candle["high"]) + float(candle["low"]) + float(candle["close"])) / 3.0
            else: # NEXT_OPEN
                return float(candle["open"])

        return float(candle["close"])


    def _update_mae_mfe(self, candle):
        pos = self.open_position
        high = float(candle["high"])
        low = float(candle["low"])
        entry = pos["entry_price"]

        if pos["side"] == Side.BUY:
            # MFE is highest point reached - entry
            pos["max_profit"] = max(pos.get("max_profit", 0), high - entry)
            # MAE is entry - lowest point reached
            pos["max_loss"] = max(pos.get("max_loss", 0), entry - low)
        else:
            # MFE is entry - lowest point reached
            pos["max_profit"] = max(pos.get("max_profit", 0), entry - low)
            # MAE is highest point reached - entry
            pos["max_loss"] = max(pos.get("max_loss", 0), high - entry)


    def _calculate_drawdown(self, current_value):
        if current_value > self.max_equity:
            self.max_equity = current_value
            return 0
        return ((self.max_equity - current_value) / self.max_equity) * 100 if self.max_equity > 0 else 0

    def _open_position(self, timestamp, price, side, instrument, quantity, signal_instrument_id=None):
        dict_key = signal_instrument_id if signal_instrument_id is not None else instrument.id
        existing_pos = self.open_positions.get(dict_key)

        if existing_pos and existing_pos["side"] == side:
            old_qty = existing_pos["quantity"]
            old_price = existing_pos["entry_price"]
            new_qty = old_qty + quantity
            avg_price = ((old_price * old_qty) + (float(price) * quantity)) / new_qty
            existing_pos["quantity"] = new_qty
            existing_pos["entry_price"] = avg_price
            return

        self.open_position = {
            "side": side,
            "entry_time": timestamp,
            "entry_price": float(price),
            "quantity": quantity,
            "instrument": instrument,
            "max_profit": 0.0,
            "max_loss": 0.0,
            "trailing_sl": None,
            "trailing_target": None,
            "signal_instrument_id": signal_instrument_id,
        }
        self.open_positions[dict_key] = self.open_position

    def close_position(self, timestamp, price, reason, exit_qty=None):
        pos = self.open_position
        entry_price = pos["entry_price"]
        quantity = exit_qty or pos["quantity"]
        instrument = pos["instrument"]
        side_closed = pos["side"]

        exit_side = Side.SELL if side_closed == Side.BUY else Side.BUY
        exit_price = float(TradingCostCalculator.apply_slippage(float(price), exit_side, self.run.slippage_pct))

        gross_pnl = (exit_price - entry_price) * quantity if side_closed == Side.BUY else (entry_price - exit_price) * quantity

        instrument_type = getattr(instrument, 'instrument_type', 'EQUITY')
        charge_profile = self.run.charge_profile
        if charge_profile is None and self.run.include_charges:
            from brokers.models import BrokerChargeProfile
            charge_profile = (
                BrokerChargeProfile.objects.filter(user=self.run.user, is_default=True).first()
                or BrokerChargeProfile.objects.filter(user=self.run.user).first()
            )
            if charge_profile:
                self.run.charge_profile = charge_profile
                self.run.save(update_fields=['charge_profile'])

        net_pnl_dec, charges_dict = TradingCostCalculator.calculate_net_pnl(
            gross_pnl=gross_pnl,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            side=side_closed,
            instrument_type=instrument_type,
            entry_time=pos["entry_time"],
            exit_time=timestamp,
            profile=charge_profile,
            include_charges=self.run.include_charges,
        )

        net_pnl = float(net_pnl_dec)
        brokerage = float(charges_dict.get('entry_charges', {}).get('brokerage', 0) + charges_dict.get('exit_charges', {}).get('brokerage', 0))
        slippage = 0

        if not hasattr(self, 'consecutive_losses'):
            self.consecutive_losses = 0

        if net_pnl > 0:
            self.consecutive_losses = 0
        elif net_pnl < 0:
            self.consecutive_losses += 1

        self.current_capital += net_pnl
        self.risk_evaluator.portfolio_capital = self.current_capital

        holding_minutes = max(int((timestamp - pos["entry_time"]).total_seconds() / 60), 0)
        trade = BacktestTrade(
            run=self.run,
            instrument=instrument,
            side=side_closed,
            entry_time=pos["entry_time"],
            exit_time=timestamp,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            gross_pnl=gross_pnl,
            brokerage=brokerage,
            slippage=slippage,
            net_pnl=net_pnl,
            charges_json=charges_dict,
            pnl_pct=(net_pnl / (entry_price * quantity)) * 100 if entry_price > 0 and quantity > 0 else 0,
            mae=pos.get("max_loss", 0),
            mfe=pos.get("max_profit", 0),
            holding_duration_minutes=holding_minutes,
            exit_reason=reason,
        )
        self.trades_to_create.append(trade)

        if exit_qty and exit_qty < pos["quantity"]:
            pos["quantity"] -= exit_qty
        else:
            self.open_position = None
            dict_key = pos.get("signal_instrument_id") or pos["instrument"].id
            self.open_positions.pop(dict_key, None)

    def _calculate_unrealized_pnl(self, candle):
        pos = self.open_position
        if not pos:
            return 0
        price = float(candle["close"])
        return (price - pos["entry_price"]) * pos["quantity"] if pos["side"] == Side.BUY else (pos["entry_price"] - price) * pos["quantity"]

    def _calculate_total_unrealized_pnl(self):
        total = 0.0
        for instrument_id, position in self.open_positions.items():
            if position is None:
                continue
            candle = self.instrument_states.get(instrument_id, {}).get("last_candle")
            if candle is None:
                continue
            total += self._calculate_position_unrealized_pnl(position, candle)
        return total

    def _force_close_open_positions(self, timestamp):
        """Force close any open positions at the end of the simulation."""
        for pos in list(self.open_positions.values()):
            if pos is None:
                continue
            instrument_id = pos["instrument"].id
            state = self.instrument_states.get(instrument_id, {})
            candle = state.get("last_candle")
            if candle is not None:
                self.open_position = pos
                self.close_position(
                    timestamp=timestamp,
                    price=float(candle["close"]),
                    reason="End of Backtest Square-off"
                )

    def _finalize_run(self):
        if self.trades_to_create:
            BacktestTrade.objects.bulk_create(self.trades_to_create)
        if self.equity_curve:
            EquityCurvePoint.objects.bulk_create(self.equity_curve, ignore_conflicts=True)
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
            metrics.final_capital = self.current_capital
            metrics.total_return_pct = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100 if self.initial_capital else 0
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

        metrics.final_capital = self.current_capital
        metrics.total_return_pct = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100 if self.initial_capital else 0
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

        if len(pnl_series) > 1:
            std = np.std(pnl_series)
            downside = np.std([min(p, 0) for p in pnl_series])
            if std > 0:
                metrics.sharpe_ratio = (np.mean(pnl_series) / std) * np.sqrt(252)
                metrics.volatility_pct = (std / self.initial_capital) * 100 if self.initial_capital else 0
            if downside > 0:
                metrics.sortino_ratio = (np.mean(pnl_series) / downside) * np.sqrt(252)
            if metrics.max_drawdown_pct:
                metrics.calmar_ratio = float(metrics.total_return_pct) / float(metrics.max_drawdown_pct)

        metrics.max_consecutive_wins, metrics.max_consecutive_losses = self._consecutive_streaks(pnl_series)
        metrics.cagr = self._calculate_cagr()
        metrics.max_drawdown_duration_days = self._calculate_drawdown_duration_days()

        metrics.save()
        return None

    def _build_runtime_stats(self, candle, daily_stats, instrument, timestamp):
        state = self.instrument_states.get(instrument.id, {})
        open_pos = self.open_positions.get(instrument.id)

        atr_value = 0.0
        if getattr(self, "rule_evaluator", None) and getattr(self.rule_evaluator, "indicator_engine", None):
            from common.enums import OperandType
            atr_series = self.rule_evaluator.indicator_engine.get_series(OperandType.ATR, {"period": 14})
            if atr_series is not None and not atr_series.empty:
                if timestamp in atr_series.index:
                    atr_value = float(atr_series.loc[timestamp])
                else:
                    atr_value = float(atr_series.iloc[-1])

        return {
            "daily_pnl": daily_stats.get("pnl", 0.0),
            "daily_trades": daily_stats.get("trades", 0),
            "instrument_daily_trades": state.get("reentry_count", 0),
            "consecutive_losses": getattr(self, "consecutive_losses", 0),
            "last_exit_time": state.get("last_exit_time"),
            "last_entry_time": state.get("last_entry_time"),
            "open_positions": len(self.open_positions),
            "drawdown": self._calculate_drawdown(self.current_capital),
            "atr": atr_value,
            "total_exposure": self._total_exposure(),
            "strategy_allocation_pct": (self._total_exposure() / self.initial_capital) * 100 if self.initial_capital else 0,
            "instrument_exposure_pct": ((float(candle["close"]) * open_pos["quantity"]) / self.initial_capital) * 100 if open_pos and self.initial_capital else 0,
            "consecutive_losses": self._current_consecutive_losses(),
            "win_rate": self._current_win_rate(),
            "weekly_pnl": self._pnl_over_window(timestamp, 7),
            "monthly_pnl": self._pnl_over_window(timestamp, 30),
            "volatility": self._estimate_volatility(),
            "time_minutes": minutes_since_session_open(timestamp.time()),
            "minutes_since_open": minutes_since_session_open(timestamp.time()),
            "custom_value": daily_stats.get("custom_value", 0),
        }

    def _apply_halt_state(self, halt_eval, timestamp):
        duration = halt_eval.get("max_halt_duration_minutes", 0)
        active_until = datetime.combine(timestamp.date(), time(23, 59, 59)) if duration == 0 else timestamp + pd.Timedelta(minutes=duration)
        self.halt_state = {"active_until": active_until, "reason": "Trade Halt"}

    def _apply_portfolio_halt(self, portfolio_eval, timestamp):
        if portfolio_eval.get("breached"):
            breach_msg = "Portfolio Risk Breach"
            breaches = portfolio_eval.get("breaches", [])
            if breaches:
                breach_msg = breaches[0].get("message", breach_msg)
            self.halt_state = {
                "active_until": datetime.combine(timestamp.date(), time(23, 59, 59)),
                "reason": breach_msg,
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

    def _get_active_groups(self, rule_type):
        return [
            group
            for group in self.config.get("rule_groups", [])
            if get_any_field(group, "rule_type") == rule_type and get_any_field(group, "is_active", True)
        ]

    def _get_rules(self, group, *possible_keys):
        for key in possible_keys:
            rules = get_any_field(group, key)
            if rules:
                return list(rules)
        return []

    def _get_rule_evaluator(self, resolution):
        resolution = MarketDataService.normalize_timeframe(resolution or self.data_resolution)
        cache_key = (self.instrument.id, resolution)
        if cache_key in self.rule_evaluators:
            return self.rule_evaluators[cache_key]

        if not self.instrument:
            raise ValueError("Backtest instrument is not initialized")

        start_dt = datetime.combine(self.run.start_date, datetime.min.time())
        end_dt = datetime.combine(self.run.end_date, datetime.max.time())
        df = FyersDataService.get_backtest_candles(
            symbol=self.instrument.sym_ticker,
            resolution=resolution,
            start_dt=start_dt,
            end_dt=end_dt,
            fetch_missing=True,
            clean=True,
            persist=True,
        )
        if df.empty:
            logger.warning("No data found for timeframe override %s; falling back to base resolution", resolution)
            return self.rule_evaluator

        evaluator = RuleEvaluator(df)
        self.market_data_cache[cache_key] = df
        self.rule_evaluators[cache_key] = evaluator
        return evaluator



    def _minutes_in_trade(self, timestamp):
        if not self.open_position:
            return 0
        return max(int((timestamp - self.open_position["entry_time"]).total_seconds() / 60), 0)

    def _current_trade_loss_pct(self, price):
        if not self.open_position:
            return 0
        entry = self.open_position["entry_price"]
        if entry <= 0:
            return 0
        loss = ((entry - price) / entry) * 100 if self.open_position["side"] == Side.BUY else ((price - entry) / entry) * 100
        return max(loss, 0)


    def _current_consecutive_losses(self):
        streak = 0
        for trade in reversed(self.trades_to_create):
            if float(trade.net_pnl) < 0:
                streak += 1
            else:
                break
        return streak

    def _current_win_rate(self):
        if not self.trades_to_create:
            return 0
        wins = len([trade for trade in self.trades_to_create if float(trade.net_pnl) > 0])
        return (wins / len(self.trades_to_create)) * 100

    def _pnl_over_window(self, timestamp, days):
        cutoff = timestamp - pd.Timedelta(days=days)
        pnl = 0.0
        for trade in reversed(self.trades_to_create):
            if trade.exit_time:
                if trade.exit_time >= cutoff:
                    pnl += float(trade.net_pnl)
                else:
                    break
        return pnl

    def _estimate_volatility(self):
        # Volatility calculation during runtime is too expensive and unused by risk limits.
        # Max/average volatility is computed in _finalize_run for metrics instead.
        return 0.0

    def _set_active_context(self, instrument_id, instrument):
        self.instrument = instrument
        cache_key = (instrument.id, self.data_resolution)
        if cache_key not in self.rule_evaluators:
            cache_key = next(
                (key for key in self.rule_evaluators if key[0] == instrument.id),
                cache_key,
            )
        self.rule_evaluator = self.rule_evaluators.get(cache_key)
        self.open_position = self.open_positions.get(instrument_id)
        state = self.instrument_states[instrument_id]
        self.last_entry_time = state.get("last_entry_time")
        self.last_trade = state.get("last_trade")

    def _persist_active_context(self, instrument_id):
        state = self.instrument_states[instrument_id]
        state["last_entry_time"] = self.last_entry_time
        state["last_trade"] = self.last_trade
        if self.open_position:
            self.open_positions[instrument_id] = self.open_position
        else:
            self.open_positions.pop(instrument_id, None)

    def _calculate_position_unrealized_pnl(self, position, candle):
        price = float(candle["close"])
        return (price - position["entry_price"]) * position["quantity"] if position["side"] == Side.BUY else (position["entry_price"] - price) * position["quantity"]

    def _total_exposure(self):
        exposure = 0.0
        for instrument_id, position in self.open_positions.items():
            if position is None:
                continue
            candle = self.instrument_states.get(instrument_id, {}).get("last_candle")
            if candle is None:
                continue
            exposure += float(candle["close"]) * position["quantity"]
        return exposure

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
        if years <= 0 or self.initial_capital <= 0 or self.current_capital <= 0:
            return 0
        return ((self.current_capital / self.initial_capital) ** (1 / years) - 1) * 100

    def _calculate_drawdown_duration_days(self):
        longest = 0
        current = 0
        for point in self.equity_curve:
            if float(point.drawdown_pct) > 0:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        return longest


    def _deep_merge(self, base, updates):
        for key, value in (updates or {}).items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
