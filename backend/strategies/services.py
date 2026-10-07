import logging
from copy import deepcopy
from django.db import transaction
from .models import Strategy, StrategyVersion, StrategyTag, EntryOrderConfig, ExitOrderConfig
from .serializers import StrategyDetailSerializer
from risk_management.models import PositionSizingRule, StrategyAutoDisable
from rules_engine.models import RuleGroup, Rule, TimeRule, SpecialEventFilter
from rules_engine.serializers import RuleGroupSerializer, TimeRuleSerializer, SpecialEventFilterSerializer
from instruments.models import WatchlistInstrument

logger = logging.getLogger(__name__)

class StrategySnapshotService:
    """
    Service to handle strategy versioning: snapshotting and rolling back.
    """

    @staticmethod
    def validate_config_snapshot(snapshot):
        """Validate that config snapshot has all required fields."""
        required_fields = [
            'name', 'strategy_type', 'market_type', 'exchange', 'instrument_type',
            'entry_order_config', 'exit_order_config', 'rule_groups', 'watchlist_instruments',
            'time_rule', 'special_event_filter', 'position_sizing_rule', 'auto_disable_rules'
        ]
        missing = [field for field in required_fields if field not in snapshot]
        if missing:
            raise ValueError(f"Config snapshot missing required fields: {missing}")
        return True

    @staticmethod
    @transaction.atomic
    def create_snapshot(strategy, user=None, change_notes=None):
        """
        Creates a new version snapshot of the strategy.
        """
        try:
            # 1. Serialize the full strategy state
            # We use specific serializers or manual dict construction to ensure deep nesting is captured
            strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
            snapshot = StrategySnapshotService._serialize_strategy(strategy)
            
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
                
            if 'special_event_filter' in snapshot:
                StrategySnapshotService._restore_event_filter(strategy, snapshot['special_event_filter'])
                
            if 'entry_order_config' in snapshot:
                StrategySnapshotService._restore_entry_config(strategy, snapshot['entry_order_config'])


                
            if 'exit_order_config' in snapshot:
                StrategySnapshotService._restore_exit_config(strategy, snapshot['exit_order_config'])

            if 'position_sizing_rule' in snapshot:
                StrategySnapshotService._restore_position_sizing_rule(strategy, snapshot['position_sizing_rule'])
                
            # 3. Restore Rule Groups (Delete all existing and recreate)
            # This is safer than trying to diff/update heavily nested structures
            strategy.rule_groups.all().delete()
            strategy.auto_disable_rules.all().delete()
            
            if 'rule_groups' in snapshot:
                for group_data in snapshot['rule_groups']:
                    StrategySnapshotService._restore_rule_group(strategy, group_data)

            if 'auto_disable_rules' in snapshot:
                for rule_data in snapshot['auto_disable_rules']:
                    StrategySnapshotService._restore_auto_disable_rule(strategy, rule_data)

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

        for rel_name in ('entry_order_config', 'exit_order_config', 'time_rule', 'special_event_filter', 'position_sizing_rule'):
            rel_obj = getattr(strategy, rel_name)
            data[rel_name] = StrategySnapshotService._model_to_dict(rel_obj, exclude=['id', 'strategy', 'created_at', 'updated_at'])

        data['auto_disable_rules'] = [
            StrategySnapshotService._model_to_dict(rule, exclude=['id', 'strategy', 'created_at', 'updated_at'])
            for rule in strategy.auto_disable_rules.order_by('id')
        ]

        # Watchlist instruments and execution routes
        watchlist_data = []
        for wi in strategy.watchlist_instruments.select_related('instrument').prefetch_related('execution_routes').order_by('instrument_id'):
            wi_dict = {'instrument_id': wi.instrument_id, 'instrument_symbol': wi.instrument.symbol, 'instrument_name': wi.instrument.name}
            
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
    def _restore_event_filter(strategy, data):
        SpecialEventFilter.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_entry_config(strategy, data):
        EntryOrderConfig.objects.update_or_create(strategy=strategy, defaults=data)

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
    def _restore_auto_disable_rule(strategy, rule_data):
        StrategyAutoDisable.objects.create(strategy=strategy, **rule_data)

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
                values = dict(route)
                for field in ExecutionRoute._meta.fields:
                    if field.is_relation and field.name in values:
                        values[field.attname] = values.pop(field.name)
                ExecutionRoute.objects.create(watchlist_instrument=watch, **values)


class StrategyLifecycleService:
    @staticmethod
    def halt_and_archive(strategy, user):
        """
        Close all open positions and archive the strategy.
        Returns a dict with status information.
        """
        if strategy.status == 'ARCHIVED':
            raise ValueError('Strategy is already archived')

        from live_trading.models import TradingSession, LivePosition
        from live_trading.services import LiveExecutionService
        from django.utils import timezone
        import time

        active_sessions = list(TradingSession.objects.filter(
            strategy=strategy,
            status__in=['RUNNING', 'PAUSED']
        ).select_related('broker_credential'))

        closed_positions = 0
        open_positions = LivePosition.objects.filter(
            strategy=strategy,
            quantity__gt=0
        ).select_related('instrument', 'broker_credential')

        for position in open_positions:
            session = next(
                (
                    item for item in active_sessions
                    if item.broker_credential_id == position.broker_credential_id
                ),
                active_sessions[0] if active_sessions else None,
            )
            if not session:
                raise ValueError(f"No active live session found to close position {position.id}")

            exit_side = 'SELL' if position.side == 'BUY' else 'BUY'
            order = LiveExecutionService.place_order(
                session=session,
                instrument=position.instrument,
                side=exit_side,
                quantity=position.quantity,
                order_type='MARKET',
                intent="EXIT",
            )
            
            for _ in range(5):
                # Use new BrokerReconciliationService instead of old sync method
                from live_trading.reconciliation_service import BrokerReconciliationService
                reconciliation_service = BrokerReconciliationService(session)
                reconciliation_service.reconcile_orders()
                
                order.refresh_from_db()
                if order.status == 'FILLED':
                    break
                time.sleep(1)
                
            if order.status != 'FILLED':
                raise RuntimeError(
                    f"Close order {order.id} for position {position.id} is {order.status}; archive aborted."
                )
            closed_positions += 1

        for session in active_sessions:
            session.status = 'STOPPED'
            session.ended_at = timezone.now()
            session.save(update_fields=['status', 'ended_at', 'updated_at'])

        strategy.status = 'ARCHIVED'
        strategy.save(update_fields=['status', 'updated_at'])

        return {
            'status': 'archived',
            'sessions_stopped': len(active_sessions),
            'positions_closing': closed_positions,
            'message': f"Strategy '{strategy.name}' archived after closing {closed_positions} live position(s)."
        }


class StrategyDeploymentService:
    @staticmethod
    def validate_for_deployment(strategy, mode='paper'):
        errors = []
        if strategy.status != 'ACTIVE':
            errors.append('Only active strategies can be deployed.')
        mode_flag = 'paper_trading_enabled' if mode == 'paper' else 'live_trading_enabled'
        if not getattr(strategy, mode_flag, False):
            errors.append(f'{mode.title()} trading is disabled for this strategy.')
        if not strategy.watchlist_instruments.exists():
            errors.append('Add at least one instrument to the strategy watchlist.')

        active_entry_groups = strategy.rule_groups.filter(rule_type='ENTRY', is_active=True).prefetch_related('rules')
        if not active_entry_groups.exists():
            errors.append('Add at least one active entry rule group.')
        elif not active_entry_groups.filter(rules__is_active=True).exists():
            errors.append('Every deployable strategy needs at least one active entry rule.')

        empty_active_groups = [
            group.name or f'Group #{group.id}'
            for group in active_entry_groups
            if not group.rules.filter(is_active=True).exists()
        ]
        if empty_active_groups:
            errors.append(f"Remove or complete empty active entry groups: {', '.join(empty_active_groups)}.")

        if not hasattr(strategy, 'position_sizing_rule'):
            errors.append('Configure position sizing before deployment.')

        has_stop_loss = strategy.rule_groups.filter(
            rule_type='STOP_LOSS',
            is_active=True,
            rules__is_active=True,
        ).exists()
        if mode == 'live' and not has_stop_loss:
            errors.append('Live deployment requires at least one active stop-loss rule.')

        return errors

    @staticmethod
    def validate_strategy_lifecycle(strategy):
        """Reject status changes while any deployment is running or paused."""
        from paper_trading.models import PaperTradingSession
        from live_trading.models import TradingSession

        paper_count = PaperTradingSession.objects.filter(strategy=strategy, status__in=['RUNNING', 'PAUSED']).count()
        live_count = TradingSession.objects.filter(strategy=strategy, status__in=['RUNNING', 'PAUSED']).count()
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
