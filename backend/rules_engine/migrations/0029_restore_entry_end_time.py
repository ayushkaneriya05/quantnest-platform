import datetime

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('rules_engine', '0028_alter_timerule_end_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timerule',
            name='end_time',
            field=models.TimeField(
                blank=True,
                default=datetime.time(15, 30),
                help_text='End time for new entries in the configured timezone',
                null=True,
            ),
        ),
    ]
