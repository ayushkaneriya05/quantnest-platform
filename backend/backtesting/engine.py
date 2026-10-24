"""Backtest orchestration: prepare history, replay the shared kernel, save reports."""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from django.utils import timezone

from common.enums import BacktestStatus
from execution.compiler import strategy_requirements, source_windows
from execution.preparation import PreparedMarket, candles_from_frame, contract_from_instrument
from execution.replay import OHLC_POLICY, Replay
from instruments.models import Instrument
from marketdata.calendar import MarketSessionCalendar
from marketdata.candles import prepare_frames
from .models import BacktestMetrics, BacktestRun, BacktestTrade, EquityCurvePoint
from .services import backtest_configuration, publish_backtest_update

logger = logging.getLogger(__name__)


class BacktestCancelled(Exception):
    pass


class BacktestEngine:
    """Database orchestration stays outside replay's decision and financial functions."""

    def __init__(self, run: BacktestRun):
        self.run = run
        self.config = backtest_configuration(run)
        self.initial_capital = float(run.initial_capital)
        self.equity_curve, self.trades_to_create = [], []
        self.max_equity = self.initial_capital
        self._last_progress_update_time = 0
        self._last_progress_message = None
        self.replay = None

    def load_data(self) -> list[PreparedMarket]:
        identities = {item['instrument_id'] for item in self.config['watchlist_instruments']}
        instruments = Instrument.objects.in_bulk(identities)
        if not identities or set(instruments) != identities:
            raise ValueError('The saved watchlist must contain available instruments.')
        markets = []
        quality = {'complete': True, 'instruments': [], 'warnings': [], 'simulation_policy': OHLC_POLICY}
        for index, instrument in enumerate(instruments.values()):
            self._broadcast_progress_update(1 + int(index / len(instruments) * 20),
                f'Preparing history for {instrument.sym_ticker}...')
            self._check_cancelled()
            calendar = MarketSessionCalendar.for_instrument(instrument)
            start = datetime.combine(self.run.start_date, datetime.min.time(), tzinfo=calendar.zone)
            end = datetime.combine(self.run.end_date, datetime.max.time(), tzinfo=calendar.zone)
            _, requirements, depths = strategy_requirements(self.config, calendar)
            frames, coverage = prepare_frames(instrument, frozenset(requirements),
                source_windows(requirements, depths, calendar, start, end), calendar)
            quality['instruments'].append(coverage)
            quality['complete'] = quality['complete'] and coverage['complete']
            self.run.data_quality = quality
            self.run.save(update_fields=['data_quality'])
            if not coverage['complete'] or any(frame.empty for frame in frames.values()):
                raise ValueError(f'Confirmed historical data is unavailable for {instrument.sym_ticker}.')
            earliest = min(frame.index[0].date() for frame in frames.values())
            calendar.load_holidays(earliest - timedelta(days=7), self.run.end_date + timedelta(days=7))
            candles = {tf: candles_from_frame(frame, tf, calendar) for tf, frame in frames.items()}
            for tf, count in requirements.items():
                if sum(bar.closed_at <= start for bar in candles[tf]) < count:
                    raise ValueError(f'Insufficient completed {tf} warmup for {instrument.sym_ticker}.')
            markets.append(PreparedMarket(contract_from_instrument(instrument), calendar, candles))
        return markets

    def run_simulation(self, markets=None):
        try:
            self._check_cancelled()
            if markets is None:
                markets = self.load_data()
            zone = ZoneInfo(self.config['time_rule']['timezone'])
            start = datetime.combine(self.run.start_date, datetime.min.time(), tzinfo=zone)
            end = datetime.combine(self.run.end_date, datetime.max.time(), tzinfo=zone)
            self.run.status, self.run.started_at, self.run.error_message = BacktestStatus.RUNNING, timezone.now(), ''
            self.run.data_quality = {**self.run.data_quality, 'simulation_policy': OHLC_POLICY,
                'execution_kernel': 1, 'ltp_semantics': 'Observed price; synthetic observations in OHLC replay.'}
            self.run.save(update_fields=['status', 'started_at', 'error_message', 'data_quality'])
            self.replay = Replay(identity=self.run.pk, version=self.run.strategy_version_id or 0,
                config=self.config, markets=markets, start=start, end=end, capital=self.run.initial_capital,
                profile=self.run.charge_profile_snapshot if self.run.include_charges else {},
                slippage=self.run.slippage_pct)
            for at in self.replay.run():
                self._check_cancelled()
                progress = 22 + int(72 * (at - start).total_seconds() / (end - start).total_seconds())
                self._broadcast_progress_update(progress, 'Replaying historical observations...')
            self.equity_curve = [EquityCurvePoint(run=self.run, timestamp=at, equity_value=value,
                drawdown_pct=self._calculate_drawdown(float(value))) for at, value in self.replay.equity]
            self.run.data_quality['final_position_policy'] = 'Close residual positions at the last completed candle price, with slippage and charges.'
            self.run.save(update_fields=['data_quality'])
            self._finalize_run()
        except BacktestCancelled:
            self.run.refresh_from_db(fields=['status'])
            self.run.completed_at = timezone.now()
            self.run.save(update_fields=['completed_at'])
        except Exception as exc:
            logger.exception('Backtest failed: %s', exc)
            self.run.status = BacktestStatus.FAILED
            self.run.error_message = str(exc)
            self.run.progress_message = f'Backtest failed: {exc}'[:255]
            self.run.completed_at = timezone.now()
            self.run.save(update_fields=['status', 'error_message', 'progress_message', 'completed_at'])
            publish_backtest_update(self.run)

    def _save_replay_results(self):
        for trade in self.replay.trades:
            entry = trade.charges.get('entry_charges', {})
            exit = trade.charges.get('exit_charges', {})
            turnover = trade.contract.value(trade.entry_price, trade.quantity)
            self.trades_to_create.append(BacktestTrade(run=self.run, instrument_id=trade.contract.instrument_id,
                side=trade.side, entry_time=trade.entry_time, exit_time=trade.exit_time,
                entry_price=trade.entry_price, exit_price=trade.exit_price, quantity=trade.quantity,
                gross_pnl=trade.gross, net_pnl=trade.net, charges_json=trade.charges, exit_reason=trade.reason,
                brokerage=entry.get('brokerage', 0) + exit.get('brokerage', 0), slippage=trade.slippage,
                pnl_pct=trade.net / turnover * 100 if turnover else 0, mae=trade.mae, mfe=trade.mfe,
                holding_duration_minutes=int((trade.exit_time - trade.entry_time).total_seconds() / 60)))
        BacktestTrade.objects.bulk_create(self.trades_to_create)
        EquityCurvePoint.objects.bulk_create(self.equity_curve, ignore_conflicts=True)

    def _broadcast_progress_update(self, progress_pct, message="Processing candles..."):
        """
        Broadcast backtest progress via WebSocket and save to database.
        Uses time-based throttling to avoid database hammering.
        """
        import time
        current_time = time.monotonic()
        progress_pct = min(max(int(progress_pct), self.run.progress_pct), 100)
        self.run.progress_pct = progress_pct
        self.run.progress_message = message
        message_changed = message != self._last_progress_message
        if not message_changed and progress_pct < 100 and current_time - self._last_progress_update_time < 0.5:
            return
        self.run.save(update_fields=["progress_pct", "progress_message"])
        self._last_progress_update_time = current_time
        self._last_progress_message = message
        publish_backtest_update(self.run)

    def _calculate_drawdown(self, current_value):
        if current_value >= self.max_equity:
            self.max_equity = current_value
            return 0
        return ((self.max_equity - current_value) / self.max_equity) * 100 if self.max_equity > 0 else 0

    def _finalize_run(self):
        self._broadcast_progress_update(95, "Saving completed trades...")
        self._save_replay_results()
        self._broadcast_progress_update(98, "Calculating performance metrics...")
        self._calculate_metrics()

        self.run.refresh_from_db(fields=["status"])
        if self.run.status == BacktestStatus.CANCELLED:
            return

        self.run.status = BacktestStatus.COMPLETED
        self.run.completed_at = timezone.now()
        self.run.progress_pct = 100
        self.run.progress_message = "Backtest completed successfully."
        self.run.diagnostics = dict(self.replay.diagnostics)
        self.run.save(update_fields=["status", "completed_at", "progress_pct", "progress_message", "diagnostics"])

        publish_backtest_update(self.run, trades_count=len(self.trades_to_create))

    def _calculate_metrics(self):
        metrics, _ = BacktestMetrics.objects.get_or_create(run=self.run)
        for field in metrics._meta.concrete_fields:
            if field.name not in {"id", "run", "created_at", "updated_at"}:
                setattr(metrics, field.name, field.get_default())

        trades = list(BacktestTrade.objects.filter(run=self.run).select_related('instrument').order_by("entry_time", "pk"))

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

        metrics.final_capital = float(self.replay.account.balance)
        metrics.total_return_pct = ((float(self.replay.account.balance) - self.initial_capital) / self.initial_capital) * 100 if self.initial_capital else 0
        metrics.total_brokerage = sum(float(t.brokerage) for t in trades)
        metrics.total_slippage = sum(float(t.slippage) for t in trades)
        metrics.total_charges = sum(float((t.charges_json or {}).get("total_charges", 0) or 0) for t in trades)
        metrics.avg_mae = np.mean([float(t.mae or 0) for t in trades]) if trades else 0
        metrics.avg_mfe = np.mean([float(t.mfe or 0) for t in trades]) if trades else 0
        instrument_breakdown = {}
        for trade in trades:
            symbol = trade.instrument.sym_ticker if trade.instrument else "Unknown"
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
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(
            self.config["time_rule"].get("timezone", "Asia/Kolkata"))
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
        if years <= 0 or self.initial_capital <= 0 or float(self.replay.account.balance) <= 0:
            return 0
        return ((float(self.replay.account.balance) / self.initial_capital) ** (1 / years) - 1) * 100

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


