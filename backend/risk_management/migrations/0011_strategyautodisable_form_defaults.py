import common.enums
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('risk_management', '0010_remove_positionsizingrule_max_daily_trades_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='strategyautodisable',
            name='trigger_type',
            field=models.CharField(
                choices=[
                    ('CONSECUTIVE_LOSSES', 'Consecutive Losses'),
                    ('CONSECUTIVE_WINS', 'Consecutive Wins'),
                    ('DAILY_LOSS', 'Daily Loss Threshold'),
                    ('WEEKLY_LOSS', 'Weekly Loss Threshold'),
                    ('MONTHLY_LOSS', 'Monthly Loss Threshold'),
                    ('WIN_RATE_DROP', 'Win Rate Below Threshold'),
                    ('DRAWDOWN', 'Drawdown Exceeded'),
                ],
                default=common.enums.AutoDisableTriggerType.CONSECUTIVE_LOSSES,
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='strategyautodisable',
            name='threshold_count',
            field=models.PositiveIntegerField(blank=True, default=5, null=True),
        ),
    ]
