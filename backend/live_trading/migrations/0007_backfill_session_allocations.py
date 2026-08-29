from django.db import migrations


def backfill_session_allocations(apps, schema_editor):
    TradingSession = apps.get_model("live_trading", "TradingSession")
    LiveStrategyAllocation = apps.get_model("live_trading", "LiveStrategyAllocation")
    LiveOrder = apps.get_model("live_trading", "LiveOrder")

    status_priority = {"RUNNING": 0, "PAUSED": 1, "ERROR": 2, "STOPPED": 3}

    for allocation in LiveStrategyAllocation.objects.all().iterator():
        sessions = list(
            TradingSession.objects.filter(
                user_id=allocation.user_id,
                strategy_id=allocation.strategy_id,
                broker_credential_id=allocation.broker_credential_id,
                allocation__isnull=True,
            ).order_by("-updated_at", "-id")
        )
        if sessions:
            sessions.sort(key=lambda session: (status_priority.get(session.status, 99), -session.id))
            canonical = sessions[0]
            canonical.allocation_id = allocation.id
            canonical.save(update_fields=["allocation"])

            for duplicate in sessions[1:]:
                LiveOrder.objects.filter(session_id=duplicate.id).update(session_id=canonical.id)


class Migration(migrations.Migration):

    dependencies = [
        ("live_trading", "0006_tradingsession_allocation"),
    ]

    operations = [
        migrations.RunPython(backfill_session_allocations, migrations.RunPython.noop),
    ]