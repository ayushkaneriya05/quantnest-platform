from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('brokers', '0009_alter_brokercredential_api_secret_and_more')]
    operations = [migrations.RemoveField(model_name='brokersession', name='refresh_token')]
