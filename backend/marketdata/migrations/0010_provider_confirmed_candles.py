from django.db import migrations, models


def clear_legacy_coverage(apps, schema_editor):
    # Older rows mixed observed ticks with provider history. Retain those rows,
    # but require provider confirmation before using them for analysis.
    apps.get_model('marketdata', 'HistoryCoverage').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [('marketdata', '0009_history_coverage')]
    operations = [
        migrations.AddField(
            model_name='candle', name='provider_confirmed',
            field=models.BooleanField(default=False, db_default=False),
        ),
        migrations.RunPython(clear_legacy_coverage, migrations.RunPython.noop),
    ]
