"""Retire duplicate cache work without touching financial or runtime records."""
from django.db import migrations


def retire_projections(apps, schema_editor):
    Outbox = apps.get_model("common", "RuntimeOutbox")
    Outbox.objects.using(schema_editor.connection.alias).filter(
        topic="cache", payload__method__in=[
            "update_order", "update_position", "remove_order", "remove_position",
        ],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("common", "0009_seed_execution_assignments")]
    operations = [migrations.RunPython(retire_projections, migrations.RunPython.noop)]
