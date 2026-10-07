"""Pure closed-trade metrics shared by recovery, execution, and backtests."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


METRICS_VERSION = 1
RECENT_TRADE_LIMIT = 256


def metrics_complete(stats):
    """Partial cache writes are not sufficient to evaluate risk restrictions."""
    required = {"risk_capital", "risk_day", "risk_week", "risk_month", "daily_pnl", "weekly_pnl",
                "monthly_pnl", "daily_trades", "total_closed_trades", "winning_trades", "losing_trades",
                "win_rate", "consecutive_losses", "consecutive_wins", "realized_pnl", "realized_peak", "drawdown"}
    return bool(stats and stats.get("risk_metrics_version") == METRICS_VERSION and required <= stats.keys())


def empty_metrics(capital, timestamp, timezone_name="Asia/Kolkata"):
    capital = float(capital)
    return normalize_periods({"risk_metrics_version": METRICS_VERSION, "risk_capital": capital,
                              "daily_pnl": 0.0, "weekly_pnl": 0.0, "monthly_pnl": 0.0,
                              "daily_trades": 0, "total_closed_trades": 0, "closed_trades": 0,
                              "winning_trades": 0, "losing_trades": 0, "win_rate": 0.0,
                              "consecutive_losses": 0, "consecutive_wins": 0,
                              "realized_pnl": 0.0, "realized_peak": capital, "drawdown": 0.0,
                              "last_entry_time": None, "last_exit_time": None, "recent_trade_ids": [],
                              "last_close_trade_id": None},
                             timestamp, timezone_name)


def normalize_periods(stats, timestamp, timezone_name="Asia/Kolkata"):
    result = dict(stats or {})
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=ZoneInfo(timezone_name))
    local = timestamp.astimezone(ZoneInfo(timezone_name))
    periods = {"day": local.date().isoformat(), "week": (local.date() - timedelta(days=local.weekday())).isoformat(),
               "month": local.strftime("%Y-%m")}
    previous_time = result.get("last_exit_time")
    if isinstance(previous_time, str):
        previous_time = datetime.fromisoformat(previous_time)
    if previous_time and previous_time.tzinfo is None:
        previous_time = previous_time.replace(tzinfo=ZoneInfo(timezone_name))
    previous = previous_time.astimezone(ZoneInfo(timezone_name)) if previous_time else local
    inferred = {"day": previous.date().isoformat(), "week": (previous.date() - timedelta(days=previous.weekday())).isoformat(),
                "month": previous.strftime("%Y-%m")}
    for period, field in (("day", "daily_pnl"), ("week", "weekly_pnl"), ("month", "monthly_pnl")):
        if result.get("risk_" + period, inferred[period]) != periods[period]:
            result[field] = 0.0
            if period == "day":
                result["daily_trades"] = 0
        result["risk_" + period] = periods[period]
    return result


def record_close(stats, pnl, timestamp, capital, timezone_name="Asia/Kolkata"):
    result = normalize_periods(stats, timestamp, timezone_name)
    pnl, capital = float(pnl), float(capital)
    result["risk_capital"] = capital
    for key in ("daily_pnl", "weekly_pnl", "monthly_pnl", "realized_pnl"):
        result[key] = float(result.get(key, 0) or 0) + pnl
    result["daily_trades"] = int(result.get("daily_trades", 0) or 0) + 1
    result["total_closed_trades"] = int(result.get("total_closed_trades", 0) or 0) + 1
    result["closed_trades"] = result["total_closed_trades"]
    result["winning_trades"] = int(result.get("winning_trades", 0) or 0) + int(pnl > 0)
    result["losing_trades"] = int(result.get("losing_trades", 0) or 0) + int(pnl < 0)
    result["win_rate"] = result["winning_trades"] / result["total_closed_trades"] * 100
    result["consecutive_losses"] = int(result.get("consecutive_losses", 0) or 0) + 1 if pnl < 0 else 0
    result["consecutive_wins"] = int(result.get("consecutive_wins", 0) or 0) + 1 if pnl > 0 else 0
    equity = capital + result["realized_pnl"]
    result["realized_peak"] = max(float(result.get("realized_peak", capital) or capital), equity)
    peak = result["realized_peak"]
    result["drawdown"] = max((peak - equity) / peak * 100, 0) if peak > 0 else 0
    result["last_exit_time"] = timestamp.isoformat()
    return result
