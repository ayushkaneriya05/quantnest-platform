import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('paper_trading', '0025_alter_paperposition_unique_together_and_more')]
    operations = [migrations.AlterField(model_name='paperposition', name='opened_at',
        field=models.DateTimeField(default=django.utils.timezone.now))]
