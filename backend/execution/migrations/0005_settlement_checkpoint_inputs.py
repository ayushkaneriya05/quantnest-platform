"""Fill new settlement inputs once; runtime recovery needs no legacy branch."""
from django.db import migrations


def upgrade_checkpoints(apps, schema_editor):
    checkpoints = apps.get_model('execution', 'AccountCheckpoint')
    instruments = apps.get_model('instruments', 'Instrument')
    rights = dict(instruments.objects.values_list('pk', 'option_type'))

    def visit(value, row):
        if isinstance(value, list):
            for item in value:
                visit(item, row)
        elif isinstance(value, dict):
            fields = value.get('fields', {})
            if value.get('record') == 'Contract':
                fields['option_type'] = rights.get(fields['instrument_id'], '')
            elif value.get('record') == 'Position' and fields.get('last_fill_at') is None:
                identity = fields['unit']['tuple'][2]
                opened_at = fields['opened_at']['datetime']
                if row.mode == 'terminal':
                    fills = apps.get_model('trading', 'TradeHistory').objects.filter(
                        order__account_id=row.account_id, order__instrument_id=identity, timestamp__gte=opened_at)
                    last_at = fills.order_by('-timestamp').values_list('timestamp', flat=True).first()
                else:
                    model = apps.get_model('paper_trading', 'PaperOrder') if row.mode == 'paper' else apps.get_model('live_trading', 'LiveOrder')
                    owner = {'account_id': row.account_id} if row.mode == 'paper' else {'broker_credential_id': row.account_id}
                    fills = model.objects.filter(**owner, instrument_id=identity, executed_at__gte=opened_at)
                    last_at = fills.order_by('-executed_at').values_list('executed_at', flat=True).first()
                fields['last_fill_at'] = {'datetime': last_at.isoformat()} if last_at else fields['opened_at']
            for item in value.values():
                visit(item, row)

    for row in checkpoints.objects.iterator():
        visit(row.state, row)
        checkpoints.objects.filter(pk=row.pk).update(state=row.state)


class Migration(migrations.Migration):
    dependencies = [
        ('execution', '0004_alter_command_kind_settlementprice_settlementposting_and_more'),
        ('trading', '0021_position_settled_pnl'),
        ('paper_trading', '0024_papertrade_settled_pnl'),
        ('live_trading', '0033_liveposition_settled_pnl'),
    ]
    operations = [migrations.RunPython(upgrade_checkpoints, migrations.RunPython.noop)]
