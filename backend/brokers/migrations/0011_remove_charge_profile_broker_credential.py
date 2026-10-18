from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('brokers', '0010_remove_brokersession_refresh_token')]

    operations = [
        migrations.RemoveField(
            model_name='brokerchargeprofile',
            name='broker_credential',
        ),
    ]
