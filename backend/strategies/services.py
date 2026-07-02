import logging
from django.db import transaction
from .models import Strategy, StrategyVersion, EntryOrderConfig, ExitOrderConfig, ReEntryRule
from .serializers import StrategyDetailSerializer
from risk_management.models import PositionSizingRule, StrategyAutoDisable
from rules_engine.models import RuleGroup, Rule, StopLossRule, TargetRule, TimeRule, SpecialEventFilter
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

            if 'reentry_rule' in snapshot:
                StrategySnapshotService._restore_reentry_rule(strategy, snapshot['reentry_rule'])
                
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
                ind_type = rule.get('indicator_type')
                if ind_type:
                    # Common params
                    params = rule.get('params', {}) or {}
                    for p_name, p_val in params.items():
                        if isinstance(p_val, (int, float)) and not isinstance(p_val, bool):
                            tunables.append({
                                'label': f"{group_name} - {ind_type} {p_name}",
                                'path': f"rule_groups.{g_idx}.rules.{r_idx}.params.{p_name}",
                                'current_value': p_val
                            })
                    # Threshold value
                    threshold = rule.get('value')
                    if threshold is not None:
                        tunables.append({
                            'label': f"{group_name} - {ind_type} Threshold",
                            'path': f"rule_groups.{g_idx}.rules.{r_idx}.value",
                            'current_value': float(threshold) if isinstance(threshold, (int, float)) else threshold
                        })
                
                # Compare To Indicator
                compare_ind = rule.get('compare_to_indicator')
                if compare_ind:
                    c_params = rule.get('compare_to_params', {}) or {}
                    for p_name, p_val in c_params.items():
                        if isinstance(p_val, (int, float)) and not isinstance(p_val, bool):
                            tunables.append({
                                'label': f"{group_name} - Comp {compare_ind} {p_name}",
                                'path': f"rule_groups.{g_idx}.rules.{r_idx}.compare_to_params.{p_name}",
                                'current_value': p_val
                            })

            # Stop Loss Rules
            sl_rules = group.get('stop_loss_rules', [])
            for r_idx, rule in enumerate(sl_rules):
                sl_type = rule.get('sl_type', 'SL')
                prefix = f"{group_name} SL ({sl_type})"
                # Fixed percentage
                val = rule.get('fixed_percentage')
                if val is not None:
                    tunables.append({
                        'label': f"{prefix} %",
                        'path': f"rule_groups.{g_idx}.stop_loss_rules.{r_idx}.fixed_percentage",
                        'current_value': float(val)
                    })
                # Fixed points
                val = rule.get('fixed_points')
                if val is not None:
                    tunables.append({
                        'label': f"{prefix} pts",
                        'path': f"rule_groups.{g_idx}.stop_loss_rules.{r_idx}.fixed_points",
                        'current_value': float(val)
                    })
                # Indicator Params
                params = rule.get('indicator_params', {}) or {}
                for p_name, p_val in params.items():
                    if isinstance(p_val, (int, float)):
                        tunables.append({
                            'label': f"{prefix} {p_name}",
                            'path': f"rule_groups.{g_idx}.stop_loss_rules.{r_idx}.indicator_params.{p_name}",
                            'current_value': p_val
                        })
                # Trailing
                val = rule.get('trailing_value')
                if val is not None:
                    tunables.append({
                        'label': f"{prefix} Trailing Val",
                        'path': f"rule_groups.{g_idx}.stop_loss_rules.{r_idx}.trailing_value",
                        'current_value': float(val)
                    })
            
            # Target Rules
            target_rules = group.get('target_rules', [])
            for r_idx, rule in enumerate(target_rules):
                tgt_type = rule.get('target_type', 'Tgt')
                prefix = f"{group_name} Target ({tgt_type})"
                # Fixed percentage
                val = rule.get('fixed_percentage')
                if val is not None:
                    tunables.append({
                        'label': f"{prefix} %",
                        'path': f"rule_groups.{g_idx}.target_rules.{r_idx}.fixed_percentage",
                        'current_value': float(val)
                    })
                val = rule.get('fixed_points')
                if val is not None:
                    tunables.append({
                        'label': f"{prefix} pts",
                        'path': f"rule_groups.{g_idx}.target_rules.{r_idx}.fixed_points",
                        'current_value': float(val)
                    })
                # Risk reward
                val = rule.get('risk_reward_ratio')
                if val is not None:
                    tunables.append({
                        'label': f"{prefix} RR Ratio",
                        'path': f"rule_groups.{g_idx}.target_rules.{r_idx}.risk_reward_ratio",
                        'current_value': float(val)
                    })
                # Indicator Params
                params = rule.get('indicator_params', {}) or {}
                for p_name, p_val in params.items():
                    if isinstance(p_val, (int, float)):
                        tunables.append({
                            'label': f"{prefix} {p_name}",
                            'path': f"rule_groups.{g_idx}.target_rules.{r_idx}.indicator_params.{p_name}",
                            'current_value': p_val
                        })

        return tunables

    @staticmethod
    def _serialize_strategy(strategy):
        """
        Constructs a clean JSON dictionary of the strategy state.
        Uses DRF serializers where appropriate but ensures flattened structure for snapshot.
        """
        # We can re-use the detail serializer but might need more specific handling
        # Using the detail serializer is a good start as it includes most things
        from .serializers import StrategyDetailSerializer
        # We need to ensure deep nested fields like rules are included fully
        # The default DetailSerializer might be read_only or flattened differently
        
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
        for rel_name in ('entry_order_config', 'exit_order_config', 'reentry_rule', 'time_rule', 'special_event_filter', 'position_sizing_rule'):
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
            g_data = StrategySnapshotService._model_to_dict(group, exclude=['id', 'strategy', 'created_at', 'updated_at', 'rules', 'stop_loss_rules', 'target_rules'])
            
            # Rules
            g_data['rules'] = [StrategySnapshotService._model_to_dict(r, exclude=['id', 'rule_group', 'created_at', 'updated_at']) for r in group.rules.all()]
            
            # Stop Losses
            g_data['stop_loss_rules'] = [StrategySnapshotService._model_to_dict(sl, exclude=['id', 'rule_group', 'created_at', 'updated_at']) for sl in group.stop_loss_rules.all()]
            
            # Targets
            g_data['target_rules'] = [StrategySnapshotService._model_to_dict(t, exclude=['id', 'rule_group', 'created_at', 'updated_at']) for t in group.target_rules.all()]
            
            groups.append(g_data)
        
        data['rule_groups'] = groups
        return data

    @staticmethod
    def _model_to_dict(instance, exclude=None):
        from django.forms.models import model_to_dict
        d = model_to_dict(instance, exclude=exclude)
        # Handle decimal/time/date serialization if needed (DRF JSONRenderer handles it usually, but raw model_to_dict might not for JSONField storage)
        # JSONField in model will handle basic types. Decimal might need casting to string or float.
        # For simplicity, we assume Django's JSONEncoder will handle it or we cast decimals.
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
    def _restore_reentry_rule(strategy, data):
        ReEntryRule.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_exit_config(strategy, data):
        ExitOrderConfig.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_position_sizing_rule(strategy, data):
        PositionSizingRule.objects.update_or_create(strategy=strategy, defaults=data)

    @staticmethod
    def _restore_rule_group(strategy, group_data):
        rules_data = group_data.pop('rules', [])
        sl_data = group_data.pop('stop_loss_rules', [])
        target_data = group_data.pop('target_rules', [])
        
        # Create Group
        group = RuleGroup.objects.create(strategy=strategy, **group_data)
        
        # Create Nested Rules
        for r_data in rules_data:
            Rule.objects.create(rule_group=group, **r_data)
            
        for sl_info in sl_data:
            StopLossRule.objects.create(rule_group=group, **sl_info)
            
        for t_info in target_data:
            TargetRule.objects.create(rule_group=group, **t_info)

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
