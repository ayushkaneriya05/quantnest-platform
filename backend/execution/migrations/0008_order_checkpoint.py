"""Split completed order history without discarding any recovery information."""
import django.db.models.deletion
from django.db import migrations, models


def split_orders(apps, schema_editor):
    Account = apps.get_model('execution', 'AccountCheckpoint')
    Order = apps.get_model('execution', 'OrderCheckpoint')
    database = schema_editor.connection.alias
    active = {'PENDING', 'PLACED', 'PARTIAL_FILL', 'UNKNOWN'}
    for account in Account.objects.using(database).iterator(chunk_size=20):
        values = account.state['fields']['orders']['mapping']
        working, completed = [], []
        for identity, state in values:
            if state['fields']['status'] in active:
                working.append([identity, state])
            else:
                completed.append(Order(account_id=account.pk, identity=identity, state=state))
        Order.objects.using(database).bulk_create(completed, batch_size=500)
        account.state['fields']['orders']['mapping'] = working
        account.save(using=database, update_fields=['state'])


def merge_orders(apps, schema_editor):
    Account = apps.get_model('execution', 'AccountCheckpoint')
    Order = apps.get_model('execution', 'OrderCheckpoint')
    database = schema_editor.connection.alias
    for account in Account.objects.using(database).iterator(chunk_size=20):
        values = dict(account.state['fields']['orders']['mapping'])
        values.update(Order.objects.using(database).filter(account_id=account.pk).values_list('identity', 'state'))
        account.state['fields']['orders']['mapping'] = list(values.items())
        account.save(using=database, update_fields=['state'])


class Migration(migrations.Migration):
    dependencies = [('execution', '0007_alter_command_kind')]
    operations = [
        migrations.CreateModel(
            name='OrderCheckpoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identity', models.CharField(max_length=160)),
                ('state', models.JSONField()),
                ('account', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.CASCADE,
                    related_name='completed_orders', to='execution.accountcheckpoint')),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('account', 'identity'),
                        name='execution_order_checkpoint')]},
        ),
        migrations.RunPython(split_orders, merge_orders),
    ]
