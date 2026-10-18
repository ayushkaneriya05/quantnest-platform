# Optional contract lists can remain empty when the agreed scope does not need them.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('installations', '0002_privatecontract_broker_account_limit_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='privatecontract',
            name='capabilities',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='privatecontract',
            name='limits',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='privatecontract',
            name='qualified_integrations',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='privatecontract',
            name='supported_releases',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
