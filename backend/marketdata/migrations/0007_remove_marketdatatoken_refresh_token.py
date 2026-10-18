from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('marketdata', '0006_alter_marketdatatoken_access_token_and_more')]
    operations = [migrations.RemoveField(model_name='marketdatatoken', name='refresh_token')]
