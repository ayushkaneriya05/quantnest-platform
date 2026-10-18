import hashlib
import json
from django.db import migrations, models


def retain_digest(apps, schema_editor):
    Event = apps.get_model("commercial", "ProviderEvent")
    for row in Event.objects.using(schema_editor.connection.alias).all().iterator(chunk_size=500):
        payload = json.dumps(row.payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        Event.objects.using(schema_editor.connection.alias).filter(pk=row.pk).update(payload_hash=hashlib.sha256(payload).hexdigest())


class Migration(migrations.Migration):
    dependencies = [("commercial", "0006_financialreview_operatingcost")]
    operations = [
        migrations.AddField(model_name="providerevent", name="payload_hash", field=models.CharField(max_length=64, default=""), preserve_default=False),
        migrations.RunPython(retain_digest, migrations.RunPython.noop),
    ]
