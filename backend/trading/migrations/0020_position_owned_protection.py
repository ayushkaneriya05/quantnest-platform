from django.db import migrations


def retire_attached_orders(apps, schema_editor):
    """Keep historical orders; active protection now belongs to its position."""
    Order = apps.get_model('trading', 'Order')
    Position = apps.get_model('trading', 'Position')
    for order in Order.objects.filter(status='OPEN', position_link__isnull=False).iterator():
        # Old bracket rows can be the only saved copy of a protection level.
        field = 'stop_loss' if order.order_type in ('STOP', 'STOP_LIMIT') else 'take_profit'
        price = order.trigger_price if field == 'stop_loss' else order.price
        if price is not None:
            Position.objects.filter(pk=order.position_link_id, **{f'{field}__isnull': True}).update(**{field: price})
        order.status, order.reserved_cash = 'CANCELLED', 0
        order.rejection_reason = 'Replaced by position protection in the shared execution engine.'
        order.save(update_fields=['status', 'reserved_cash', 'rejection_reason'])


class Migration(migrations.Migration):
    dependencies = [('trading', '0019_order_request_id')]
    operations = [
        migrations.RunPython(retire_attached_orders, migrations.RunPython.noop),
        migrations.RemoveField(model_name='order', name='is_oco'),
        migrations.RemoveField(model_name='order', name='oco_linked_order'),
        migrations.RemoveField(model_name='order', name='position_link'),
    ]
