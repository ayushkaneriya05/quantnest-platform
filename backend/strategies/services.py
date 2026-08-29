import logging
from django.db import transaction
from .models import Strategy, StrategyVersion, EntryOrderConfig, ExitOrderConfig
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
    def create_snapshot(strategy, user=None, change_notes=None):
        """
        Creates a new version snapshot of the strategy.
        """
        try:
            # 1. Serialize the full strategy state
            # We use specific serializers or manual dict construction to ensure deep nesting is captured
            snapshot = StrategySnapshotService._serialize_strategy(strategy)
            
            # 2. Determine version number
            last_version = strategy.versions.order_by('-version_number').first()
            next_version = (last_version.version_number + 1) if last_version else 1
            
            # 3. Save Version
            version = StrategyVersion.objects.create(
                strategy=strategy,
                version_number=next_version,
                config_snapshot=snapshot,
                change_notes=change_notes,
                created_by=user
            )
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
            snapshot = version.config_snapshot
            
            # 1. Restore Strategy Base Fields
            strategy.name = snapshot.get('name', strategy.name)
            strategy.description = snapshot.get('description', strategy.description)
            strategy.strategy_type = snapshot.get('strategy_type', strategy.strategy_type)
            strategy.market_type = snapshot.get('market_type', strategy.market_type)
            strategy.exchange = snapshot.get('exchange', strategy.exchange)
            strategy.instrument_type = snapshot.get('instrument_type', strategy.instrument_type)
            strategy.save()
            
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
            elif 'watchlist_instrument_ids' in snapshot:
                StrategySnapshotService._restore_watchlist(strategy, snapshot['watchlist_instrument_ids'])
            
            # 4. Create a new version to represent this rollback state
            # This ensures the "Current" version in history matches the restored state
            StrategySnapshotService.create_snapshot(
                strategy, 
                change_notes=f"Rollback to version {version.version_number}"
            )

            return strategy
        except StrategyVersion.DoesNotExist:
            raise ValueError("Version not found")
        except Exception as e:
            logger.error(f"Error restoring version {version_id} for strategy {strategy.id}: {str(e)}")
            raise

    @staticmethod
    def extract_tunable_parameters(snapshot):
        """
        Scans strategy config snapshot and returns list of tunable parameters as dict-paths.
        Returns list of {label: str, path: str, current_value: any}
        """
        tunables = []
        
        # 1. Scan Rule Groups -> Rules
        groups = snapshot.get('rule_groups', [])
        for g_idx, group in enumerate(groups):
            group_name = group.get('name') or f"Group {g_idx + 1}"
            
            # Indicator Rules
            rules = group.get('rules', [])
            for r_idx, rule in enumerate(rules):
                ind_type = rule.get('operand_a_type')
                if ind_type:
                    # Common params
                    params = rule.get('operand_a_params', {}) or {}
                    for p_name, p_val in params.items():
                        if isinstance(p_val, (int, float)) and not isinstance(p_val, bool):
                            tunables.append({
                                'label': f"{group_name} - {ind_type} {p_name}",
                                'path': f"rule_groups.{g_idx}.rules.{r_idx}.operand_a_params.{p_name}",
                                'current_value': p_val
                            })
                            
                    # Operand B
                    op_b = rule.get('operand_b_type')
                    if op_b:
                        c_params = rule.get('operand_b_params', {}) or {}
                        for p_name, p_val in c_params.items():
                            if isinstance(p_val, (int, float)) and not isinstance(p_val, bool):
                                tunables.append({
                                    'label': f"{group_name} - Comp {op_b} {p_name}",
                                    'path': f"rule_groups.{g_idx}.rules.{r_idx}.operand_b_params.{p_name}",
                                    'current_value': p_val
                                })

        return tunables

    @staticmethod
    def _serialize_strategy(strategy):
        """
        Constructs a clean JSON dictionary of the strategy state.
        Uses DRF serializers where appropriate but ensures flattened structure for snapshot.
        """
      
        # Let's build a custom robust dict
        data = {
            'name': strategy.name,
            'description': strategy.description,
            'strategy_type': strategy.strategy_type,
            'market_type': strategy.market_type,
            'exchange': strategy.exchange,
            'instrument_type': strategy.instrument_type,
        }

        # 1:1 Relations — use try/except to handle RelatedObjectDoesNotExist
        for rel_name in ('entry_order_config', 'exit_order_config', 'time_rule', 'special_event_filter', 'position_sizing_rule'):
            try:
                rel_obj = getattr(strategy, rel_name)
                if rel_obj is not None:
                    data[rel_name] = StrategySnapshotService._model_to_dict(rel_obj, exclude=['id', 'strategy', 'created_at', 'updated_at'])
            except Exception:
                pass

        data['auto_disable_rules'] = [
            StrategySnapshotService._model_to_dict(rule, exclude=['id', 'strategy', 'created_at', 'updated_at'])
            for rule in strategy.auto_disable_rules.all()
        ]

        # Watchlist instruments and execution routes
        watchlist_data = []
        for wi in strategy.watchlist_instruments.all().prefetch_related('execution_routes'):
            wi_dict = {'instrument_id': wi.instrument_id}
            
            routes_data = []
            for route in wi.execution_routes.all():
                routes_data.append(StrategySnapshotService._model_to_dict(
                    route, 
                    exclude=['id', 'watchlist_instrument', 'created_at', 'updated_at']
                ))
                
            if routes_data:
                wi_dict['execution_routes'] = routes_data
                # Keep singular for older clients if needed
                wi_dict['execution_route'] = routes_data[0]
                
            watchlist_data.append(wi_dict)
            
        data['watchlist_instruments'] = watchlist_data
        data['watchlist_instrument_ids'] = [wi['instrument_id'] for wi in watchlist_data] # Keep for backward compatibility

        # Rule Groups (Deep nesting)
        groups = []
        for group in strategy.rule_groups.all().order_by('priority'):
            g_data = StrategySnapshotService._model_to_dict(group, exclude=['id', 'strategy', 'created_at', 'updated_at', 'rules'])
            
            # Rules
            g_data['rules'] = [StrategySnapshotService._model_to_dict(r, exclude=['id', 'rule_group', 'created_at', 'updated_at']) for r in group.rules.all()]
            
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
        """Restore watchlist instruments and routes from snapshot."""
        from instruments.models import Instrument, WatchlistInstrument, ExecutionRoute
        strategy.watchlist_instruments.all().delete()
        
        # Backward compatibility for old snapshots (list of IDs)
        if isinstance(watchlist_data, list) and (len(watchlist_data) == 0 or isinstance(watchlist_data[0], int)):
            for inst_id in watchlist_data:
                try:
                    instrument = Instrument.objects.get(id=inst_id)
                    WatchlistInstrument.objects.get_or_create(strategy=strategy, instrument=instrument)
                except Instrument.DoesNotExist:
                    pass
            return

        # New format (list of dicts)
        for item in watchlist_data:
            inst_id = item.get('instrument_id')
            try:
                instrument = Instrument.objects.get(id=inst_id)
                wi, _ = WatchlistInstrument.objects.get_or_create(
                    strategy=strategy,
                    instrument=instrument,
                )
                # Restore multiple routes
                routes_data = item.get('execution_routes', [])
                if not routes_data and item.get('execution_route'):
                    routes_data = [item.get('execution_route')]
                    
                for route_data in routes_data:
                    ExecutionRoute.objects.create(
                        watchlist_instrument=wi,
                        **route_data
                    )
            except Instrument.DoesNotExist:
                logger.warning("Watchlist instrument %s not found during restore", inst_id)


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
            )
            
            for _ in range(5):
                LiveExecutionService.sync_orders_from_broker(
                    user,
                    credential=session.broker_credential,
                    force=True,
                )
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
    def _has_static_stop_distance(strategy):
        for group in strategy.rule_groups.filter(rule_type='STOP_LOSS', is_active=True).prefetch_related('rules'):
            for rule in group.rules.filter(is_active=True):
                if rule.operand_a_type in ['POSITION_PNL_POINTS', 'POSITION_PNL_PERCENTAGE', 'TRAILING_PEAK_OFFSET'] and rule.operand_b_type == 'CONSTANT':
                    return True
        return False

    @staticmethod
    def validate_for_deployment(strategy, mode='paper'):
        errors = []
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
        else:
            sizing = strategy.position_sizing_rule

            if sizing.sizing_method == 'RISK_BASED' and not StrategyDeploymentService._has_static_stop_distance(strategy):
                errors.append('Risk-based sizing requires a fixed, trailing, or emergency stop-loss distance.')

        has_stop_loss = strategy.rule_groups.filter(
            rule_type='STOP_LOSS',
            is_active=True,
            rules__is_active=True,
        ).exists()
        if mode == 'live' and not has_stop_loss:
            errors.append('Live deployment requires at least one active stop-loss rule.')

        return errors

    @staticmethod
    def activate_for_deployment(strategy):
        if strategy.status != 'ACTIVE':
            strategy.status = 'ACTIVE'
            strategy.save(update_fields=['status', 'updated_at'])
        return strategy
