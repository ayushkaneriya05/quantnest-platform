from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("brokers", "0007_refactor_broker_models")]
    operations = [migrations.DeleteModel(name="OrderSettings")]
