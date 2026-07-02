from collections import defaultdict

import numpy as np
import pandas as pd

from .models import BacktestRun


class BacktestAnalytics:
    def __init__(self, run_id):
        self.run = BacktestRun.objects.prefetch_related("trades", "equity_curve").get(id=run_id)
        self.trades = list(self.run.trades.select_related("instrument").order_by("entry_time"))
        self.equity_points = list(self.run.equity_curve.order_by("timestamp"))

    def monthly_returns(self):
        if not self.equity_points:
            return {}
        df = pd.DataFrame(
            [{"timestamp": point.timestamp, "equity": float(point.equity_value)} for point in self.equity_points]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        monthly = df["equity"].resample("ME").last().pct_change().fillna(0) * 100
        return {idx.strftime("%Y-%m"): round(value, 4) for idx, value in monthly.items()}

    def rolling_metrics(self, windows=(30, 60, 90)):
        if not self.trades:
            return {}
        df = pd.DataFrame(
            [{"exit_time": trade.exit_time or trade.entry_time, "net_pnl": float(trade.net_pnl)} for trade in self.trades]
        )
        df["exit_time"] = pd.to_datetime(df["exit_time"])
        df = df.set_index("exit_time").sort_index()
        results = {}
        for window in windows:
            pnl = df["net_pnl"].rolling(window=window, min_periods=1)
            rolling_win_rate = (
                df["net_pnl"].gt(0).rolling(window=window, min_periods=1).mean().fillna(0) * 100
            )
            rolling_pf = pnl.sum() / abs(df["net_pnl"].clip(upper=0).rolling(window=window, min_periods=1).sum()).replace(0, np.nan)
            results[str(window)] = [
                {
                    "timestamp": index.isoformat(),
                    "sharpe": float((series.mean() / series.std()) * np.sqrt(252)) if len(series := df["net_pnl"].iloc[max(0, i - window + 1): i + 1]) > 1 and series.std() else 0,
                    "win_rate": float(rolling_win_rate.iloc[i]),
                    "profit_factor": float(rolling_pf.iloc[i]) if pd.notna(rolling_pf.iloc[i]) else 0,
                }
                for i, index in enumerate(df.index)
            ]
        return results

    def trade_distribution(self):
        by_hour = defaultdict(int)
        holding_times = []
        pnl_values = []
        instrument_breakdown = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0})
        for trade in self.trades:
            pnl = float(trade.net_pnl)
            holding_times.append(int(trade.holding_duration_minutes or 0))
            pnl_values.append(pnl)
            by_hour[trade.entry_time.hour] += 1
            symbol = trade.instrument.symbol if trade.instrument else "Unknown"
            instrument_breakdown[symbol]["trades"] += 1
            instrument_breakdown[symbol]["pnl"] += pnl
            instrument_breakdown[symbol]["wins"] += 1 if pnl > 0 else 0
        return {
            "pnl_histogram": pnl_values,
            "holding_times": holding_times,
            "entry_hour_heatmap": dict(sorted(by_hour.items())),
            "instrument_breakdown": {
                symbol: {
                    **data,
                    "win_rate": (data["wins"] / data["trades"]) * 100 if data["trades"] else 0,
                }
                for symbol, data in instrument_breakdown.items()
            },
        }

    def drawdown_periods(self):
        if not self.equity_points:
            return []
        periods = []
        current = None
        for point in self.equity_points:
            drawdown = float(point.drawdown_pct)
            if drawdown > 0 and current is None:
                current = {"start": point.timestamp, "max_drawdown": drawdown, "end": None}
            elif drawdown > 0 and current is not None:
                current["max_drawdown"] = max(current["max_drawdown"], drawdown)
            elif drawdown <= 0 and current is not None:
                current["end"] = point.timestamp
                periods.append(current)
                current = None
        if current is not None:
            periods.append(current)
        return [
            {
                "start": period["start"].isoformat(),
                "end": period["end"].isoformat() if period["end"] else None,
                "max_drawdown": period["max_drawdown"],
            }
            for period in periods
        ]

    def mae_mfe_analysis(self):
        if not self.trades:
            return {"avg_mae": 0, "avg_mfe": 0, "efficiency": 0, "points": []}
        maes = np.array([float(trade.mae or 0) for trade in self.trades], dtype=float)
        mfes = np.array([float(trade.mfe or 0) for trade in self.trades], dtype=float)
        pnls = np.array([float(trade.net_pnl or 0) for trade in self.trades], dtype=float)
        capture = np.divide(pnls, mfes, out=np.zeros_like(pnls), where=mfes != 0)
        return {
            "avg_mae": float(maes.mean()) if len(maes) else 0,
            "avg_mfe": float(mfes.mean()) if len(mfes) else 0,
            "efficiency": float(capture.mean()) if len(capture) else 0,
            "points": [
                {
                    "instrument": trade.instrument.symbol if trade.instrument else "Unknown",
                    "mae": float(trade.mae or 0),
                    "mfe": float(trade.mfe or 0),
                    "pnl": float(trade.net_pnl or 0),
                }
                for trade in self.trades
            ],
        }

    def full_report(self):
        return {
            "monthly_returns": self.monthly_returns(),
            "rolling_metrics": self.rolling_metrics(),
            "trade_distribution": self.trade_distribution(),
            "drawdown_periods": self.drawdown_periods(),
            "mae_mfe_analysis": self.mae_mfe_analysis(),
        }
