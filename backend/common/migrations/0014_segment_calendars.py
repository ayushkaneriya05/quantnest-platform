from datetime import time
from django.db import migrations


def seed(apps, schema_editor):
    Calendar = apps.get_model('common', 'ExchangeConfig')
    Holiday = apps.get_model('common', 'MarketHoliday')
    Calendar.objects.filter(exchange='MCX', segment=10).update(segment=20)
    schedules = [('NSE', 10, time(9, 15), time(15, 30)), ('BSE', 10, time(9, 15), time(15, 30)),
                 ('NSE', 11, time(9, 15), time(15, 40)), ('BSE', 11, time(9, 15), time(15, 40)),
                 ('NSE', 12, time(9), time(17)), ('NSE', 20, time(9), time(23, 30)),
                 ('MCX', 20, time(9), time(23, 30))]
    for exchange, segment, opening, closing in schedules:
        row, created = Calendar.objects.get_or_create(exchange=exchange, segment=segment,
            defaults={'timezone': 'Asia/Kolkata', 'market_open': opening, 'market_close': closing})
        if created and segment == 11:
            cash = Calendar.objects.filter(exchange=exchange, segment=10).first()
            if cash:
                Holiday.objects.bulk_create([Holiday(exchange=row, date=h.date, description=h.description,
                    is_partial=h.is_partial, partial_open=h.partial_open, partial_close=h.partial_close)
                    for h in Holiday.objects.filter(exchange=cash)], ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [('common', '0013_alter_exchangeconfig_options_exchangeconfig_segment_and_more')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
