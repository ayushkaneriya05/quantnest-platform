"""Drop the constant routing marker from saved configuration documents."""
from django.db import migrations


DOCUMENT_FIELDS = (
    ('strategies', 'Strategy', ('definition',)),
    ('strategies', 'StrategyVersion', ('config_snapshot',)),
    ('backtesting', 'BacktestRun', ('config_snapshot',)),
    ('research', 'ResearchSession', ('context',)),
    ('research', 'ResearchRun', ('request', 'evidence', 'result')),
    ('research', 'ResearchAction', ('payload',)),
    ('research', 'ResearchEvidenceRow', ('payload',)),
    ('audit', 'AuditLog', ('old_value', 'new_value')),
)


def remove_marker(value):
    """Preserve every other value, including ownership and financial records."""
    if isinstance(value, list):
        return [remove_marker(item) for item in value]
    if not isinstance(value, dict):
        return value
    if 'route_type' in value and value['route_type'] != 'DIRECT':
        raise ValueError('A saved configuration has an unexpected route type; review it before migrating.')
    return {key: remove_marker(item) for key, item in value.items() if key != 'route_type'}


def remove_constant_route_type(apps, schema_editor):
    alias = schema_editor.connection.alias
    for app, name, fields in DOCUMENT_FIELDS:
        model = apps.get_model(app, name)
        for row in model.objects.using(alias).only('pk', *fields).iterator(chunk_size=200):
            updates = {}
            for field in fields:
                original = getattr(row, field)
                cleaned = remove_marker(original)
                if cleaned != original:
                    updates[field] = cleaned
            if updates:
                model.objects.using(alias).filter(pk=row.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ('strategies', '0001_squashed_0034_canonical_strategy_documents'),
        ('backtesting', '0022_backtesttrade_leg_id_backtesttrade_route_id'),
        ('research', '0007_extract_evidence_rows'),
        ('audit', '0003_current_execution_flow'),
    ]

    operations = [migrations.RunPython(remove_constant_route_type, migrations.RunPython.noop)]
