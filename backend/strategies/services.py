import logging
from copy import deepcopy
from django.db import transaction
from django.utils import timezone
from .models import Strategy, StrategyVersion, StrategyTag
from execution.order_reports import ACTIVE

logger = logging.getLogger(__name__)

class StrategySnapshotService:
    """Immutable versions copy the same document used by Studio and execution."""

    @staticmethod
    def validate_config_snapshot(snapshot):
        from .definitions import document_from_snapshot
        if not isinstance(snapshot, dict):
            raise ValueError('Strategy configuration must be an object.')
        required = ('name', 'strategy_type', 'market_type', 'exchange', 'instrument_type')
        if any(field not in snapshot for field in required):
            raise ValueError('The strategy snapshot is missing its classification.')
        document_from_snapshot(snapshot)
        return True

    @staticmethod
    @transaction.atomic
    def create_snapshot(strategy, user=None, change_notes=None, *, config_snapshot=None):
        # The row lock serializes version numbers with edits and restores.
        strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
        snapshot = (StrategySnapshotService._serialize_strategy(strategy)
                    if config_snapshot is None else deepcopy(config_snapshot))
        StrategySnapshotService.validate_config_snapshot(snapshot)
        previous = strategy.versions.order_by('-version_number').first()
        version = StrategyVersion.objects.create(strategy=strategy,
            version_number=previous.version_number + 1 if previous else 1,
            config_snapshot=snapshot, change_notes=change_notes, created_by=user)
        from audit.services import AuditService
        AuditService.configuration_changed(strategy, previous.config_snapshot if previous else {}, snapshot, version)
        return version

    @staticmethod
    @transaction.atomic
    def restore_version(strategy, version_id):
        from .definitions import compile_preview, document_from_snapshot, validate_definition
        strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
        try:
            version = strategy.versions.get(pk=version_id)
        except StrategyVersion.DoesNotExist:
            raise ValueError('Version not found.') from None
        snapshot = version.config_snapshot
        StrategySnapshotService.validate_config_snapshot(snapshot)
        document = validate_definition(document_from_snapshot(snapshot))
        fields = ('name', 'description', 'strategy_type', 'market_type', 'exchange', 'instrument_type')
        values = {key: snapshot[key] for key in fields if key in snapshot}
        # Restore passes the same compiler boundary as an editor save.
        for key, value in values.items():
            setattr(strategy, key, value)
        compile_preview(strategy, document)
        # One explicit version below; model signals must not create another.
        Strategy.objects.filter(pk=strategy.pk).update(**values, definition=document, updated_at=timezone.now())
        strategy.refresh_from_db()
        auto_version = strategy.auto_version_enabled
        strategy.auto_version_enabled = False
        strategy.tags.set([StrategyTag.objects.get_or_create(name=name)[0] for name in snapshot.get('tags', [])])
        strategy.auto_version_enabled = auto_version
        StrategySnapshotService.create_snapshot(strategy, user=strategy.user,
            change_notes=f'Rollback to version {version.version_number}')
        return strategy

    @staticmethod
    def _serialize_strategy(strategy):
        from .definitions import current_document
        fields = ('id', 'user_id', 'name', 'description', 'strategy_type', 'market_type', 'exchange',
                  'instrument_type', 'status', 'visibility', 'auto_version_enabled',
                  'paper_trading_enabled', 'live_trading_enabled')
        return {**{key: getattr(strategy, key) for key in fields}, **current_document(strategy),
                'tags': list(strategy.tags.order_by('name').values_list('name', flat=True))}


class StrategyLifecycleService:
    @staticmethod
    def halt_and_archive(strategy, user):
        """Reuse session square-off; archive only after confirmed settlement."""
        from live_trading.models import TradingSession, LivePosition
        from live_trading.services import LiveExecutionService
        from django.db.models import Q
        if strategy.user_id != user.pk:
            raise ValueError('Choose one of your own strategies.')
        if strategy.status == 'ARCHIVED':
            raise ValueError('Strategy is already archived.')
        sessions = list(TradingSession.objects.filter(strategy=strategy).filter(
            Q(status__in=['RUNNING', 'PAUSED', 'STOPPING', 'ERROR']) |
            Q(orders__status__in=ACTIVE) |
            Q(allocation__positions__quantity__gt=0)).distinct())
        for session in sessions:
            LiveExecutionService.stop_session(session, close_positions=True)
        with transaction.atomic():
            strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
            if TradingSession.objects.filter(pk__in=[item.pk for item in sessions]).exclude(status='STOPPED').exists():
                raise RuntimeError('Square-off is awaiting broker settlement. Review Live sessions and retry archive after all positions and orders settle.')
            StrategyDeploymentService.validate_strategy_lifecycle(strategy)
            if LivePosition.objects.filter(strategy=strategy, quantity__gt=0).exists():
                raise RuntimeError('Unsettled live positions remain. Review their allocation before archiving.')
            strategy.status = 'ARCHIVED'
            strategy.save(update_fields=['status', 'updated_at'])
        return {'status': 'archived', 'sessions_stopped': len(sessions),
                'message': f"Strategy '{strategy.name}' archived after session settlement."}


class StrategyDeploymentService:
    @staticmethod
    def validate_snapshot(snapshot, mode='paper'):
        """Validate the immutable configuration that execution will actually use."""
        from instruments.services import InstrumentResolver
        from rest_framework.exceptions import ValidationError
        from common.enums import InstrumentType, QuantityType, QuantityUnit, RuleType, Side, StrategyType
        from .definitions import document_from_snapshot, validate_definition
        from execution.preparation import compile_markets
        StrategySnapshotService.validate_config_snapshot(snapshot)
        try:
            validate_definition(document_from_snapshot(snapshot))
            instruments = InstrumentResolver.validate_execution_snapshot(snapshot, historical=mode == 'backtest')
            if (snapshot['strategy_type'] != StrategyType.INTRADAY and snapshot['entry_order_config']['entry_side'] == Side.SELL
                    and any(instruments[watch['instrument_id']].instrument_type == InstrumentType.STOCK
                            and 'contract_selection' not in watch for watch in snapshot['watchlist_instruments'])):
                raise ValueError('Stock short entries require an Intraday strategy. Delivery execution does not include stock borrowing.')
            active = [group for group in snapshot['rule_groups'] if group.get('is_active', True)]
            if not any(group['rule_type'] == RuleType.ENTRY for group in active):
                raise ValueError('The selected version needs an active entry condition.')
            if mode == 'live' and not any(group['rule_type'] == RuleType.STOP_LOSS for group in active):
                raise ValueError('The selected live version needs an active stop-loss condition.')
            if mode != 'backtest':
                from execution.preparation import contract_from_instrument
                compiled = compile_markets(snapshot, 0)
                if any(not item.is_active for item in compiled.instruments.values()):
                    raise ValueError('Signal and traded instruments must be active before deployment.')
                # Validate every tradable candidate once before admission. Index
                # underlyings are data inputs and never receive financial terms.
                contracts = {}
                now = timezone.now()
                for identity in compiled.trade_ids:
                    contract = contract_from_instrument(compiled.instruments[identity])
                    contract.validate(contract.lot_size, (), now.astimezone(compiled.calendars[identity].zone))
                    contracts[identity] = contract
                for watch in snapshot['watchlist_instruments']:
                    identity = watch['instrument_id']
                    sizing = InstrumentResolver.sizing_for(watch, snapshot['position_sizing_rule'])
                    if ('contract_selection' not in watch and sizing['sizing_method'] == QuantityType.FIXED
                            and sizing['quantity_unit'] == QuantityUnit.UNITS
                            and int(sizing['fixed_quantity']) % contracts[identity].lot_size):
                        raise ValueError(f'{instruments[identity].name}: fixed units must be a multiple of lot size {contracts[identity].lot_size}; choose Lots or correct the units.')
        except ValidationError as exc:
            from backend.middleware.api_responses import error_envelope
            raise ValueError(f"Invalid selected version: {error_envelope(exc.detail, 400)['message']}") from None

    @staticmethod
    @transaction.atomic
    def change_version(allocation, version, scope, user):
        """One cold path for version validation, capacity and actor publication."""
        from django.contrib.auth import get_user_model
        from execution.lifecycle import request_session_refresh
        get_user_model().objects.select_for_update().get(pk=user.pk)
        if scope == 'live':
            from brokers.models import BrokerCredential
            from execution.lifecycle import require_execution_scope
            from common.enums import ExecutionScope
            from live_trading.models import LiveStrategyAllocation, LiveOrder, LivePosition, TradingSession
            require_execution_scope(ExecutionScope.LIVE)
            BrokerCredential.objects.select_for_update().get(pk=allocation.broker_credential_id)
            allocation = LiveStrategyAllocation.objects.select_for_update().get(pk=allocation.pk, user=user)
            positions = LivePosition.objects.filter(allocation=allocation, quantity__gt=0)
            orders = LiveOrder.objects.filter(allocation=allocation)
            sessions = list(TradingSession.objects.select_for_update().filter(allocation=allocation))
        else:
            from paper_trading.models import CapitalAllocation, PaperAccount, PaperPosition, PaperOrder
            PaperAccount.objects.select_for_update().filter(allocation=allocation).first()
            allocation = CapitalAllocation.objects.select_for_update().get(pk=allocation.pk, portfolio__user=user)
            positions = PaperPosition.objects.filter(account__allocation=allocation, quantity__gt=0)
            orders = PaperOrder.objects.filter(account__allocation=allocation)
            sessions = list(allocation.paper_sessions.select_for_update())
        if version.strategy_id != allocation.strategy_id:
            raise ValueError('Choose a version belonging to this strategy.')
        if allocation.deployed_version_id == version.pk:
            return allocation
        if scope == "paper" and CapitalAllocation.objects.filter(
            strategy_id=allocation.strategy_id, deployed_version=version
        ).exclude(pk=allocation.pk).exists():
            raise ValueError("This strategy version already has a Paper deployment. Choose another version.")
        StrategyDeploymentService.validate_snapshot(version.config_snapshot, scope)
        from instruments.services import InstrumentResolver
        old_bindings = {(item['route_id'], item['leg_id']): (InstrumentResolver.input_bindings(item), item.get('contract_selection'))
                        for item in allocation.deployed_version.config_snapshot['watchlist_instruments']}
        new_bindings = {(item['route_id'], item['leg_id']): (InstrumentResolver.input_bindings(item), item.get('contract_selection'))
                        for item in version.config_snapshot['watchlist_instruments']}
        if any(old_bindings.get(identity) != new_bindings.get(identity)
               for identity in positions.values_list('route_id', 'leg_id')):
            raise ValueError('Close positions before changing their signal or traded instrument.')
        # An existing position belongs to its captured occurrence. Applying a
        # different setup would replace the meaning of its protection values.
        if positions.exists() and any(group.get('setup') for snapshot in
                (allocation.deployed_version.config_snapshot, version.config_snapshot)
                for group in snapshot.get('rule_groups', []) if group.get('is_active', True)):
            raise ValueError('Close positions before changing a version that uses captured setup values.')
        active_statuses = ['PENDING', 'PLACED', 'PARTIAL_FILL', 'UNKNOWN']
        if orders.filter(status__in=active_statuses).exists():
            raise ValueError('Wait for outstanding orders to settle before changing the version.')
        if scope == 'paper':
            from commercial.usage import require_inventory_capacity
            require_inventory_capacity(user, paper_snapshot=version.config_snapshot, paper_allocation=allocation)
        allocation.deployed_version = version
        allocation.save(update_fields=['deployed_version', 'updated_at'])
        for session in sessions:
            request_session_refresh(scope, session)
        return allocation

    @staticmethod
    def validate_strategy_lifecycle(strategy):
        """Reject status changes while any deployment is running or paused."""
        from paper_trading.models import PaperTradingSession
        from live_trading.models import TradingSession

        paper_count = PaperTradingSession.objects.filter(strategy=strategy, status__in=['RUNNING', 'PAUSED', 'STOPPING', 'ERROR']).count()
        live_count = TradingSession.objects.filter(strategy=strategy, status__in=['RUNNING', 'PAUSED', 'STOPPING', 'ERROR']).count()
        if paper_count or live_count:
            modes = []
            if paper_count:
                modes.append(f'{paper_count} paper')
            if live_count:
                modes.append(f'{live_count} live')
            raise ValueError(
                f"Cannot change strategy status while {' and '.join(modes)} session(s) are running or paused. "
                'Stop those sessions first.'
            )
