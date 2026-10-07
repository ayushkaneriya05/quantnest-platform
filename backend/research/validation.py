"""Research uses the same serializers and parameter defaults as the builder."""
import json
from datetime import time
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.exceptions import ValidationError
from common.enums import (OperandType, OPERAND_GROUPS, RuleType, TradingDay, InstrumentType,
                          RuleGroupAction, get_operand_parameter_config)
from instruments.models import Instrument
from risk_management.serializers import PositionSizingRuleSerializer, StrategyAutoDisableSerializer
from rules_engine.models import Rule, RuleGroup
from rules_engine.serializers import (RuleSerializer, RuleGroupCreateSerializer,
                                     TimeRuleSerializer, SpecialEventFilterSerializer)
from strategies.serializers import (StrategyCreateSerializer, EntryOrderConfigSerializer,
                                    ExitOrderConfigSerializer)


def json_data(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder, allow_nan=False))


def validate_config(serializer_class, data):
    if not isinstance(data, dict):
        raise ValidationError("Configuration must be an object.")
    model = serializer_class.Meta.model
    instance = model()
    serializer = serializer_class(instance)
    allowed = set(serializer.fields) - {"id", "strategy", "rule_group"}
    unknown = set(data) - allowed
    if unknown:
        raise ValidationError(f"Unsupported fields: {', '.join(sorted(unknown))}.")
    defaults = {key: value for key, value in serializer.data.items() if key in allowed}
    serializer = serializer_class(instance, data={**defaults, **data}, partial=True)
    for field in ("strategy", "rule_group"):
        if field in serializer.fields:
            serializer.fields[field].read_only = True
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def validate_rule(data, rule_type=RuleType.ENTRY):
    if not isinstance(data, dict):
        raise ValidationError("Each rule must be an object.")
    serializer = RuleSerializer()
    unknown = set(data) - (set(serializer.fields) - {"id", "rule_group"})
    if unknown:
        raise ValidationError(f"Unsupported rule fields: {', '.join(sorted(unknown))}.")
    if not data.get("operand_a_type") or not data.get("operand_b_type") or not data.get("comparison"):
        raise ValidationError("Specify both operands and their comparison.")
    instance = Rule(rule_group=RuleGroup(rule_type=rule_type))
    serializer = RuleSerializer(instance, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    result = serializer.validated_data
    result["is_active"] = result.get("is_active", True)
    # Normalize parameters even when only an operand type is provided.
    from rules_engine.serializers import _normalize_and_validate_operand_params
    from common.enums import get_math_expression_operand_types
    for side in ("a", "b"):
        field = f"operand_{side}_params"
        operand = result[f"operand_{side}_type"]
        _validate_parameter_keys(operand, result.get(field) or {})
        result[field] = _normalize_and_validate_operand_params(
            operand, result.get(field) or {}, field,
            math_variable_types=set(get_math_expression_operand_types(rule_type)))
        if rule_type == RuleType.ENTRY and operand in OPERAND_GROUPS["Position State (Exit)"]:
            raise ValidationError("Position state operands can only be used in exit rules.")
    return result


def _validate_parameter_keys(operand, params, *, source=False):
    schema = get_operand_parameter_config(OperandType(operand))
    keys = {item["key"] for item in schema}
    if source:
        keys -= {"source", "shift"}
    elif "source" in keys:
        keys.add("source_params")
    if set(params) - keys:
        raise ValidationError(f"Unsupported {operand} parameters: {', '.join(sorted(set(params) - keys))}.")
    if params.get("source_params"):
        _validate_parameter_keys(params["source"], params["source_params"], source=True)
    if operand == OperandType.MATH_EXPRESSION:
        expression = params.get("expression")
        if not isinstance(expression, dict) or set(expression) - {"expression", "variables"}:
            raise ValidationError("Math expressions need expression text and configured variables.")
        for variable in (expression.get("variables") or {}).values():
            if set(variable) - {"type", "params", "timeframe"}:
                raise ValidationError("Unsupported math variable configuration.")
            _validate_parameter_keys(variable["type"], variable.get("params") or {})


CONFIG_SERIALIZERS = {
    "entry_order_config": EntryOrderConfigSerializer,
    "exit_order_config": ExitOrderConfigSerializer,
    "position_sizing_rule": PositionSizingRuleSerializer,
    "time_rule": TimeRuleSerializer,
    "special_event_filter": SpecialEventFilterSerializer,
}


def validate_draft(draft, instrument_ids):
    if not isinstance(draft, dict):
        raise ValidationError("Strategy draft must be an object.")
    base_fields = {"name", "description", "strategy_type", "market_type", "exchange", "instrument_type"}
    allowed = base_fields | set(CONFIG_SERIALIZERS) | {"rule_groups", "watchlist_instruments", "auto_disable_rules"}
    if set(draft) - allowed:
        raise ValidationError(f"Unsupported draft fields: {', '.join(sorted(set(draft) - allowed))}.")
    serializer = StrategyCreateSerializer(data={key: draft[key] for key in base_fields if key in draft})
    serializer.is_valid(raise_exception=True)
    result = dict(serializer.validated_data)
    if result.get("exchange") != "NSE" or result.get("instrument_type") != InstrumentType.STOCK or result.get("market_type") != "EQUITY":
        raise ValidationError("Research drafts currently support NSE equities and direct execution routes.")
    for name, config_serializer in CONFIG_SERIALIZERS.items():
        result[name] = validate_config(config_serializer, draft.get(name, {}))
    time_rule = result["time_rule"]
    days = time_rule.get("trading_days")
    if not isinstance(days, list) or not days or any(day not in TradingDay.values for day in days):
        raise ValidationError("Choose valid trading days.")
    if not time_rule.get("start_time") or not time_rule.get("end_time") or time_rule["start_time"] >= time_rule["end_time"]:
        raise ValidationError("Trading start time must precede end time.")
    windows = time_rule.get("no_trade_windows") or []
    if not isinstance(windows, list):
        raise ValidationError("No-trade windows must be a list.")
    for window in windows:
        try:
            if time.fromisoformat(window["start"]) >= time.fromisoformat(window["end"]):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ValidationError("No-trade windows need valid start and end times.")
    watchlist = draft.get("watchlist_instruments") or [{"instrument_id": value} for value in instrument_ids]
    if not isinstance(watchlist, list):
        raise ValidationError("Watchlist instruments must be a list.")
    ids = [item.get("instrument_id") for item in watchlist if isinstance(item, dict)]
    if not ids or any(not isinstance(value, int) or isinstance(value, bool) for value in ids) or len(ids) != len(watchlist) or len(set(ids)) != len(ids) or set(ids) - set(instrument_ids):
        raise ValidationError("Select unique instruments from this research universe.")
    instruments = Instrument.objects.in_bulk(ids)
    if len(instruments) != len(ids) or any(item.exchange != "NSE" or item.instrument_type != InstrumentType.STOCK or not item.is_active for item in instruments.values()):
        raise ValidationError("The selected instruments must be active NSE equities.")
    for item in watchlist:
        if set(item) - {"instrument_id", "execution_routes"}:
            raise ValidationError("Unsupported watchlist fields.")
        routes = item.get("execution_routes", [{"route_type": "DIRECT"}])
        if routes != [{"route_type": "DIRECT"}]:
            raise ValidationError("Each instrument must have one DIRECT route.")
    result["watchlist_instruments"] = [{"instrument_id": value, "execution_routes": [{"route_type": "DIRECT"}]} for value in ids]
    groups = draft.get("rule_groups", [])
    if not isinstance(groups, list) or not 1 <= len(groups) <= 12:
        raise ValidationError("Provide between 1 and 12 rule groups.")
    result["rule_groups"] = []
    for group in groups:
        if not isinstance(group, dict) or set(group) - {"name", "rule_type", "logical_operator", "priority", "action", "action_params", "rules"}:
            raise ValidationError("Unsupported rule group fields.")
        config = validate_config(RuleGroupCreateSerializer, {key: value for key, value in group.items() if key != "rules"})
        rules = group.get("rules", [])
        if not isinstance(rules, list) or not 1 <= len(rules) <= 12:
            raise ValidationError("Each group needs between 1 and 12 rules.")
        config["rules"] = [validate_rule(rule, config["rule_type"]) for rule in rules]
        if any(not rule.get("is_active", True) for rule in config["rules"]):
            raise ValidationError("Draft rules must be active; disable them later in the builder.")
        action = config.get("action")
        if action == RuleGroupAction.PARTIAL_EXIT:
            percentage = (config.get("action_params") or {}).get("exit_pct")
            if not isinstance(percentage, (float, int)) or not 0 < percentage < 100:
                raise ValidationError("Partial exits require exit_pct between 0 and 100.")
        result["rule_groups"].append(config)
    if not any(group["rule_type"] == RuleType.ENTRY for group in result["rule_groups"]):
        raise ValidationError("A strategy needs an entry group.")
    if not any(group["rule_type"] != RuleType.ENTRY for group in result["rule_groups"]):
        raise ValidationError("Add an exit, stop-loss, or target group.")
    auto_disable = draft.get("auto_disable_rules", [])
    if not isinstance(auto_disable, list) or len(auto_disable) > 12:
        raise ValidationError("Auto-disable rules must be a list with at most 12 rules.")
    result["auto_disable_rules"] = [validate_config(StrategyAutoDisableSerializer, item) for item in auto_disable]
    return json_data(result)
