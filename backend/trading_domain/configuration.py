"""Validated timeframe and warmup contracts, independent of market providers."""
SUPPORTED_TIMEFRAMES = ("1m", "3m", "5m", "15m", "30m", "1H", "4H", "1D", "1W")


def normalize_timeframe(value):
    value = str(value or "1m").strip()
    aliases = {"1": "1m", "3": "3m", "5": "5m", "15": "15m", "30": "30m",
               "60": "1H", "240": "4H", "D": "1D", "d": "1D", "W": "1W", "w": "1W",
               "1d": "1D", "1w": "1W", "1h": "1H", "4h": "4H"}
    result = aliases.get(value, value)
    if result not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"Unsupported timeframe '{value}'")
    return result


def timeframe_minutes(session_minutes=375):
    return {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1H": 60,
            "4H": 240, "1D": session_minutes, "1W": session_minutes * 5}


def requirements(config, session_minutes=375):
    from rules_engine.metadata import IndicatorRequirementAnalyzer
    base = normalize_timeframe((config.get("time_rule") or {}).get("candle_timeframe"))
    warmup = IndicatorRequirementAnalyzer.get_warmup_requirements(config)
    counts = {normalize_timeframe(tf): count for tf, count in warmup.items()}
    minutes = timeframe_minutes(session_minutes)
    count = max(2, max((count * minutes[tf] for tf, count in counts.items()), default=2))
    return base, frozenset({base, *counts}), count
