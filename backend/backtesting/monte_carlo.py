import logging
import random

import numpy as np
from django.utils import timezone

from .models import BacktestTrade, MonteCarloResult, MonteCarloRun

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """
    Performs Monte Carlo simulations by shuffling trade sequences.
    Computes 7 metrics: Terminal Capital, Total Return, Max Drawdown,
    Win Rate, Sharpe Ratio, Profit Factor, and Expectancy.
    Also generates equity distribution data for histogram rendering.
    """

    ANNUALIZATION_FACTOR = 252  # Trading days in a year (Indian markets)

    def __init__(self, mc_run_id):
        self.run = MonteCarloRun.objects.get(id=mc_run_id)
        self.backtest = self.run.backtest_run

    def run_simulation(self):
        trades = list(BacktestTrade.objects.filter(run=self.backtest))
        if not trades:
            self.run.status = "FAILED"
            self.run.completed_at = timezone.now()
            self.run.save(update_fields=["status", "completed_at"])
            return

        pnl_sequence = [float(trade.net_pnl) for trade in trades]
        initial_capital = float(self.backtest.initial_capital)

        self.run.status = "RUNNING"
        self.run.save(update_fields=["status"])
        self.run.results.all().delete()

        iterations = int(self.run.num_simulations or 1000)
        confidence_level = float(self.run.confidence_level or 0.95)
        lower_pct = max((1 - confidence_level) / 2 * 100, 0)
        upper_pct = min((1 + confidence_level) / 2 * 100, 100)

        # ==========================================
        # 🚀 MASSIVE SPEED IMPROVEMENT: VECTORIZATION
        # ==========================================
        # Generate all random samples at once in a 2D matrix: shape (iterations, len(pnl_sequence))
        pnl_array = np.array(pnl_sequence)
        n_trades = len(pnl_array)
        
        # Matrix of simulated PNLs
        samples = np.random.choice(pnl_array, size=(iterations, n_trades), replace=True)

        # 1. Terminal Capital & Total Return
        cum_pnl = np.cumsum(samples, axis=1)
        equities = initial_capital + cum_pnl
        final_equities_arr = equities[:, -1]
        final_returns_arr = ((final_equities_arr - initial_capital) / initial_capital) * 100 if initial_capital else np.zeros(iterations)

        # 2. Max Drawdown
        # Calculate running maximums. (Include initial capital to catch immediate drawdowns)
        running_max = np.maximum.accumulate(equities, axis=1)
        running_max = np.maximum(running_max, initial_capital)
        # Avoid division by zero
        drawdowns = np.where(running_max > 0, ((running_max - equities) / running_max) * 100, 0)
        max_drawdowns_arr = np.max(drawdowns, axis=1)

        # 3. Win Rate
        wins_arr = np.sum(samples > 0, axis=1)
        win_rates_arr = (wins_arr / n_trades) * 100 if n_trades > 0 else np.zeros(iterations)

        # 4. Profit Factor
        win_pnls_arr = np.sum(np.where(samples > 0, samples, 0), axis=1)
        loss_pnls_arr = np.sum(np.where(samples < 0, np.abs(samples), 0), axis=1)
        profit_factors_arr = np.divide(
            win_pnls_arr, 
            loss_pnls_arr, 
            out=np.full(iterations, 999.0), 
            where=(loss_pnls_arr != 0)
        )
        # If both win and loss are 0, PF is 0
        profit_factors_arr[(loss_pnls_arr == 0) & (win_pnls_arr == 0)] = 0.0

        # 5. Expectancy
        losses_arr = n_trades - wins_arr
        avg_wins_arr = np.divide(win_pnls_arr, wins_arr, out=np.zeros(iterations), where=(wins_arr != 0))
        avg_losses_arr = np.divide(loss_pnls_arr, losses_arr, out=np.zeros(iterations), where=(losses_arr != 0))
        expectancies_arr = ((win_rates_arr / 100) * avg_wins_arr) - (((100 - win_rates_arr) / 100) * avg_losses_arr)

        # 6. Sharpe Ratio
        # Need prev equities to calculate trade-by-trade returns
        prev_equities = np.hstack([np.full((iterations, 1), initial_capital), equities[:, :-1]])
        prev_equities = np.maximum(prev_equities, 1) # Prevent div by 0
        returns_matrix = samples / prev_equities
        
        mean_returns = np.mean(returns_matrix, axis=1)
        std_returns = np.std(returns_matrix, axis=1)
        sharpes_arr = np.divide(
            mean_returns, 
            std_returns, 
            out=np.zeros(iterations), 
            where=(std_returns > 0)
        ) * np.sqrt(self.ANNUALIZATION_FACTOR)

        # Convert final_equities array to list for histogram parsing later
        final_equities = final_equities_arr.tolist()

        # Store all 7 metrics
        self._store_metric(
            "Terminal Capital",
            final_equities_arr,
            lower_pct, upper_pct, worst_is_min=True,
        )
        self._store_metric(
            "Total Return",
            final_returns_arr,
            lower_pct, upper_pct, worst_is_min=True,
        )
        self._store_metric(
            "Max Drawdown",
            max_drawdowns_arr,
            lower_pct, upper_pct, worst_is_min=False,
        )
        self._store_metric(
            "Win Rate",
            win_rates_arr,
            lower_pct, upper_pct, worst_is_min=True,
        )
        self._store_metric(
            "Sharpe Ratio",
            sharpes_arr,
            lower_pct, upper_pct, worst_is_min=True,
        )
        self._store_metric(
            "Profit Factor",
            profit_factors_arr,
            lower_pct, upper_pct, worst_is_min=True,
        )
        self._store_metric(
            "Expectancy",
            expectancies_arr,
            lower_pct, upper_pct, worst_is_min=True,
        )

        # B9: Store equity distribution for histogram
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        equity_distribution = {
            f"p{p}": float(np.percentile(final_equities, p)) for p in percentiles
        }
        equity_distribution["min"] = float(min(final_equities))
        equity_distribution["max"] = float(max(final_equities))
        equity_distribution["mean"] = float(np.mean(final_equities))

        # Build histogram bins for charting (20 bins)
        hist_counts, bin_edges = np.histogram(final_equities, bins=20)
        equity_distribution["histogram"] = {
            "counts": hist_counts.tolist(),
            "bin_edges": [float(b) for b in bin_edges.tolist()],
        }

        self.run.equity_distribution_json = equity_distribution
        self.run.status = "COMPLETED"
        self.run.completed_at = timezone.now()
        self.run.save(update_fields=["status", "completed_at", "equity_distribution_json"])

    def _store_metric(self, metric_name, values, lower_pct, upper_pct, worst_is_min):
        MonteCarloResult.objects.create(
            monte_carlo_run=self.run,
            metric_name=metric_name,
            mean_value=np.mean(values),
            median_value=np.median(values),
            std_dev=np.std(values),
            percentile_5=np.percentile(values, lower_pct),
            percentile_95=np.percentile(values, upper_pct),
            worst_case=min(values) if worst_is_min else max(values),
            best_case=max(values) if worst_is_min else min(values),
        )
