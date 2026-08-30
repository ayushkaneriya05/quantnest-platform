# Generated migration for broker model refactoring

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brokers', '0006_remove_ordersettings_primary_broker_and_more'),
    ]

    operations = [
        # Remove OrderReconciliation model
        migrations.DeleteModel(
            name='OrderReconciliation',
        ),
        
        # Simplify OrderSettings model
        migrations.RemoveField(
            model_name='ordersettings',
            name='default_slippage_pct',
        ),
        migrations.RemoveField(
            model_name='ordersettings',
            name='max_retries',
        ),
        migrations.RemoveField(
            model_name='ordersettings',
            name='partial_fill_action',
        ),
        migrations.RemoveField(
            model_name='ordersettings',
            name='retry_delay_ms',
        ),
        migrations.RemoveField(
            model_name='ordersettings',
            name='use_amo_orders',
        ),
    ]
