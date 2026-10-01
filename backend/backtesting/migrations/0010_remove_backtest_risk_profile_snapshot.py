from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("backtesting", "0009_remove_backtestrun_fill_model"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="backtestrun",
            name="risk_profile_snapshot",
        ),
    ]
