from django.db import migrations


def remove_analytics_records(apps, schema_editor):
    database = schema_editor.connection.alias
    Consent = apps.get_model("customer_support", "Consent")
    DeliveryJob = apps.get_model("commercial", "DeliveryJob")
    Consent.objects.using(database).filter(purpose="analytics").delete()
    DeliveryJob.objects.using(database).filter(kind="analytics").delete()


class Migration(migrations.Migration):
    dependencies = [("customer_support", "0008_quotation_workflow")]

    operations = [
        migrations.RunPython(remove_analytics_records, migrations.RunPython.noop),
        migrations.DeleteModel(name="CustomerEvent"),
        migrations.DeleteModel(name="VisitorConsent"),
    ]
