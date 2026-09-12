# Add instrument-based index to the Candle table for analytics/backtest queries.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("instruments", "0009_remove_executionroute_risk_per_trade_amount"),
        ("marketdata", "0005_candle"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="candle",
            index=models.Index(
                fields=["instrument", "timeframe", "-time"],
                name="candle_instrument_tf_time_idx",
            ),
        ),
    ]
