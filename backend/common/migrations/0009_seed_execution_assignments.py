from django.db import migrations


def seed(apps, schema_editor):
    from django.conf import settings
    from quantnest_runtime.ownership import partition
    Assignment = apps.get_model("common", "RuntimeAssignment")
    alias = schema_editor.connection.alias
    for scope, app, name in (("live", "live_trading", "TradingSession"), ("paper", "paper_trading", "PaperTradingSession")):
        Session = apps.get_model(app, name)
        for session in Session.objects.using(alias).filter(status__in=["RUNNING", "PAUSED", "STOPPING", "ERROR"]).select_related(
            "allocation__deployed_version").iterator(chunk_size=500):
            version = session.allocation.deployed_version if session.allocation_id else None
            if not version:
                continue
            user_id = session.user_id if scope == "live" else session.account.user_id
            for item in version.config_snapshot.get("watchlist_instruments", []):
                instrument_id = item.get("instrument_id")
                if instrument_id:
                    Assignment.objects.using(alias).update_or_create(
                        scope=scope, session_id=str(session.pk), instrument_id=instrument_id,
                        defaults={"user_id": user_id, "shard": partition(f"{scope}:{session.pk}:{instrument_id}", settings.EXECUTION_SHARDS)},
                    )


class Migration(migrations.Migration):
    dependencies = [("common", "0008_runtimeassignment"),
                    ("live_trading", "0026_initialize_order_cursors"),
                    ("paper_trading", "0015_papertradingsession_auto_disable_state")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
