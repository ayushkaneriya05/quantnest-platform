import uuid
from django.db import migrations, models


def populate_request_ids(apps, schema_editor):
    LiveOrder = apps.get_model("live_trading", "LiveOrder")
    database = schema_editor.connection.alias
    for order in LiveOrder.objects.using(database).filter(request_id__isnull=True).iterator(chunk_size=500):
        order.request_id = uuid.uuid4()
        order.save(using=database, update_fields=["request_id"])


class Migration(migrations.Migration):
    dependencies = [("live_trading", "0020_liveorder_reason")]
    operations = [
        migrations.AddField(
            model_name="liveorder",
            name="request_id",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(populate_request_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="liveorder",
            name="request_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
