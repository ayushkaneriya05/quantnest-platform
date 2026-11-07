"""Store calculated tables once; hydrate them only for model tools or one-row previews."""
from copy import deepcopy
from .models import ResearchEvidenceRow


def hydrate_evidence(item):
    if not item.get('storage_run_id'):
        return item
    rows = ResearchEvidenceRow.objects.filter(run_id=item['storage_run_id'], evidence_id=item['evidence_id']).order_by('ordinal')
    return {**item, 'data': {**item['data'], 'rows': [row.payload for row in rows]}}


def store_evidence(run, item):
    """Caller holds the run lock. Metadata and rows commit in the same transaction."""
    if item.get('storage_run_id') == run.pk:
        return {**item, 'data': {key: value for key, value in item['data'].items() if key != 'rows'}}
    item = deepcopy(item if 'rows' in item.get('data', {}) else hydrate_evidence(item))
    rows = item.get('data', {}).pop('rows', None)
    if rows is None:
        return item
    ResearchEvidenceRow.objects.bulk_create([
        ResearchEvidenceRow(run=run, evidence_id=item['evidence_id'], ordinal=index,
            instrument_id=row['instrument_id'], symbol=row['symbol'],
            close=row.get('close'), return_20_bars_pct=row.get('return_20_bars_pct'),
            volatility_20_bars_pct=row.get('volatility_20_bars_pct'), payload=row)
        for index, row in enumerate(rows)
    ], batch_size=250)
    item['storage_run_id'] = run.pk
    item['data']['row_count'] = len(rows)
    return item
