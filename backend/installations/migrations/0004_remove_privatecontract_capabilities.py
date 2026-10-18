from django.db import migrations
from django.db.models import F


def advance_licence_schema(apps, schema_editor):
    # The new claim schema needs a newer contract revision, so refresh does not
    # compare the new token with a module-list token at the same revision.
    contract = apps.get_model("installations", "PrivateContract")
    contract.objects.using(schema_editor.connection.alias).update(revision=F("revision") + 1)


class Migration(migrations.Migration):
    dependencies = [("installations", "0003_contract_validation")]

    operations = [
        migrations.RunPython(advance_licence_schema, migrations.RunPython.noop),
        migrations.RemoveField(model_name="privatecontract", name="capabilities"),
    ]
