from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backtesting", "0013_alter_backtesttrade_mae_alter_backtesttrade_mfe"),
    ]

    operations = [
        migrations.AddField(
            model_name="backtestmetrics",
            name="instrument_breakdown_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
