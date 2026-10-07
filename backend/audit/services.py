"""Small, sanitized activity records for configuration and lifecycle changes."""
from datetime import date, datetime
from decimal import Decimal
from contextvars import ContextVar
from .models import AuditLog, ActivityResource

audit_request = ContextVar("audit_request", default=None)

SAFE_FIELDS = {
    "Strategy": ("name", "status", "visibility", "strategy_type", "market_type", "exchange",
                 "instrument_type", "paper_trading_enabled", "live_trading_enabled"),
    "BrokerCredential": ("broker_name", "label", "is_active", "is_verified"),
    "PaperAccount": ("name",),
    "CapitalAllocation": ("strategy_id", "deployed_version_id", "allocation_type", "allocated_amount", "allocated_percentage"),
    "LiveStrategyAllocation": ("strategy_id", "broker_credential_id", "deployed_version_id", "allocation_type", "allocated_capital", "allocated_percentage"),
    "PaperTradingSession": ("strategy_id", "account_id", "status", "slippage_pct", "include_charges", "charge_profile_id"),
    "TradingSession": ("strategy_id", "broker_credential_id", "allocation_id", "status"),
}
CONFIG_FIELDS = ("name", "description", "strategy_type", "market_type", "exchange", "instrument_type",
                 "time_rule", "special_event_filter", "entry_order_config", "exit_order_config",
                 "position_sizing_rule", "auto_disable_rules", "watchlist_instruments", "rule_groups")


def json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


class AuditService:
    @staticmethod
    def snapshot_instance(instance):
        return json_safe({field: getattr(instance, field) for field in SAFE_FIELDS.get(type(instance).__name__, ())})

    @staticmethod
    def log_action(user, action, entity, old_value=None, new_value=None, request=None, reason="", actor_name=None):
        entity_type = type(entity).__name__
        if entity_type not in ActivityResource.values:
            raise ValueError("This resource is not supported by activity history.")
        request = request or audit_request.get()
        actor = getattr(request, "user", None)
        allowed = set(SAFE_FIELDS.get(type(entity).__name__, ()))
        if type(entity).__name__ == "Strategy":
            allowed.update(CONFIG_FIELDS)
        if type(entity).__name__ == "PaperAccount" and action == "RESET":
            allowed.add("current_balance")
        return AuditLog.objects.create(
            user=user, actor_name=actor_name or (actor.get_username() if actor and actor.is_authenticated else "System"),
            action=action, entity_type=entity_type, entity_id=str(entity.pk or ""),
            entity_name=str(getattr(entity, "name", None) or getattr(entity, "label", None) or f"{type(entity).__name__} #{entity.pk}")[:255],
            old_value=json_safe({key: value for key, value in (old_value or {}).items() if key in allowed}),
            new_value=json_safe({key: value for key, value in (new_value or {}).items() if key in allowed}), reason=reason,
            ip_address=request.META.get("REMOTE_ADDR") if request else None,
        )

    @staticmethod
    def configuration_changed(strategy, previous, current, version):
        old = {field: previous.get(field) for field in CONFIG_FIELDS}
        new = {field: current.get(field) for field in CONFIG_FIELDS}
        changed = [field for field in CONFIG_FIELDS if old[field] != new[field]]
        if changed:
            AuditService.log_action(strategy.user, "UPDATE", strategy,
                old_value={field: old[field] for field in changed}, new_value={field: new[field] for field in changed},
                reason=f"Saved configuration version {version.version_number}")
