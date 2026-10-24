from django.db import migrations
from django.db.models import F


def preserve(apps, schema_editor):
    Order = apps.get_model('trading', 'Order')
    Order.objects.filter(status='COMPLETE').update(avg_fill_price=F('price'), filled_quantity=F('quantity'))
    Order.objects.filter(position_link__isnull=False).update(reduce_only=True, validity='GTC')
    # Existing working orders had no expiry; preserve that explicit behaviour.
    Order.objects.filter(status='OPEN').update(validity='GTC')
    apps.get_model('trading', 'ClosedPositionLog').objects.update(gross_pnl=F('realized_pnl'))


class Migration(migrations.Migration):
    dependencies = [('trading', '0011_account_charge_profile_account_charges_paid_and_more')]
    operations = [migrations.RunPython(preserve, migrations.RunPython.noop)]
