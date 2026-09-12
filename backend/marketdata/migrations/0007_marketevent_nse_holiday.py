# Add NSE_HOLIDAY choice to MarketEvent.event_type.
# Choice additions are Django metadata only -- no SQL DDL is emitted.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketdata", "0006_candle_instrument_index"),
    ]

    operations = [
        migrations.AlterField(
            model_name="marketevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("EARNINGS", "Earnings"),
                    ("RBI_POLICY", "RBI Policy"),
                    ("BUDGET", "Union Budget"),
                    ("GDP", "GDP Data"),
                    ("INFLATION", "Inflation Data"),
                    ("FED_DECISION", "Fed Decision"),
                    ("NEWS", "News Event"),
                    ("CUSTOM", "Custom Event"),
                    ("NSE_HOLIDAY", "NSE Holiday"),
                ],
                max_length=32,
            ),
        ),
    ]
