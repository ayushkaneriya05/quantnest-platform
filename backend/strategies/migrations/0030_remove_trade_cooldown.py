"""Remove trade cooldown from configuration and saved structured payloads."""
from django.db import migrations


def remove_cooldown(value):
    if isinstance(value, list):
        return [remove_cooldown(item) for item in value]
    if isinstance(value, dict):
        return {key: remove_cooldown(item) for key, item in value.items()
                if key not in {"cooldown_seconds", "cooldown_restrictions"}}
    return value


def clean_saved_configurations(apps, schema_editor):
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
                after = remove_cooldown(before)
                if before != after:
                    updates[field] = after
            if updates:
                Model.objects.using(alias).filter(pk=record.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [("strategies", "0029_full_exit_snapshots")]
    operations = [
        migrations.RemoveField(model_name="entryorderconfig", name="cooldown_seconds"),
        migrations.RunPython(clean_saved_configurations),
    ]
