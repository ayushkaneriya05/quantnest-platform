from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0010_retire_unused_order_position_projections")]

    operations = [
        migrations.CreateModel(
            name="MaintenanceState",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("enabled", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [models.CheckConstraint(condition=models.Q(id=1), name="single_maintenance_state")],
            },
        ),
    ]
