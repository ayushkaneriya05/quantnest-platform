"""Return fees prepaid on open exposure before removing its fee cache."""
from django.db import migrations
from django.db.models import F, Sum


def refund_open_fees(apps, schema_editor):
    alias = schema_editor.connection.alias
    Position = apps.get_model("trading", "Position")
    Account = apps.get_model("trading", "Account")
    refunds = (Position.objects.using(alias).filter(entry_charges__gt=0)
               .values("account_id").annotate(total=Sum("entry_charges")))
    for refund in refunds:
        Account.objects.using(alias).filter(pk=refund["account_id"]).update(
            balance=F("balance") + refund["total"],
            charges_paid=F("charges_paid") - refund["total"],
        )


class Migration(migrations.Migration):
    dependencies = [("trading", "0017_remove_terminal_validity")]

    operations = [
        migrations.RunPython(refund_open_fees, migrations.RunPython.noop),
        migrations.RemoveField(model_name="position", name="entry_charges"),
    ]
