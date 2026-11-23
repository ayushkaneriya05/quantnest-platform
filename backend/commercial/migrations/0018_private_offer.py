"""Restore quoted Private marketing without changing purchased public terms."""
from copy import deepcopy

from django.db import migrations
from django.utils import timezone


def publish(apps, schema_editor):
    Catalog = apps.get_model("commercial", "CatalogRevision")
    Mapping = apps.get_model("commercial", "PriceMapping")
    database = schema_editor.connection.alias
    previous = Catalog.objects.using(database).get(is_active=True)
    specification = deepcopy(previous.specification)
    revision = "2026-11-private-offer-1"
    # Freeze release data here. Future catalog edits must not change migrations.
    specification.update(revision=revision, private_offer={
        "code": "private", "name": "QuantNest Private", "pricing_type": "contact",
        "price_minor": None, "availability": "on_request", "delivery": "managed_dedicated",
        "description": "Your own QuantNest-managed workspace, including broker-connected Live strategies.",
        "execution_scopes": ["paper", "live"],
        "capacity_note": "No public-plan quotas. Server capacity, hosting, support, data and AI costs are agreed in your quotation.",
        "cta_label": "Discuss Private", "cta_url": "/contact/?type=private",
    })
    specification.pop("live", None)
    for plan in specification["plans"].values():
        plan["execution_scopes"] = ["paper"]
    for feature in specification["features"]:
        feature["included_in"] = ["explore", "build", "pro", "private"]
    for code, name, description in (
        ("brokers", "Broker Integration", "Connect your own supported broker account in QuantNest Private."),
        ("live", "Live Trading", "Run saved strategy versions through your broker in a managed Private workspace."),
    ):
        specification["features"].append({"code": code, "name": name, "documentation": f"/docs/{code}/",
                                          "description": description, "included_in": ["private"]})
    Catalog.objects.using(database).filter(pk=previous.pk).update(is_active=False)
    current = Catalog.objects.using(database).create(
        revision=revision, specification=specification, published_at=timezone.now(), is_active=True,
    )
    # Only presentation changed, so existing provider prices remain applicable.
    for mapping in Mapping.objects.using(database).filter(catalog=previous):
        mapping.pk = None
        mapping.catalog = current
        mapping.save(using=database)


class Migration(migrations.Migration):
    dependencies = [("commercial", "0017_derivatives_simulation")]
    operations = [migrations.RunPython(publish)]
