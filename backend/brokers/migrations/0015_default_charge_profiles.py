from django.conf import settings
from django.db import migrations, models


def ensure_default_charge_profiles(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Profile = apps.get_model('brokers', 'BrokerChargeProfile')
    database = schema_editor.connection.alias
    for user_id in User.objects.using(database).values_list('pk', flat=True).iterator():
        profiles = Profile.objects.using(database).filter(user_id=user_id)
        profile = profiles.order_by('-is_default', '-created_at', '-pk').first()
        if profile is None:
            profiles.create(user_id=user_id, name='QuantNest', is_default=True)
        else:
            profiles.exclude(pk=profile.pk).filter(is_default=True).update(is_default=False)
            profiles.filter(pk=profile.pk).update(is_default=True)


class Migration(migrations.Migration):
    dependencies = [
        ('brokers', '0014_terminal_contract_settings'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(ensure_default_charge_profiles, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='brokerchargeprofile',
            constraint=models.UniqueConstraint(
                fields=('user',), condition=models.Q(is_default=True),
                name='unique_default_charge_profile_per_user',
            ),
        ),
    ]
