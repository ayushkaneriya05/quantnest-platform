from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('marketdata', '0012_remove_market_events')]
    operations = [migrations.AddField(model_name='historycoverage', name='rejected_times',
        field=models.JSONField(default=list, db_default=[], blank=True,
            help_text='UTC epoch seconds of provider candles excluded for invalid OHLCV'))]
