from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("live_trading", "0013_remove_liveposition_day_pnl"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="livestrategyallocation",
            name="available_capital",
        ),
        migrations.RemoveField(
            model_name="livestrategyallocation",
            name="last_synced_at",
        ),
        migrations.RemoveField(
            model_name="livestrategyallocation",
            name="realized_pnl",
        ),
        migrations.RemoveField(
            model_name="livestrategyallocation",
            name="reserved_capital",
        ),
        migrations.RemoveField(
            model_name="livestrategyallocation",
            name="total_pnl",
        ),
        migrations.RemoveField(
            model_name="livestrategyallocation",
            name="unrealized_pnl",
        ),
        migrations.RemoveField(
            model_name="livestrategyallocation",
            name="used_capital",
        ),
        migrations.RemoveField(
            model_name="tradingsession",
            name="pnl",
        ),
        migrations.RemoveField(
            model_name="tradingsession",
            name="trades_count",
        ),
    ]
