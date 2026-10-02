from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backtesting", "0015_remove_unused_backtesttrade_rules"),
    ]

    operations = [
        migrations.AddField(
            model_name="backtestrun",
            name="progress_message",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
