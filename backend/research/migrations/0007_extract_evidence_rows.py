"""Preserve saved evidence without rerunning calculations or changing usage."""
from django.db import migrations


def extract_rows(apps, schema_editor):
    Run = apps.get_model('research', 'ResearchRun')
    Row = apps.get_model('research', 'ResearchEvidenceRow')
    alias = schema_editor.connection.alias
    for run in Run.objects.using(alias).only('id', 'evidence').iterator(chunk_size=100):
        changed = False
        for item in run.evidence:
            rows = item.get('data', {}).pop('rows', None)
            if rows is None:
                continue
            Row.objects.using(alias).bulk_create([
                Row(run_id=run.pk, evidence_id=item['evidence_id'], ordinal=index,
                    instrument_id=row['instrument_id'], symbol=row['symbol'], close=row.get('close'),
                    return_20_bars_pct=row.get('return_20_bars_pct'),
                    volatility_20_bars_pct=row.get('volatility_20_bars_pct'), payload=row)
                for index, row in enumerate(rows)
            ], batch_size=250)
            item['storage_run_id'] = run.pk
            item['data']['row_count'] = len(rows)
            changed = True
        if changed:
            Run.objects.using(alias).filter(pk=run.pk).update(evidence=run.evidence)


def restore_rows(apps, schema_editor):
    Run = apps.get_model('research', 'ResearchRun')
    Row = apps.get_model('research', 'ResearchEvidenceRow')
    alias = schema_editor.connection.alias
    for run in Run.objects.using(alias).only('id', 'evidence').iterator(chunk_size=100):
        changed = False
        for item in run.evidence:
            if item.pop('storage_run_id', None) is None:
                continue
            item['data']['rows'] = list(Row.objects.using(alias).filter(run_id=run.pk, evidence_id=item['evidence_id']).order_by('ordinal').values_list('payload', flat=True))
            item['data'].pop('row_count', None)
            changed = True
        if changed:
            Run.objects.using(alias).filter(pk=run.pk).update(evidence=run.evidence)
    Row.objects.using(alias).all().delete()


class Migration(migrations.Migration):
    dependencies = [('research', '0006_paged_evidence')]
    operations = [migrations.RunPython(extract_rows, restore_rows)]
