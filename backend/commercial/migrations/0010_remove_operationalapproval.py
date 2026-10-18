from django.db import migrations


def preserve_maintenance(apps, schema_editor):
    database = schema_editor.connection.alias
    Approval = apps.get_model("commercial", "OperationalApproval")
    MaintenanceState = apps.get_model("common", "MaintenanceState")
    enabled = Approval.objects.using(database).filter(purpose="maintenance", state="active").exists()
    row, _ = MaintenanceState.objects.using(database).get_or_create(pk=1, defaults={"enabled": enabled})
    if enabled and not row.enabled:
        MaintenanceState.objects.using(database).filter(pk=1).update(enabled=True)


def restore_maintenance(apps, schema_editor):
    database = schema_editor.connection.alias
    Approval = apps.get_model("commercial", "OperationalApproval")
    MaintenanceState = apps.get_model("common", "MaintenanceState")
    enabled = MaintenanceState.objects.using(database).filter(pk=1, enabled=True).exists()
    Approval.objects.using(database).update_or_create(purpose="maintenance",
        defaults={"state": "active" if enabled else "inactive"})


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0011_maintenancestate"),
        ("commercial", "0009_payment_recovery"),
    ]

    operations = [
        migrations.RunPython(preserve_maintenance, restore_maintenance),
        migrations.DeleteModel(name="OperationalApproval"),
    ]
