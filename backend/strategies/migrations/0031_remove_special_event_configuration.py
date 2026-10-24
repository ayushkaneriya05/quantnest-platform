"""Remove retired event filters from saved strategy and research configuration."""
from django.db import migrations


RETIRED_KEYS = {
    "special_event_filter", "avoid_earnings", "avoid_news", "avoid_rbi_policy",
    "custom_avoid_dates", "time_event_restrictions",
}


def remove_event_configuration(value):
    if isinstance(value, list):
        return [remove_event_configuration(item) for item in value]
    if isinstance(value, dict):
        return {key: remove_event_configuration(item) for key, item in value.items() if key not in RETIRED_KEYS}
    return value


def clean_saved_configuration(apps, schema_editor):
    alias = schema_editor.connection.alias
    for app, name, fields in (
        ("strategies", "StrategyVersion", ("config_snapshot",)),
        ("backtesting", "BacktestRun", ("config_snapshot", "diagnostics")),
        ("research", "ResearchSession", ("context",)),
        ("research", "ResearchRun", ("request", "evidence", "result")),
        ("research", "ResearchAction", ("payload",)),
        ("audit", "AuditLog", ("old_value", "new_value")),
    ):
        Model = apps.get_model(app, name)
        for record in Model.objects.using(alias).only("pk", *fields).iterator(chunk_size=500):
            updates = {}
            for field in fields:
                before = getattr(record, field)
                after = remove_event_configuration(before)
                if after != before:
                    updates[field] = after
            if updates:
                Model.objects.using(alias).filter(pk=record.pk).update(**updates)
    ContentType = apps.get_model("contenttypes", "ContentType")
    for app, model in (("marketdata", "marketevent"), ("rules_engine", "specialeventfilter")):
        ContentType.objects.using(alias).filter(app_label=app, model=model).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("strategies", "0030_remove_trade_cooldown"),
        ("marketdata", "0012_remove_market_events"),
        ("rules_engine", "0031_remove_market_events"),
        ("backtesting", "0021_backtestrun_charge_profile_snapshot"),
        ("research", "0004_conversation_contract"),
        ("audit", "0003_current_execution_flow"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]
    operations = [migrations.RunPython(clean_saved_configuration)]
