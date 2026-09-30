from datetime import time

from django.db import migrations, models
import common.enums


def align_empty_time_rules(apps, schema_editor):
    TimeRule = apps.get_model('rules_engine', 'TimeRule')
    for rule in TimeRule.objects.all().iterator():
        # Only migrate untouched rows that were auto-created with model
        # defaults while the UI displayed weekday/market-hour defaults.
        # Preserve any row an operator has saved or customized.
        if (
            abs((rule.updated_at - rule.created_at).total_seconds()) <= 1
            and not rule.trading_days
            and rule.start_time is None
            and rule.end_time is None
        ):
            TimeRule.objects.filter(pk=rule.pk).update(
                trading_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
                start_time=time(9, 15),
                end_time=time(15, 30),
            )


class Migration(migrations.Migration):
    dependencies = [
        ('rules_engine', '0024_alter_rulegroup_action'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timerule',
            name='trading_days',
            field=models.JSONField(
                default=common.enums.default_trading_days,
                help_text="List of trading days: ['Monday', 'Tuesday', ...]",
            ),
        ),
        migrations.AlterField(
            model_name='timerule',
            name='start_time',
            field=models.TimeField(blank=True, default=time(9, 15), help_text='Start time for trading (IST)', null=True),
        ),
        migrations.AlterField(
            model_name='timerule',
            name='end_time',
            field=models.TimeField(blank=True, default=time(15, 30), help_text='End time for trading (IST)', null=True),
        ),
        migrations.RunPython(align_empty_time_rules, migrations.RunPython.noop),
    ]
