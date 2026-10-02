from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backtesting", "0011_backtestrun_data_quality"),
    ]

    operations = [
        migrations.RemoveField(model_name="backtestrun", name="brokerage_per_trade"),
        migrations.RemoveField(model_name="backtestrun", name="brokerage_pct"),
        migrations.AlterField(
            model_name="backtestmetrics", name="profit_factor",
            field=models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name="backtestmetrics", name="payoff_ratio",
            field=models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name="backtestmetrics", name="sharpe_ratio",
            field=models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name="backtestmetrics", name="sortino_ratio",
            field=models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name="backtestmetrics", name="calmar_ratio",
            field=models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name="backtestmetrics", name="recovery_factor",
            field=models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True),
        ),
        *[
            migrations.AlterField(
                model_name="montecarloresult", name=field_name,
                field=models.DecimalField(blank=True, decimal_places=6, max_digits=15, null=True),
            )
            for field_name in (
                "mean_value", "median_value", "std_dev", "percentile_5",
                "percentile_95", "worst_case", "best_case",
            )
        ],
    ]
