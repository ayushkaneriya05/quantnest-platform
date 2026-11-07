from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations


def project_collateral(apps, schema_editor):
    """Initialize read models from committed financial state, without replaying fills."""
    alias = schema_editor.connection.alias
    checkpoints = apps.get_model('execution', 'AccountCheckpoint')
    money = Decimal('0.01')
    for checkpoint in checkpoints.objects.using(alias).filter(mode__in=('paper', 'live')).iterator():
        state = checkpoint.state['fields']
        mode = checkpoint.mode
        order_model = apps.get_model(f'{mode}_trading', 'PaperOrder' if mode == 'paper' else 'LiveOrder')
        for _, record in state['orders']['mapping']:
            order = record['fields']
            # JSON decimal values are strings: retain exact money on migration.
            reserved = Decimal(order['reserved']['decimal']).quantize(money, rounding=ROUND_HALF_UP)
            order_model.objects.using(alias).filter(request_id=order['identity']).update(reserved_capital=reserved)
        if mode == 'live':
            positions = apps.get_model('live_trading', 'LivePosition')
            sessions = apps.get_model('live_trading', 'TradingSession')
            allocations = dict(sessions.objects.using(alias).filter(
                broker_credential_id=checkpoint.account_id).values_list('pk', 'allocation_id'))
            for key, record in state['positions']['mapping']:
                _, session_id, instrument_id = key['tuple']
                allocation_id = allocations.get(session_id)
                if allocation_id is None:
                    raise ValueError(f'Live position session {session_id} has no allocation; repair ownership before migrating.')
                positions.objects.using(alias).filter(allocation_id=allocation_id, instrument_id=instrument_id).update(
                    margin_blocked=Decimal(record['fields']['margin']['decimal']).quantize(money, rounding=ROUND_HALF_UP))

    # An exposed record without its authoritative checkpoint must be reviewed.
    # Guessing from option premium could substantially understate short margin.
    for app, model, field in (
        ('paper_trading', 'PaperOrder', 'account_id'),
        ('live_trading', 'LiveOrder', 'broker_credential_id'),
        ('live_trading', 'LivePosition', 'broker_credential_id'),
    ):
        mode = app.removesuffix('_trading')
        known = checkpoints.objects.using(alias).filter(mode=mode).values('account_id')
        rows = apps.get_model(app, model).objects.using(alias)
        if model.endswith('Position'):
            rows = rows.filter(quantity__gt=0)
        else:
            rows = rows.filter(status__in=('PENDING', 'PLACED', 'PARTIAL_FILL', 'UNKNOWN'))
        if rows.exclude(**{f'{field}__in': known}).exists():
            raise ValueError(f'{model} has exposure without an execution checkpoint; recover it before migrating.')


class Migration(migrations.Migration):
    dependencies = [
        ('execution', '0002_alter_command_kind_evaluationcheckpoint'),
        ('paper_trading', '0022_paperorder_reserved_capital'),
        ('live_trading', '0032_liveorder_reserved_capital_and_more'),
    ]

    operations = [migrations.RunPython(project_collateral, migrations.RunPython.noop)]
