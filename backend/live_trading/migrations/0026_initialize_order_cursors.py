"""Initialize durable cursors before broker observations resume."""
from decimal import Decimal
from django.db import migrations


def initialize_orders(apps, schema_editor):
    Order = apps.get_model("live_trading", "LiveOrder")
    alias = schema_editor.connection.alias
    for order in Order.objects.using(alias).select_related("allocation").iterator(chunk_size=1000):
        order.filled_value = Decimal(order.avg_fill_price or 0) * order.filled_quantity
        if order.allocation_id:
            order.strategy_version_id = order.allocation.deployed_version_id
        if order.closed_trades.exists():
            order.intent = "EXIT"
        order.save(using=alias, update_fields=["filled_value", "strategy_version", "intent"])


class Migration(migrations.Migration):
    dependencies = [("live_trading", "0025_liveorder_filled_value_liveorder_intent_and_more")]
    operations = [migrations.RunPython(initialize_orders, migrations.RunPython.noop)]
