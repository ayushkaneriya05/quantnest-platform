from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0011_maintenancestate"),
        ("commercial", "0010_remove_operationalapproval"),
    ]

    operations = [migrations.DeleteModel(name="MaintenanceState")]
