# Provider refund retry identity and a stable first-observed accounting date.

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('commercial', '0008_managed_catalog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='period_start',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='paid_through',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='founding_price_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='protected_price_minor',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='refundrequest',
            name='provider_idempotency_key',
            field=models.CharField(blank=True, editable=False, max_length=100),
        ),
        migrations.AlterField(
            model_name='refundrecord',
            name='observed_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
