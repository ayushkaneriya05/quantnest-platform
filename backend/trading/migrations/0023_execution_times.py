import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('trading', '0022_alter_closedpositionlog_exit_reason_and_more')]
    operations = [
        migrations.AlterField(model_name='position', name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now)),
        migrations.AlterField(model_name='tradehistory', name='timestamp',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
        migrations.AlterField(model_name='closedpositionlog', name='exit_time',
            field=models.DateTimeField(default=django.utils.timezone.now)),
    ]
