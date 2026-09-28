from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("live_trading", "0019_dedupe_broker_orders"),
    ]

    operations = [
        migrations.AddField(
            model_name="liveorder",
            name="reason",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
