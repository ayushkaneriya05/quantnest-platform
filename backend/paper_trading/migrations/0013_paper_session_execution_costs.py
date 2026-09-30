from django.db import migrations, models
import django.db.models.deletion


PROFILE_FIELDS = (
    "brokerage_per_order",
    "brokerage_pct",
    "brokerage_cap",
    "stt_eq_delivery_pct",
    "stt_eq_intraday_pct",
    "stt_futures_pct",
    "stt_options_sell_pct",
    "exchange_txn_pct",
    "exchange_txn_fo_pct",
    "sebi_turnover_pct",
    "stamp_duty_pct",
    "gst_pct",
)


def snapshot_existing_profiles(apps, schema_editor):
    Session = apps.get_model("paper_trading", "PaperTradingSession")
    Profile = apps.get_model("brokers", "BrokerChargeProfile")
    db = schema_editor.connection.alias

    for session in Session.objects.using(db).all().iterator():
        profile = Profile.objects.using(db).filter(user_id=session.user_id, is_default=True).first()
        if profile is None:
            profile = Profile.objects.using(db).filter(user_id=session.user_id).first()
        if profile is None:
            session.charge_profile_snapshot = {"resolved": True}
            session.save(using=db, update_fields=["charge_profile_snapshot"])
            continue

        session.charge_profile_id = profile.pk
        session.charge_profile_snapshot = {
            "name": profile.name,
            **{field: str(getattr(profile, field)) for field in PROFILE_FIELDS},
        }
        session.save(using=db, update_fields=["charge_profile", "charge_profile_snapshot"])


class Migration(migrations.Migration):

    dependencies = [
        ("brokers", "0007_refactor_broker_models"),
        ("paper_trading", "0012_paperorder_request_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="paperorder",
            name="slippage_pct_applied",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=7),
        ),
        migrations.AddField(
            model_name="paperorder",
            name="slippage_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="papertradingsession",
            name="slippage_pct",
            field=models.DecimalField(decimal_places=4, default=0, help_text="Simulated adverse fill adjustment as a percentage.", max_digits=7),
        ),
        migrations.AddField(
            model_name="papertradingsession",
            name="charge_profile_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="papertradingsession",
            name="include_charges",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="papertradingsession",
            name="charge_profile",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="paper_sessions", to="brokers.brokerchargeprofile"),
        ),
        migrations.RunPython(snapshot_existing_profiles, migrations.RunPython.noop),
    ]
