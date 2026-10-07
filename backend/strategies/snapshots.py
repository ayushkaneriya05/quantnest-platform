"""Complete, deterministic comparisons of saved strategy configurations."""
import json
from collections import Counter

IGNORED_FIELDS = {"id", "user", "user_id", "strategy", "rule_group", "watchlist_instrument", "created_at", "updated_at", "instrument_symbol", "instrument_name", "target_instrument_symbol", "target_underlying_symbol"}
SECTIONS = {
    "rule_groups": "Trading rules", "watchlist_instruments": "Instruments and routes",
    "position_sizing_rule": "Position sizing", "auto_disable_rules": "Auto-disable rules",
    "time_rule": "Trading schedule", "special_event_filter": "Event restrictions",
    "entry_order_config": "Entry settings", "exit_order_config": "Exit settings",
}
LABELS = {
    "operand_a_type": "Left operand", "operand_b_type": "Right operand",
    "operand_a_params": "Left operand parameters", "operand_b_params": "Right operand parameters",
    "operand_a_timeframe": "Left operand timeframe", "operand_b_timeframe": "Right operand timeframe",
    "comparison": "Comparison", "is_active": "Enabled", "logical_operator": "Combine conditions",
    "rule_groups": "Groups", "rules": "Conditions", "execution_routes": "Execution routes", "instrument_id": "Instrument",
}


def label(key):
    return LABELS.get(key, key.replace("_", " ").capitalize())


def snapshot_changes(previous, current):
    """Compare every configuration field; parameter changes are individual rows."""
    if previous is None:
        return []
    changes = []
    missing = object()

    def identity(item):
        if not isinstance(item, dict):
            return json.dumps(item, sort_keys=True)
        if "instrument_id" in item:
            return ("instrument", item["instrument_id"])
        if item.get("name"):
            return ("named", item.get("rule_type"), item["name"])
        return json.dumps({key: value for key, value in item.items() if key not in IGNORED_FIELDS}, sort_keys=True)

    def item_name(item, index, path):
        name = (item.get("name") or item.get("instrument_symbol")) if isinstance(item, dict) else None
        label = {"Conditions": "Condition", "Execution routes": "Route", "Groups": "Group", "Auto disable rules": "Rule"}.get(path[-1], "Item")
        return name or f"{label} {index + 1}"

    def visit(old, new, path, section):
        if old is missing or new is missing:
            changes.append({"section": section, "path": path, "label": " / ".join(path),
                            "kind": "added" if old is missing else "removed",
                            "before": None if old is missing else old, "after": None if new is missing else new})
        elif isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(set(old) | set(new)):
                if key in IGNORED_FIELDS:
                    continue
                visit(old.get(key, missing), new.get(key, missing), path + [label(key)], section)
                if key == "instrument_id" and old.get(key) != new.get(key) and changes:
                    changes[-1]["before"] = old.get("instrument_symbol", f"Instrument #{old.get(key)}")
                    changes[-1]["after"] = new.get("instrument_symbol", f"Instrument #{new.get(key)}")
        elif isinstance(old, list) and isinstance(new, list):
            if not all(isinstance(item, dict) for item in old + new):
                if old != new:
                    changes.append({"section": section, "path": path, "label": " / ".join(path),
                                    "kind": "changed", "before": old, "after": new})
                return
            old_keys, new_keys = [identity(item) for item in old], [identity(item) for item in new]
            old_counts, new_counts = Counter(old_keys), Counter(new_keys)
            matches = {index: old_keys.index(key) for index, key in enumerate(new_keys)
                       if old_counts[key] == new_counts[key] == 1}
            unmatched_old = [index for index in range(len(old)) if index not in matches.values()]
            unmatched_new = [index for index in range(len(new)) if index not in matches]
            # Preserve field-level edits for modified/renamed items. Unchanged
            # items are matched first so inserting a condition does not rewrite
            # the history of every condition below it.
            if len(unmatched_old) == len(unmatched_new):
                matches.update(zip(unmatched_new, unmatched_old))
                unmatched_old = []
            for index, item in enumerate(new):
                before = old[matches[index]] if index in matches else missing
                visit(before, item, path + [item_name(item, index, path)], section)
            for index in unmatched_old:
                visit(old[index], missing, path + [item_name(old[index], index, path)], section)
            old_order = [key for key in old_keys if key in new_keys]
            new_order = [key for key in new_keys if key in old_keys]
            if old_order != new_order:
                changes.append({"section": section, "path": path + ["Order"], "label": " / ".join(path + ["Order"]),
                                "kind": "changed", "before": [item_name(item, index, path) for index, item in enumerate(old)],
                                "after": [item_name(item, index, path) for index, item in enumerate(new)]})
        elif type(old) is not type(new) or old != new:
            changes.append({"section": section, "path": path, "label": " / ".join(path),
                            "kind": "changed", "before": old, "after": new})

    for key in sorted(set(previous) | set(current)):
        if key in IGNORED_FIELDS:
            continue
        section = SECTIONS.get(key, "Strategy details")
        visit(previous.get(key, missing), current.get(key, missing), [label(key)], section)
    return changes


def public_configuration(snapshot):
    """Explicit allowlist: sharing exposes rules, never account or execution data."""
    fields = {"name", "description", "strategy_type", "market_type", "exchange", "instrument_type", "tags", *SECTIONS}
    return {key: snapshot[key] for key in fields if key in snapshot}
