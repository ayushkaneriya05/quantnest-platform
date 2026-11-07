from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('instruments', '0016_currency_price_precision')]

    operations = [migrations.AlterField(
        model_name='instrument', name='fy_token',
        field=models.CharField(max_length=30, unique=True, db_index=True,
            null=True, blank=True, default=None,
            help_text='Fyers token; unknown for history-only contracts discovered after expiry'))]
