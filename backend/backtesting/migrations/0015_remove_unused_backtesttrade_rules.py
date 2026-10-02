from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("backtesting", "0014_backtestmetrics_instrument_breakdown"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="backtesttrade",
            name="entry_rule",
        ),
        migrations.RemoveField(
            model_name="backtesttrade",
            name="exit_rule",
        ),
    ]
