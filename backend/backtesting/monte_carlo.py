import numpy as np
from django.db import transaction
from django.utils import timezone

from common.enums import BacktestStatus
from .models import BacktestTrade, MonteCarloResult, MonteCarloRun


class MonteCarloSimulator:
    """
    Bootstraps recorded net trade P&Ls with replacement to estimate outcome distributions.
    Computes 7 metrics: Terminal Capital, Total Return, Max Drawdown,
    Win Rate, Sharpe Ratio, Profit Factor, and Expectancy.
    Also generates equity distribution data for histogram rendering.
    """

    CHUNK_SIZE = 128

    def __init__(self, mc_run_id):
        self.run = MonteCarloRun.objects.select_related("backtest_run").get(id=mc_run_id)
        self.backtest = self.run.backtest_run

    def run_simulation(self):
        pnl_array = np.asarray(
            list(BacktestTrade.objects.filter(run=self.backtest).values_list("net_pnl", flat=True)),
            dtype=float,
        )
        if not pnl_array.size:
            self.run.status = BacktestStatus.FAILED
            self.run.error_message = "The selected backtest has no trades to simulate."
            self.run.completed_at = timezone.now()
            self.run.save(update_fields=["status", "error_message", "completed_at"])
            return

        if not np.isfinite(pnl_array).all():
            raise ValueError("Backtest contains non-finite trade P&L values.")

        initial_capital = float(self.backtest.initial_capital)
        if not np.isfinite(initial_capital) or initial_capital <= 0:
            raise ValueError("Backtest initial capital must be greater than zero.")

        iterations = int(self.run.num_simulations)
        if not 100 <= iterations <= 10000:
            raise ValueError("Simulation count must be between 100 and 10,000.")

        confidence_level = float(self.run.confidence_level)
        if not 0.90 <= confidence_level <= 0.99:
            raise ValueError("Confidence level must be between 90% and 99%.")

        self.run.status = BacktestStatus.RUNNING
        self.run.error_message = ""
        self.run.save(update_fields=["status", "error_message"])
        lower_pct = (1 - confidence_level) / 2 * 100
        upper_pct = 100 - lower_pct

        n_trades = len(pnl_array)
        rng = np.random.default_rng(int(self.run.pk))
        metric_chunks = {name: [] for name in (
            "Terminal Capital", "Total Return", "Max Drawdown", "Win Rate",
            "Per-Trade Sharpe Ratio", "Profit Factor", "Expectancy",
        )}
        final_equities = []
        for offset in range(0, iterations, self.CHUNK_SIZE):
            size = min(self.CHUNK_SIZE, iterations - offset)
            samples = rng.choice(pnl_array, size=(size, n_trades), replace=True)
            equities = initial_capital + np.cumsum(samples, axis=1)
            terminal = equities[:, -1]
            final_equities.extend(terminal.tolist())
            running_max = np.maximum.accumulate(equities, axis=1)
            running_max = np.maximum(running_max, initial_capital)
            drawdowns = np.divide(running_max - equities, running_max, out=np.zeros_like(equities), where=running_max > 0) * 100
            wins = np.sum(samples > 0, axis=1)
            profits = np.sum(np.where(samples > 0, samples, 0), axis=1)
            losses = np.sum(np.where(samples < 0, np.abs(samples), 0), axis=1)
            factors = np.divide(profits, losses, out=np.full(size, np.nan), where=losses > 0)
            previous_equities = np.hstack([np.full((size, 1), initial_capital), equities[:, :-1]])
            trade_returns = np.divide(samples, previous_equities, out=np.zeros_like(samples), where=previous_equities > 0)
            deviations = np.std(trade_returns, axis=1)
            sharpes = np.divide(trade_returns.mean(axis=1), deviations, out=np.full(size, np.nan), where=deviations > 0)
            sharpes[~np.all(previous_equities > 0, axis=1)] = np.nan
            metric_chunks["Terminal Capital"].append(terminal)
            metric_chunks["Total Return"].append((terminal - initial_capital) / initial_capital * 100 if initial_capital else np.zeros(size))
            metric_chunks["Max Drawdown"].append(np.max(drawdowns, axis=1))
            metric_chunks["Win Rate"].append(wins / n_trades * 100)
            metric_chunks["Per-Trade Sharpe Ratio"].append(sharpes)
            metric_chunks["Profit Factor"].append(factors)
            metric_chunks["Expectancy"].append(samples.mean(axis=1))

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

        with transaction.atomic():
            self.run.results.all().delete()
            for metric_name, chunks in metric_chunks.items():
                self._store_metric(
                    metric_name,
                    np.concatenate(chunks),
                    lower_pct,
                    upper_pct,
                    worst_is_min=metric_name != "Max Drawdown",
                )

            self.run.equity_distribution_json = equity_distribution
            self.run.status = BacktestStatus.COMPLETED
            self.run.error_message = ""
            self.run.completed_at = timezone.now()
            self.run.save(update_fields=["status", "error_message", "completed_at", "equity_distribution_json"])

    def _store_metric(self, metric_name, values, lower_pct, upper_pct, worst_is_min):
        finite_values = np.asarray(values, dtype=float)
        finite_values = finite_values[np.isfinite(finite_values)]
        summary = {
            "valid_simulations": int(finite_values.size),
            "mean_value": float(np.mean(finite_values)) if finite_values.size else None,
            "median_value": float(np.median(finite_values)) if finite_values.size else None,
            "std_dev": float(np.std(finite_values)) if finite_values.size else None,
            "lower_outcome_bound": float(np.percentile(finite_values, lower_pct)) if finite_values.size else None,
            "upper_outcome_bound": float(np.percentile(finite_values, upper_pct)) if finite_values.size else None,
            "worst_case": float(np.min(finite_values) if worst_is_min else np.max(finite_values)) if finite_values.size else None,
            "best_case": float(np.max(finite_values) if worst_is_min else np.min(finite_values)) if finite_values.size else None,
        }
        MonteCarloResult.objects.create(
            monte_carlo_run=self.run,
            metric_name=metric_name,
            **summary,
        )
