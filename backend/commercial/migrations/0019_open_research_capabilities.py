"""Publish expanded capabilities; purchased and previous published terms remain immutable."""
from copy import deepcopy
from django.db import migrations
from django.utils import timezone


def publish(apps, schema_editor):
    Catalog = apps.get_model('commercial', 'CatalogRevision')
    Mapping = apps.get_model('commercial', 'PriceMapping')
    database = schema_editor.connection.alias
    previous = Catalog.objects.using(database).get(is_active=True)
    specification = deepcopy(previous.specification)
    specification['revision'] = '2026-11-research-open-1'
    for plan in specification['plans'].values():
        plan['limits'].pop('research_instruments', None)
        plan['limits'].pop('backtest_attachments', None)
    for feature in specification['features']:
        if feature['code'] == 'research':
            feature['description'] = 'Research finance and supported markets, develop strategy ideas and review evidence with period credits.'
        elif feature['code'] == 'screener':
            feature['description'] = 'Evaluate selected catalog instruments against completed-candle conditions.'
    Catalog.objects.using(database).filter(pk=previous.pk).update(is_active=False)
    current = Catalog.objects.using(database).create(revision=specification['revision'],
        specification=specification, published_at=timezone.now(), is_active=True)
    for mapping in Mapping.objects.using(database).filter(catalog=previous):
        mapping.pk = None
        mapping.catalog = current
        mapping.save(using=database)


class Migration(migrations.Migration):
    dependencies = [('commercial', '0018_private_offer')]
    operations = [migrations.RunPython(publish)]
