from decimal import Decimal
from django.db import migrations


def initialize(apps, schema_editor):
    Order = apps.get_model("trading", "Order")
    Position = apps.get_model("trading", "Position")
    holdings = {(row.account_id, row.instrument_id): max(row.quantity, 0) for row in Position.objects.all().iterator()}
    updates = []
    for order in Order.objects.filter(status="OPEN", position_link__isnull=True).order_by("created_at", "pk").iterator():
        price = order.price or order.trigger_price
        if not price or price <= 0:
            order.status = "REJECTED"
        else:
            quantity = order.quantity
            if order.transaction_type == "SELL":
                key = order.account_id, order.instrument_id
                closed = min(holdings.get(key, 0), quantity)
                holdings[key] = max(holdings.get(key, 0) - closed, 0)
                quantity -= closed
            order.reserved_cash = (price * quantity).quantize(Decimal("0.01"))
        updates.append(order)
        if len(updates) == 1000:
            Order.objects.bulk_update(updates, ["status", "reserved_cash"], batch_size=1000)
            updates = []
    if updates:
        Order.objects.bulk_update(updates, ["status", "reserved_cash"], batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [("trading", "0008_order_reserved_cash_and_more")]
    operations = [migrations.RunPython(initialize, migrations.RunPython.noop)]
