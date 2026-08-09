from django.db import migrations


def seed_charge_profiles(apps, schema_editor):
    """Seed default BrokerChargeProfile entries for supported brokers.
    
    These profiles use publicly available charge structures as of 2024.
    Users can duplicate and customize these profiles.
    """
    BrokerChargeProfile = apps.get_model('brokers', 'BrokerChargeProfile')
    User = apps.get_model('users', 'User')
    
    # Get or skip if no admin user exists (fresh install)
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        return
    
    profiles = [
        {
            'name': 'Zerodha - Equity Intraday',
            'brokerage_per_order': 20,
            'brokerage_pct': 0.03,
            'brokerage_cap': 20,
            'stt_eq_delivery_pct': 0.1,
            'stt_eq_intraday_pct': 0.025,
            'stt_futures_pct': 0.02,
            'stt_options_sell_pct': 0.1,
            'exchange_txn_pct': 0.00345,
            'exchange_txn_fo_pct': 0.05,
            'sebi_turnover_pct': 0.0001,
            'stamp_duty_pct': 0.003,
            'gst_pct': 18.00,
            'is_default': True,
        },
        {
            'name': 'Fyers - Equity',
            'brokerage_per_order': 20,
            'brokerage_pct': 0.03,
            'brokerage_cap': 20,
            'stt_eq_delivery_pct': 0.1,
            'stt_eq_intraday_pct': 0.025,
            'stt_futures_pct': 0.02,
            'stt_options_sell_pct': 0.1,
            'exchange_txn_pct': 0.00345,
            'exchange_txn_fo_pct': 0.05,
            'sebi_turnover_pct': 0.0001,
            'stamp_duty_pct': 0.003,
            'gst_pct': 18.00,
            'is_default': False,
        },
        {
            'name': 'Angel One - Equity',
            'brokerage_per_order': 20,
            'brokerage_pct': 0.25,
            'brokerage_cap': 20,
            'stt_eq_delivery_pct': 0.1,
            'stt_eq_intraday_pct': 0.025,
            'stt_futures_pct': 0.02,
            'stt_options_sell_pct': 0.1,
            'exchange_txn_pct': 0.00345,
            'exchange_txn_fo_pct': 0.05,
            'sebi_turnover_pct': 0.0001,
            'stamp_duty_pct': 0.003,
            'gst_pct': 18.00,
            'is_default': False,
        },
    ]
    
    for profile_data in profiles:
        BrokerChargeProfile.objects.get_or_create(
            user=admin_user,
            name=profile_data['name'],
            defaults=profile_data,
        )


def reverse_seed(apps, schema_editor):
    BrokerChargeProfile = apps.get_model('brokers', 'BrokerChargeProfile')
    BrokerChargeProfile.objects.filter(
        name__in=['Zerodha - Equity Intraday', 'Fyers - Equity', 'Angel One - Equity']
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('brokers', '0004_add_broker_charge_profile'),
    ]
    
    operations = [
        migrations.RunPython(seed_charge_profiles, reverse_seed),
    ]
