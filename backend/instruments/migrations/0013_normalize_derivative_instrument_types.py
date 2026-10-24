from django.db import migrations


def normalize_types(apps, schema_editor):
    Instrument = apps.get_model('instruments', 'Instrument')
    # Frozen FYERS exchange codes keep this historical migration reproducible.
    instruments = Instrument.objects.using(schema_editor.connection.alias)
    instruments.filter(ex_inst_type__in=[16, 17, 18, 25, 30, 33, 34, 35]).update(instrument_type='FUTURE')
    instruments.filter(ex_inst_type__in=[19, 31, 32, 36, 37]).update(instrument_type='OPTION')
    instruments.filter(ex_inst_type=24).update(instrument_type='INDEX')


def restore_asset_types(apps, schema_editor):
    Instrument = apps.get_model('instruments', 'Instrument')
    instruments = Instrument.objects.using(schema_editor.connection.alias)
    instruments.filter(ex_inst_type__in=[16, 17, 18, 19, 24, 25]).update(instrument_type='CURRENCY')
    instruments.filter(ex_inst_type__in=[30, 31, 32, 33, 34, 35, 36, 37]).update(instrument_type='COMMODITY')


class Migration(migrations.Migration):
    dependencies = [
        ('instruments', '0012_remove_executionroute_avoid_same_day_expiry_and_more'),
    ]

    operations = [migrations.RunPython(normalize_types, restore_asset_types)]
