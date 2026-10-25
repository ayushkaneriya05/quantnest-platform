"""Start token credits in a new catalog; preserve published terms and old buckets."""
from copy import deepcopy
from django.db import migrations
from django.utils import timezone


def publish(apps, schema_editor):
    Catalog = apps.get_model("commercial", "CatalogRevision")
    Run = apps.get_model("research", "ResearchRun")
    if Run.objects.filter(status__in=["PENDING", "RUNNING"]).exists():
        raise RuntimeError("Finish or cancel active research before deploying token credits.")
    if apps.get_model("commercial", "Subscription").objects.exists():
        raise RuntimeError("Review purchased subscription terms before the token-credit cutover.")
    previous = Catalog.objects.get(is_active=True)
    specification = deepcopy(previous.specification)
    revision = "2026-10-research-credits-1"
    specification["revision"] = revision
    for code, tokens in (("explore", 150000), ("build", 500000), ("pro", 1500000)):
        limits = specification["plans"][code]["limits"]
        limits.pop("research_turns", None)
        limits["research_tokens"] = tokens
    Catalog.objects.filter(pk=previous.pk).update(is_active=False)
    current = Catalog.objects.create(revision=revision, specification=specification,
                                     published_at=timezone.now(), is_active=True)
    Mapping = apps.get_model("commercial", "PriceMapping")
    for mapping in Mapping.objects.filter(catalog=previous):
        mapping.pk = None
        mapping.catalog = current
        mapping.save()


class Migration(migrations.Migration):
    dependencies = [("commercial", "0015_remove_creationreceipt_providerevent_commercialaudit"),
                    ("research", "0004_conversation_contract")]
    operations = [migrations.RunPython(publish)]
