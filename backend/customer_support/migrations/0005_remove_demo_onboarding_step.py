from django.db import migrations


def remove_retired_data(apps, schema_editor):
    Onboarding = apps.get_model('customer_support', 'Onboarding')
    rows = Onboarding.objects.using(schema_editor.connection.alias)
    for row in rows.iterator(chunk_size=500):
        if 'demo' in row.completed_steps:
            row.completed_steps = [step for step in row.completed_steps if step != 'demo']
            row.save(using=schema_editor.connection.alias, update_fields=['completed_steps'])
    CustomerEvent = apps.get_model('customer_support', 'CustomerEvent')
    DeliveryJob = apps.get_model('commercial', 'DeliveryJob')
    CustomerEvent.objects.using(schema_editor.connection.alias).filter(name='demo_opened').delete()
    DeliveryJob.objects.using(schema_editor.connection.alias).filter(kind='analytics', payload__name='demo_opened').delete()


class Migration(migrations.Migration):
    dependencies = [('customer_support', '0004_erasurerequest')]
    operations = [migrations.RunPython(remove_retired_data, migrations.RunPython.noop)]
