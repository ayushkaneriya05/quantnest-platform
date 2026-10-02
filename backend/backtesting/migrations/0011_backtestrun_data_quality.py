from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backtesting", "0010_remove_backtest_risk_profile_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="backtestrun",
            name="data_quality",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
