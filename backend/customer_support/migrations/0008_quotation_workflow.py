# Automatic quotation metadata, frozen issued scope and support form validation.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def freeze_unaccepted_scopes(apps, schema_editor):
    Quotation = apps.get_model('customer_support', 'Quotation')
    rows = Quotation.objects.using(schema_editor.connection.alias).filter(accepted_at__isnull=True,
        scope_snapshot={}).select_related('engagement')
    for quote in rows.iterator(chunk_size=500):
        snapshot = {name: getattr(quote.engagement, name) for name in
            ('scope', 'acceptance_criteria', 'ownership_terms', 'support_allowance')}
        Quotation.objects.using(schema_editor.connection.alias).filter(pk=quote.pk).update(scope_snapshot=snapshot)


class Migration(migrations.Migration):

    dependencies = [
        ('customer_support', '0007_remove_discovery_planning_record'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='engagement',
            name='change_requests',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='engagement',
            name='active_slot',
            field=models.PositiveSmallIntegerField(blank=True, editable=False, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='engagement',
            name='stage',
            field=models.CharField(choices=[('requirements', 'Requirements'), ('quoted', 'Quoted'), ('accepted', 'Accepted'), ('implementation', 'Implementation'), ('acceptance', 'Acceptance'), ('completed', 'Completed'), ('paused', 'Paused'), ('cancelled', 'Cancelled')], default='requirements', max_length=25),
        ),
        migrations.AlterField(
            model_name='quotation',
            name='accepted_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='quotation',
            name='approved_by',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='quotation',
            name='revision',
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AlterField(
            model_name='quotation',
            name='scope_snapshot',
            field=models.JSONField(default=dict, editable=False),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.CharField(choices=[('received', 'Received'), ('awaiting_support', 'Awaiting support'), ('awaiting_customer', 'Awaiting your reply'), ('in_progress', 'In progress'), ('resolved', 'Resolved'), ('closed', 'Closed')], default='received', max_length=25),
        ),
        migrations.RunPython(freeze_unaccepted_scopes, migrations.RunPython.noop),
    ]
