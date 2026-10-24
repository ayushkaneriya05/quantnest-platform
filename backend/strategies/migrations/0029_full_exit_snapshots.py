"""Normalize saved configurations to sizing plus full-position exits."""
from django.db import migrations


def clean_configuration(value):
    if isinstance(value, list):
        return [clean_configuration(item) for item in value]
    if not isinstance(value, dict):
        return value
    group = "rule_type" in value and "rules" in value
    return {key: clean_configuration(item) for key, item in value.items()
            if key != "auto_disable_rules" and not key.startswith("auto_disable_")
            and not (group and key in {"action", "action_params"})}


def remove_retired_configuration(apps, schema_editor):
    alias = schema_editor.connection.alias
    for app, name, fields in (
        ("strategies", "StrategyVersion", ("config_snapshot",)),
        ("backtesting", "BacktestRun", ("config_snapshot", "diagnostics")),
        ("research", "ResearchRun", ("result",)),
        ("research", "ResearchAction", ("payload",)),
    ):
        Model = apps.get_model(app, name)
        for record in Model.objects.using(alias).only("pk", *fields).iterator(chunk_size=500):
            updates = {}
            for field in fields:
                before = getattr(record, field)
                after = clean_configuration(before)
                if after != before:
                    updates[field] = after
            if updates:
                Model.objects.using(alias).filter(pk=record.pk).update(**updates)
    Outbox = apps.get_model("common", "RuntimeOutbox")
    Outbox.objects.using(alias).filter(topic="risk").delete()
    Outbox.objects.using(alias).filter(topic="cache", payload__method="update_risk_metrics").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("strategies", "0028_alter_entryorderconfig_order_type"),
        ("rules_engine", "0030_full_exit_strategy_rules"),
        ("paper_trading", "0020_full_exit_sessions"),
        ("live_trading", "0030_remove_auto_disable_state"),
        ("backtesting", "0021_backtestrun_charge_profile_snapshot"),
        ("research", "0004_conversation_contract"),
        ("common", "0016_exchangeconfig_session_breaks_and_more"),
    ]
    operations = [migrations.RunPython(remove_retired_configuration)]
