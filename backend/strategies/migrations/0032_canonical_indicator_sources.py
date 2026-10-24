"""Canonicalize old source names once; LTP rules deliberately remain live-tick rules."""
from django.db import migrations


PRICE_SOURCES = {'open', 'high', 'low', 'close', 'volume', 'hl2', 'hlc3', 'ohlc4'}


def canonical(value):
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: item.upper() if key == 'source' and isinstance(item, str) and item in PRICE_SOURCES
                else canonical(item) for key, item in value.items()}
    return value


def normalize_sources(apps, schema_editor):
    alias = schema_editor.connection.alias
    # Reports and audit evidence retain their historical inputs. Editable rules
    # and deployable saved versions use the same canonical builder schema.
    for app, model, fields in (
        ('rules_engine', 'Rule', ('operand_a_params', 'operand_b_params')),
        ('strategies', 'StrategyVersion', ('config_snapshot',)),
    ):
        records = apps.get_model(app, model).objects.using(alias)
        for record in records.only('pk', *fields).iterator(chunk_size=500):
            changes = {field: canonical(getattr(record, field)) for field in fields
                       if canonical(getattr(record, field)) != getattr(record, field)}
            if changes:
                records.filter(pk=record.pk).update(**changes)


class Migration(migrations.Migration):
    dependencies = [
        ('strategies', '0031_remove_special_event_configuration'),
        ('rules_engine', '0031_remove_market_events'),
    ]
    operations = [migrations.RunPython(normalize_sources, migrations.RunPython.noop)]
