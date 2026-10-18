from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("commercial", "0014_remove_deliveryjob")]

    operations = [
        migrations.DeleteModel(name="CreationReceipt"),
        migrations.DeleteModel(name="ProviderEvent"),
        migrations.DeleteModel(name="CommercialAudit"),
    ]
