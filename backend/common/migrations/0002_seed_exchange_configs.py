from django.db import migrations
from datetime import time


def seed_exchange_configs(apps, schema_editor):
    """Seed default exchange configurations for Indian markets."""
    ExchangeConfig = apps.get_model('common', 'ExchangeConfig')
    
    configs = [
        {
            'exchange': 'NSE',
            'market_open': time(9, 15),
            'market_close': time(15, 30),
            'pre_market_open': time(9, 0),
            'pre_market_close': time(9, 15),
        },
        {
            'exchange': 'BSE',
            'market_open': time(9, 15),
            'market_close': time(15, 30),
            'pre_market_open': time(9, 0),
            'pre_market_close': time(9, 15),
        },
        {
            'exchange': 'NFO',
            'market_open': time(9, 15),
            'market_close': time(15, 30),
            'pre_market_open': None,
            'pre_market_close': None,
        },
        {
            'exchange': 'MCX',
            'market_open': time(9, 0),
            'market_close': time(23, 30),
            'pre_market_open': None,
            'pre_market_close': None,
        },
    ]
    
    for config_data in configs:
        ExchangeConfig.objects.get_or_create(
            exchange=config_data['exchange'],
            defaults=config_data,
        )


def reverse_seed(apps, schema_editor):
    ExchangeConfig = apps.get_model('common', 'ExchangeConfig')
    ExchangeConfig.objects.filter(
        exchange__in=['NSE', 'BSE', 'NFO', 'MCX']
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('common', '0001_add_exchange_config_and_holidays'),
    ]
    
    operations = [
        migrations.RunPython(seed_exchange_configs, reverse_seed),
    ]
