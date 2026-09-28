from django.db import migrations, models
from django.db.models import Count


def dedupe_broker_orders(apps, schema_editor):
    LiveOrder = apps.get_model("live_trading", "LiveOrder")
    LiveTrade = apps.get_model("live_trading", "LiveTrade")
    ExecutionLog = apps.get_model("live_trading", "ExecutionLog")
    SlippageRecord = apps.get_model("live_trading", "SlippageRecord")
    JournalEntry = apps.get_model("trade_journal", "JournalEntry")
    database = schema_editor.connection.alias

    duplicate_keys = list(
        LiveOrder.objects.using(database)
        .filter(broker_credential_id__isnull=False)
        .exclude(broker_order_id="")
        .values("broker_credential_id", "broker_order_id")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
    )

    for key in duplicate_keys:
        rows = list(
            LiveOrder.objects.using(database)
            .filter(
                broker_credential_id=key["broker_credential_id"],
                broker_order_id=key["broker_order_id"],
            )
            .order_by("id")
        )
        keeper = rows[0]
        # Keep the most advanced broker state while retaining the stable first
        # local order ID referenced by strategy and execution records.
        status_priority = {
            "PENDING": 0,
            "PLACED": 1,
            "PARTIAL_FILL": 2,
            "CANCELLED": 3,
            "REJECTED": 3,
            "EXPIRED": 3,
            "FILLED": 4,
        }
        best = max(rows, key=lambda row: (status_priority.get(row.status, 0), row.filled_quantity or 0, row.id))
        keeper.status = best.status
        keeper.filled_quantity = max(row.filled_quantity or 0 for row in rows)
        keeper.pending_quantity = max((keeper.quantity or 0) - keeper.filled_quantity, 0)
        keeper.avg_fill_price = best.avg_fill_price or keeper.avg_fill_price
        keeper.exchange_order_id = best.exchange_order_id or keeper.exchange_order_id
        keeper.reconciliation_attempts = max(row.reconciliation_attempts or 0 for row in rows)
        keeper.last_reconciliation = max(
            (row.last_reconciliation for row in rows if row.last_reconciliation),
            default=keeper.last_reconciliation,
        )
        keeper.save(using=database)

        for duplicate in rows[1:]:
            LiveTrade.objects.using(database).filter(exit_order_id=duplicate.pk).update(exit_order_id=keeper.pk)
            ExecutionLog.objects.using(database).filter(order_id=duplicate.pk).update(order_id=keeper.pk)
            JournalEntry.objects.using(database).filter(live_order_id=duplicate.pk).update(live_order_id=keeper.pk)
            if not SlippageRecord.objects.using(database).filter(order_id=keeper.pk).exists():
                SlippageRecord.objects.using(database).filter(order_id=duplicate.pk).update(order_id=keeper.pk)
            duplicate.delete(using=database)


class Migration(migrations.Migration):
    # PostgreSQL cannot create the unique index while the cleanup's FK trigger
    # events are pending in the same transaction. Commit the data cleanup before
    # running AddConstraint. The cleanup is idempotent, so a failed index build
    # can be retried safely.
    atomic = False

    dependencies = [
        ("live_trading", "0018_liveorder_last_reconciliation_and_more"),
        ("trade_journal", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(dedupe_broker_orders, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="liveorder",
            constraint=models.UniqueConstraint(
                fields=("broker_credential", "broker_order_id"),
                condition=models.Q(broker_credential__isnull=False) & ~models.Q(broker_order_id=""),
                name="uniq_live_order_broker_id_per_credential",
            ),
        ),
    ]
