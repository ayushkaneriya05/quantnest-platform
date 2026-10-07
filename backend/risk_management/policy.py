"""Config-only auto-disable decisions. No database or cache access."""
from datetime import datetime, timedelta
from .evaluator import RiskEvaluator
from .metrics import normalize_periods


def evaluate_configuration(config, stats, capital, timestamp, release=None):
    rules = config["auto_disable_rules"]
    stats = normalize_periods(stats, timestamp, (config.get("time_rule") or {}).get("timezone", "Asia/Kolkata"))
    release = release or stats.get("auto_disable_release") or {}
    released_count = release.get("trade_count", -1)
    evaluator = RiskEvaluator(capital)
    matches = []
    for index, rule in enumerate(rules):
        result = evaluator.evaluate_auto_disable_rule(rule, stats)
        result["rule_index"] = index
        if result["triggered"] and not (index in release.get("rule_indexes", []) and stats.get("total_closed_trades", 0) <= released_count):
            matches.append(result)
    return {"matches": matches, "should_disable": bool(matches),
            "can_auto_reenable": bool(matches) and all(item["auto_reenable"] for item in matches),
            "max_cooldown_hours": max((item["cooldown_hours"] for item in matches), default=0)}


def pause_state(evaluation, timestamp):
    return {"matches": evaluation["matches"], "paused_at": timestamp.isoformat(),
            "resume_at": (timestamp + timedelta(hours=evaluation["max_cooldown_hours"])).isoformat()
            if evaluation["can_auto_reenable"] else None}


def release_state(state, stats):
    # A cooldown permits another trade; unchanged historic totals cannot instantly
    # pause the session again before a new close has been recorded.
    return {"release": {"trade_count": int(stats.get("total_closed_trades", 0) or 0),
                        "rule_indexes": [item["rule_index"] for item in state.get("matches", [])]}}


def cooldown_elapsed(state, timestamp):
    deadline = state.get("resume_at")
    return bool(deadline and datetime.fromisoformat(deadline) <= timestamp)
