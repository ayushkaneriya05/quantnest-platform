from django.db import migrations


def initialize_missing_configurations(apps, schema_editor):
    Strategy = apps.get_model('strategies', 'Strategy')
    for app, name in (('strategies', 'EntryOrderConfig'), ('strategies', 'ExitOrderConfig'),
            ('rules_engine', 'TimeRule'),
            ('rules_engine', 'SpecialEventFilter')):
        Config = apps.get_model(app, name)
        missing = Strategy.objects.exclude(pk__in=Config.objects.values('strategy_id'))
        for identity in missing.values_list('pk', flat=True).iterator(chunk_size=1000):
            Config.objects.create(strategy_id=identity)


class Migration(migrations.Migration):
    dependencies = [
        ('strategies', '0026_remove_entryorderconfig_price_offset'),
        ('rules_engine', '0027_alter_timerule_market_session'),
    ]
    operations = [migrations.RunPython(initialize_missing_configurations, migrations.RunPython.noop)]
