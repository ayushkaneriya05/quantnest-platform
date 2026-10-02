from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backtesting", "0016_backtestrun_progress_message"),
    ]

    operations = [
        migrations.AddField(
            model_name="montecarlorun",
            name="error_message",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="montecarloresult",
            name="valid_simulations",
            field=models.PositiveIntegerField(blank=True, default=None, null=True),
        ),
        migrations.AlterField(
            model_name="montecarlorun",
            name="equity_distribution_json",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Percentile-based equity distribution for histogram rendering.",
            ),
        ),
        migrations.RenameField(
            model_name="montecarloresult",
            old_name="percentile_5",
            new_name="lower_outcome_bound",
        ),
        migrations.RenameField(
            model_name="montecarloresult",
            old_name="percentile_95",
            new_name="upper_outcome_bound",
        ),
    ]
