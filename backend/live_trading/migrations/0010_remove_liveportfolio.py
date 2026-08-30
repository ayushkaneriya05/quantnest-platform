from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("live_trading", "0009_alter_executionlog_event_type_alter_liveorder_status_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="liveorder",
            name="portfolio",
        ),
        migrations.RemoveField(
            model_name="livestrategyallocation",
            name="portfolio",
        ),
        migrations.DeleteModel(
            name="LivePortfolio",
        ),
    ]
