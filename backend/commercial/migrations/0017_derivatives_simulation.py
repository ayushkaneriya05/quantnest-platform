"""Publish simulation availability without rewriting purchased financial terms."""
from copy import deepcopy

from django.db import migrations
from django.utils import timezone


def publish(apps, schema_editor):
    Catalog = apps.get_model("commercial", "CatalogRevision")
    Mapping = apps.get_model("commercial", "PriceMapping")
    database = schema_editor.connection.alias
    previous = Catalog.objects.using(database).get(is_active=True)
    specification = deepcopy(previous.specification)
    revision = "2026-11-derivatives-simulation-1"
    # Freeze this release's descriptors here; future seed edits must not change
    # migration history. Prices, limits and purchased snapshots stay untouched.
    markets = [
        {"code": "nse_stocks", "name": "NSE stocks", "status": "available"},
        {"code": "nse_futures", "name": "NSE futures", "status": "available"},
        {"code": "nse_options", "name": "NSE options", "status": "available"},
    ]
    specification.update(revision=revision, markets=[row["name"] for row in markets],
                         market_catalog=markets)
    for plan in specification["plans"].values():
        plan["markets"] = deepcopy(markets)
    Catalog.objects.using(database).filter(pk=previous.pk).update(is_active=False)
    current = Catalog.objects.using(database).create(
        revision=revision, specification=specification,
        published_at=timezone.now(), is_active=True,
    )
    for mapping in Mapping.objects.using(database).filter(catalog=previous):
        mapping.pk = None
        mapping.catalog = current
        mapping.save(using=database)


class Migration(migrations.Migration):
    dependencies = [("commercial", "0016_research_token_credits")]
    operations = [migrations.RunPython(publish)]
