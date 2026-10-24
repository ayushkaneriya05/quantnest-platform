import logging
from copy import deepcopy
from django.db import transaction
from .models import Strategy, StrategyVersion, StrategyTag, EntryOrderConfig, ExitOrderConfig
from rules_engine.models import PositionSizingRule, RuleGroup, Rule, TimeRule
from instruments.models import WatchlistInstrument
from execution.order_reports import ACTIVE

logger = logging.getLogger(__name__)

class StrategySnapshotService:
    """
    Service to handle strategy versioning: snapshotting and rolling back.
    """

    @staticmethod
    def validate_config_snapshot(snapshot):
        """Validate that config snapshot has all required fields."""
        if not isinstance(snapshot, dict):
            raise ValueError('Strategy configuration must be an object.')
        required_fields = [
            'name', 'strategy_type', 'market_type', 'exchange', 'instrument_type',
            'entry_order_config', 'exit_order_config', 'rule_groups', 'watchlist_instruments',
            'time_rule', 'position_sizing_rule'
        ]
        missing = [field for field in required_fields if field not in snapshot]
        if missing:
            raise ValueError(f"Config snapshot missing required fields: {missing}")
        objects = ('entry_order_config', 'exit_order_config', 'time_rule', 'position_sizing_rule')
        if any(not isinstance(snapshot[field], dict) for field in objects):
            raise ValueError('Order, time and sizing configurations must be objects.')
        if any(not isinstance(snapshot[field], list) for field in ('rule_groups', 'watchlist_instruments')):
            raise ValueError('Rules and instruments must be lists.')
        if any(not isinstance(group, dict) or not isinstance(group.get('rules', []), list) or
                any(not isinstance(rule, dict) for rule in group.get('rules', [])) for group in snapshot['rule_groups']):
            raise ValueError('Each rule group must contain a list of rule objects.')
        return True

    @staticmethod
    @transaction.atomic
    def create_snapshot(strategy, user=None, change_notes=None, *, config_snapshot=None):
        """
        Creates a new version snapshot of the strategy.
        """
        try:
            # 1. Serialize the full strategy state
            # We use specific serializers or manual dict construction to ensure deep nesting is captured
            strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
            snapshot = (StrategySnapshotService._serialize_strategy(strategy)
                        if config_snapshot is None else deepcopy(config_snapshot))
            
            # 2. Validate snapshot completeness
            StrategySnapshotService.validate_config_snapshot(snapshot)
            
            # 3. Determine version number
            last_version = strategy.versions.order_by('-version_number').first()
            next_version = (last_version.version_number + 1) if last_version else 1
            
            # 4. Save Version
            version = StrategyVersion.objects.create(
                strategy=strategy,
                version_number=next_version,
                config_snapshot=snapshot,
                change_notes=change_notes,
                created_by=user
            )
            from audit.services import AuditService
            AuditService.configuration_changed(strategy, last_version.config_snapshot if last_version else {}, snapshot, version)
            return version
        except Exception as e:
            logger.error(f"Error creating snapshot for strategy {strategy.id}: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def restore_version(strategy, version_id):
        """
        Restores the strategy to a specific version.
        WARNING: This is a destructive operation for the current configuration.
        """
        try:
            version = StrategyVersion.objects.get(id=version_id, strategy=strategy)
            snapshot = deepcopy(version.config_snapshot)
            StrategySnapshotService.validate_config_snapshot(snapshot)
            strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
            auto_version_enabled = strategy.auto_version_enabled
            strategy.auto_version_enabled = False
            
            # 1. Restore Strategy Base Fields
            strategy.name = snapshot.get('name', strategy.name)
            strategy.description = snapshot.get('description', strategy.description)
            strategy.strategy_type = snapshot.get('strategy_type', strategy.strategy_type)
            strategy.market_type = snapshot.get('market_type', strategy.market_type)
            strategy.exchange = snapshot.get('exchange', strategy.exchange)
            strategy.instrument_type = snapshot.get('instrument_type', strategy.instrument_type)
            strategy.save()
            strategy.tags.set([StrategyTag.objects.get_or_create(name=name)[0] for name in snapshot.get('tags', [])])

            # 2. Restore 1:1 Configs (Update in place)
            if 'time_rule' in snapshot:
                StrategySnapshotService._restore_time_rule(strategy, snapshot['time_rule'])
                
            if 'entry_order_config' in snapshot:
                StrategySnapshotService._restore_entry_config(strategy, snapshot['entry_order_config'])


                
            if 'exit_order_config' in snapshot:
                StrategySnapshotService._restore_exit_config(strategy, snapshot['exit_order_config'])

            if 'position_sizing_rule' in snapshot:
                StrategySnapshotService._restore_position_sizing_rule(strategy, snapshot['position_sizing_rule'])
                
            # 3. Restore Rule Groups (Delete all existing and recreate)
            # This is safer than trying to diff/update heavily nested structures
            strategy.rule_groups.all().delete()
            
            if 'rule_groups' in snapshot:
                for group_data in snapshot['rule_groups']:
                    StrategySnapshotService._restore_rule_group(strategy, group_data)

            # 5. Restore watchlist instruments
            if 'watchlist_instruments' in snapshot:
                StrategySnapshotService._restore_watchlist(strategy, snapshot['watchlist_instruments'])
            
            # 4. Create a new version to represent this rollback state
            # This ensures the "Current" version in history matches the restored state
            strategy.auto_version_enabled = auto_version_enabled
            strategy.save(update_fields=['auto_version_enabled', 'updated_at'])
            StrategySnapshotService.create_snapshot(
                strategy, user=strategy.user, 
                change_notes=f"Rollback to version {version.version_number}"
            )

            return strategy
        except StrategyVersion.DoesNotExist:
            raise ValueError("Version not found")
        except Exception as e:
            logger.error(f"Error restoring version {version_id} for strategy {strategy.id}: {str(e)}")
            raise


    @staticmethod
    def _serialize_strategy(strategy):
        """
        Constructs a clean JSON dictionary of the strategy state.
        Uses DRF serializers where appropriate but ensures flattened structure for snapshot.
        """
      
        # Let's build a custom robust dict
        data = {
            'id': strategy.id,
            'user_id': strategy.user_id,
            'name': strategy.name,
            'description': strategy.description,
            'strategy_type': strategy.strategy_type,
            'market_type': strategy.market_type,
            'exchange': strategy.exchange,
            'instrument_type': strategy.instrument_type,
            'status': strategy.status,
            'visibility': strategy.visibility,
            'auto_version_enabled': strategy.auto_version_enabled,
            'paper_trading_enabled': strategy.paper_trading_enabled,
            'live_trading_enabled': strategy.live_trading_enabled,
            'tags': list(strategy.tags.order_by('name').values_list('name', flat=True)),
        }

        for rel_name in ('entry_order_config', 'exit_order_config', 'time_rule', 'position_sizing_rule'):
            rel_obj = getattr(strategy, rel_name)
            data[rel_name] = StrategySnapshotService._model_to_dict(rel_obj, exclude=['id', 'strategy', 'created_at', 'updated_at'])

        # Watchlist instruments and execution routes
        watchlist_data = []
        for wi in strategy.watchlist_instruments.select_related('instrument').prefetch_related('execution_routes').order_by('instrument_id'):
            wi_dict = {'instrument_id': wi.instrument_id, 'instrument_symbol': wi.instrument.sym_ticker, 'instrument_name': wi.instrument.name}
            
            routes_data = []
            for route in sorted(wi.execution_routes.all(), key=lambda item: item.pk):
                routes_data.append(StrategySnapshotService._model_to_dict(
                    route, 
                    exclude=['id', 'watchlist_instrument', 'created_at', 'updated_at']
                ))
                
            if routes_data:
                wi_dict['execution_routes'] = routes_data
                
            watchlist_data.append(wi_dict)
            
        data['watchlist_instruments'] = watchlist_data

        # Rule Groups (Deep nesting)
        groups = []
        for group in strategy.rule_groups.prefetch_related('rules').order_by('rule_type', 'priority', 'id'):
            g_data = StrategySnapshotService._model_to_dict(group, exclude=['id', 'strategy', 'created_at', 'updated_at', 'rules'])
            
            # Rules
            g_data['rules'] = [StrategySnapshotService._model_to_dict(r, exclude=['id', 'rule_group', 'created_at', 'updated_at']) for r in sorted(group.rules.all(), key=lambda item: item.pk)]
            
            groups.append(g_data)
        
        data['rule_groups'] = groups
        return data

    @staticmethod
    def _model_to_dict(instance, exclude=None):
        from django.forms.models import model_to_dict
        d = model_to_dict(instance, exclude=exclude)

        for key, value in d.items():
            import decimal
            import datetime
            if isinstance(value, decimal.Decimal):
                d[key] = float(value) # or str(value)
            elif isinstance(value, (datetime.time, datetime.date, datetime.datetime)):
                d[key] = value.isoformat()
        return d

    @staticmethod
    def _restore_time_rule(strategy, data):
        TimeRule.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_entry_config(strategy, data):
        fields = {field.name for field in EntryOrderConfig._meta.fields} - {'id', 'strategy', 'created_at', 'updated_at'}
        EntryOrderConfig.objects.update_or_create(strategy=strategy, defaults={key: value for key, value in data.items() if key in fields})

    @staticmethod
    def _restore_exit_config(strategy, data):
        ExitOrderConfig.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_position_sizing_rule(strategy, data):
        PositionSizingRule.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_rule_group(strategy, group_data):
        rules_data = group_data.pop('rules', [])
        
        # Create Group
        group = RuleGroup.objects.create(strategy=strategy, **group_data)
        
        # Create Nested Rules
        for r_data in rules_data:
            Rule.objects.create(rule_group=group, **r_data)

    @staticmethod
    def _restore_watchlist(strategy, watchlist_data):
        """Restore the complete selection; fail if a saved instrument is unavailable."""
        from instruments.models import Instrument, ExecutionRoute
        ids = {item['instrument_id'] for item in watchlist_data}
        instruments = Instrument.objects.in_bulk(ids)
        missing = ids - set(instruments)
        if missing:
            raise ValueError(f"Saved instruments are unavailable: {sorted(missing)}.")
        strategy.watchlist_instruments.all().delete()
        for item in watchlist_data:
            watch = WatchlistInstrument.objects.create(strategy=strategy, instrument=instruments[item['instrument_id']])
            for route in item.get('execution_routes', []):
                fields = {field.name for field in ExecutionRoute._meta.fields} - {'id', 'watchlist_instrument', 'created_at', 'updated_at'}
                values = {key: value for key, value in route.items() if key in fields}
                for field in ExecutionRoute._meta.fields:
                    if field.is_relation and field.name in values:
                        values[field.attname] = values.pop(field.name)
                ExecutionRoute.objects.create(watchlist_instrument=watch, **values)


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
        from instruments.serializers import ExecutionRouteSerializer
        from rules_engine.serializers import TimeRuleSerializer, RuleSerializer, RuleGroupSerializer
        from rules_engine.serializers import PositionSizingRuleSerializer
        from .serializers import EntryOrderConfigSerializer, ExitOrderConfigSerializer
        from rest_framework.exceptions import ValidationError
        StrategySnapshotService.validate_config_snapshot(snapshot)
        instruments = InstrumentResolver.validate_execution_snapshot(snapshot)
        def validate(serializer_class, data):
            serializer = serializer_class(data=data, partial=True)
            for field in ('strategy', 'rule_group'):
                if field in serializer.fields:
                    serializer.fields[field].read_only = True
            serializer.is_valid(raise_exception=True)
            return serializer.validated_data
        try:
            for name, serializer in (('time_rule', TimeRuleSerializer),
                    ('entry_order_config', EntryOrderConfigSerializer),
                    ('exit_order_config', ExitOrderConfigSerializer),
                    ('position_sizing_rule', PositionSizingRuleSerializer)):
                validate(serializer, snapshot[name])
            from common.enums import InstrumentType
            if (snapshot['strategy_type'] != 'INTRADAY' and snapshot['entry_order_config'].get('entry_side') == 'SELL'
                    and any(item.instrument_type == InstrumentType.STOCK for item in instruments.values())):
                raise ValueError('Stock short entries require an Intraday strategy. Delivery execution does not include stock borrowing.')
            for watch in snapshot['watchlist_instruments']:
                for route in watch.get('execution_routes', []):
                    validate(ExecutionRouteSerializer, route)
            active = [group for group in snapshot['rule_groups'] if group.get('is_active', True)]
            entries = [group for group in active if group.get('rule_type') == 'ENTRY']
            if not entries or any(not any(rule.get('is_active', True) for rule in group.get('rules', [])) for group in entries):
                raise ValueError('The selected version needs complete active entry rules.')
            if mode == 'live' and not any(group.get('rule_type') == 'STOP_LOSS' and
                    any(rule.get('is_active', True) for rule in group.get('rules', [])) for group in active):
                raise ValueError('The selected live version needs an active stop-loss rule.')
            for group in active:
                validate(RuleGroupSerializer, group)
                for rule in group.get('rules', []):
                    if rule.get('is_active', True):
                        serializer = RuleSerializer(data=rule, context={'rule_type': group['rule_type']})
                        serializer.fields['rule_group'].read_only = True
                        serializer.is_valid(raise_exception=True)
            from marketdata.calendar import MarketSessionCalendar
            from execution.compiler import compile_strategy
            markets = set()
            for watch in snapshot['watchlist_instruments']:
                instrument_id, side, _ = InstrumentResolver.resolve(watch,
                    snapshot['entry_order_config']['entry_side'], snapshot['position_sizing_rule'])
                instrument = instruments[instrument_id]
                markets.add((instrument.exchange, instrument.segment, side))
            for exchange, segment, side in markets:
                config = deepcopy(snapshot)
                config['entry_order_config']['entry_side'] = side
                compile_strategy(config, 0, calendar=MarketSessionCalendar.for_exchange(exchange, segment))
        except ValidationError as exc:
            from backend.middleware.api_responses import error_envelope
            message = error_envelope(exc.detail, 400)['message']
            raise ValueError(f'Invalid selected version: {message}') from None

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
        identities = {int(item['instrument_id']) for item in version.config_snapshot['watchlist_instruments']}
        if positions.exclude(instrument_id__in=identities).exists():
            raise ValueError('Close positions before removing their instruments from the deployed version.')
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
