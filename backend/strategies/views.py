"""
Views for the strategies app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from brokers.models import BrokerCredential
from live_trading.services import LiveExecutionService
from paper_trading.services import PortfolioService
from risk_management.models import PositionSizingRule, StrategyAutoDisable
from paper_trading.serializers import PaperAccountSerializer
from .models import Strategy, StrategyVersion, StrategyTag, EntryOrderConfig, ExitOrderConfig, ReEntryRule
from .serializers import (
    StrategyListSerializer, StrategyDetailSerializer, StrategyCreateSerializer,
    StrategyVersionSerializer, StrategyTagSerializer,
    EntryOrderConfigSerializer, ExitOrderConfigSerializer, ReEntryRuleSerializer
)
from .services import StrategySnapshotService


class StrategyTagViewSet(viewsets.ModelViewSet):
    """ViewSet for strategy tags."""
    queryset = StrategyTag.objects.all()
    serializer_class = StrategyTagSerializer
    permission_classes = [permissions.IsAuthenticated]


class StrategyViewSet(viewsets.ModelViewSet):
    """ViewSet for CRUD operations on strategies."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter strategies by current user."""
        return Strategy.objects.filter(user=self.request.user).select_related(
            'user'
        ).prefetch_related('tags')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StrategyListSerializer
        elif self.action == 'create':
            return StrategyCreateSerializer
        return StrategyDetailSerializer

    def _activate_for_deployment(self, strategy):
        update_fields = []
        if strategy.status != 'ACTIVE':
            strategy.status = 'ACTIVE'
            update_fields.append('status')
        if update_fields:
            strategy.save(update_fields=[*update_fields, 'updated_at'])
        return strategy

    def _deployment_errors(self, strategy, mode='paper'):
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
            if sizing.max_daily_trades < 1:
                errors.append('Max daily trades must be at least 1.')
            if sizing.max_open_positions < 1:
                errors.append('Max open positions must be at least 1.')

            if sizing.sizing_method in {'RISK_FIXED', 'RISK_PERCENTAGE'} and not self._has_static_stop_distance(strategy):
                errors.append('Risk-based sizing requires a fixed, trailing, or emergency stop-loss distance.')

        has_stop_loss = strategy.rule_groups.filter(
            rule_type='STOP_LOSS',
            is_active=True,
            stop_loss_rules__is_active=True,
        ).exists()
        if mode == 'live' and not has_stop_loss:
            errors.append('Live deployment requires at least one active stop-loss rule.')

        return errors

    def _has_static_stop_distance(self, strategy):
        for group in strategy.rule_groups.filter(rule_type='STOP_LOSS', is_active=True).prefetch_related('stop_loss_rules'):
            for rule in group.stop_loss_rules.filter(is_active=True):
                if rule.sl_type == 'FIXED_POINTS' and rule.fixed_points and rule.fixed_points > 0:
                    return True
                if rule.sl_type == 'FIXED_PERCENTAGE' and rule.fixed_percentage and rule.fixed_percentage > 0:
                    return True
                if rule.sl_type == 'TRAILING_FIXED' and rule.trailing_value and rule.trailing_value > 0:
                    return True
                if rule.sl_type == 'TRAILING_PERCENTAGE' and rule.trailing_value and rule.trailing_value > 0:
                    return True
                if rule.sl_type == 'EMERGENCY' and rule.emergency_loss_pct and rule.emergency_loss_pct > 0:
                    return True
        return False
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone an existing strategy."""
        original = self.get_object()
        
        # Create new strategy with copied data
        new_strategy = Strategy.objects.create(
            user=request.user,
            name=f"{original.name} (Copy)",
            description=original.description,
            strategy_type=original.strategy_type,
            market_type=original.market_type,
            exchange=original.exchange,
            instrument_type=original.instrument_type,
            visibility='PRIVATE',
            status='DRAFT',
        )
        new_strategy.tags.set(original.tags.all())
        
        # Clone configs
        if hasattr(original, 'entry_order_config'):
            config = original.entry_order_config
            EntryOrderConfig.objects.update_or_create(
                strategy=new_strategy,
                defaults={
                    'entry_side': config.entry_side,
                    'entry_group_operator': config.entry_group_operator,
                    'execution_style': config.execution_style,
                    'price_offset': config.price_offset,
                    'allow_partial_entry': config.allow_partial_entry,
                    'entry_cooldown_seconds': config.entry_cooldown_seconds,
                }
            )

        if hasattr(original, 'reentry_rule'):
            config = original.reentry_rule
            ReEntryRule.objects.update_or_create(
                strategy=new_strategy,
                defaults={
                    'allow_reentry': config.allow_reentry,
                    'reentry_cooldown_seconds': config.reentry_cooldown_seconds,
                    'allow_reverse_entry': config.allow_reverse_entry,
                }
            )

        # Clone exit config
        if hasattr(original, 'exit_order_config'):
            config = original.exit_order_config
            ExitOrderConfig.objects.update_or_create(
                strategy=new_strategy,
                defaults={
                    'stop_loss_group_operator': config.stop_loss_group_operator,
                    'target_group_operator': config.target_group_operator,
                }
            )

        if hasattr(original, 'position_sizing_rule'):
            sizing = original.position_sizing_rule
            PositionSizingRule.objects.update_or_create(
                strategy=new_strategy,
                defaults={
                    'sizing_method': sizing.sizing_method,
                    'fixed_quantity': sizing.fixed_quantity,
                    'capital_percentage': sizing.capital_percentage,
                    'risk_per_trade_amount': sizing.risk_per_trade_amount,
                    'risk_per_trade_percentage': sizing.risk_per_trade_percentage,
                    'max_daily_trades': sizing.max_daily_trades,
                    'max_open_positions': sizing.max_open_positions,
                    'loss_recovery_mode': sizing.loss_recovery_mode,
                    'loss_recovery_multiplier': sizing.loss_recovery_multiplier,
                }
            )

        for auto_disable_rule in original.auto_disable_rules.all():
            StrategyAutoDisable.objects.create(
                strategy=new_strategy,
                name=auto_disable_rule.name,
                trigger_type=auto_disable_rule.trigger_type,
                threshold_value=auto_disable_rule.threshold_value,
                threshold_count=auto_disable_rule.threshold_count,
                auto_reenable=auto_disable_rule.auto_reenable,
                cooldown_hours=auto_disable_rule.cooldown_hours,
                require_manual_review=auto_disable_rule.require_manual_review,
                is_active=auto_disable_rule.is_active,
            )

        serializer = StrategyDetailSerializer(new_strategy, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a draft or paused strategy."""
        strategy = self.get_object()
        if strategy.status in ('DRAFT', 'PAUSED'):
            strategy.status = 'ACTIVE'
            strategy.save()
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='deploy-paper')
    def deploy_paper(self, request, pk=None):
        strategy = self.get_object()
        try:
            errors = self._deployment_errors(strategy, mode='paper')
            if errors:
                return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
            self._activate_for_deployment(strategy)
            if not strategy.paper_trading_enabled:
                strategy.paper_trading_enabled = True
                strategy.save(update_fields=['paper_trading_enabled', 'updated_at'])

            portfolio = PortfolioService.get_or_create_portfolio(request.user)
            account = PortfolioService.ensure_paper_account_for_strategy(portfolio, strategy)
            return Response(
                {
                    'strategy': StrategyDetailSerializer(strategy, context={'request': request}).data,
                    'paper_account': PaperAccountSerializer(account).data,
                    'message': 'Strategy deployed to paper trading',
                }
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='deploy-live')
    def deploy_live(self, request, pk=None):
        strategy = self.get_object()
        broker_credential = None
        broker_credential_id = request.data.get('broker_credential')
        try:
            errors = self._deployment_errors(strategy, mode='live')
            if errors:
                return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
            self._activate_for_deployment(strategy)
            if broker_credential_id:
                broker_credential = BrokerCredential.objects.get(
                    id=broker_credential_id,
                    user=request.user,
                    is_verified=True,
                )
            session = LiveExecutionService.deploy_strategy(
                request.user,
                strategy,
                broker_credential,
                allocation_amount=request.data.get('allocation_amount'),
                allocation_percentage=request.data.get('allocation_percentage'),
            )
            return Response(
                {
                    'strategy': StrategyDetailSerializer(strategy, context={'request': request}).data,
                    'session_id': session.id,
                    'broker_credential': session.broker_credential_id,
                    'status': session.status,
                    'message': 'Strategy deployed to live trading',
                }
            )
        except BrokerCredential.DoesNotExist:
            return Response({'error': 'Selected broker account is not available'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause an active strategy."""
        strategy = self.get_object()
        if strategy.status == 'ACTIVE':
            strategy.status = 'PAUSED'
            strategy.save()
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='create-version')
    def create_version(self, request, pk=None):
        """Create a new version snapshot."""
        strategy = self.get_object()
        notes = request.data.get('notes', '')
        
        try:
            version = StrategySnapshotService.create_snapshot(
                strategy, 
                user=request.user, 
                change_notes=notes
            )
            serializer = StrategyVersionSerializer(version)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """Rollback strategy to a specific version."""
        strategy = self.get_object()
        version_id = request.data.get('version_id')
        
        if not version_id:
            return Response({'error': 'version_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            strategy = StrategySnapshotService.restore_version(strategy, version_id)
            serializer = StrategyDetailSerializer(strategy, context={'request': request})
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get history of versions."""
        strategy = self.get_object()
        versions = strategy.versions.all()
        serializer = StrategyVersionSerializer(versions, many=True)
        return Response(serializer.data)

    def get_object(self):
        """
        Override get_object to ensure config objects exist.
        This handles cases where strategies were created before signals were added.
        """
        obj = super().get_object()
        
        # Ensure EntryOrderConfig exists
        if not hasattr(obj, 'entry_order_config'):
            EntryOrderConfig.objects.create(strategy=obj)
            
        # Ensure ReEntryRule exists
        if not hasattr(obj, 'reentry_rule'):
            ReEntryRule.objects.create(strategy=obj)

        # Ensure ExitOrderConfig exists
        if not hasattr(obj, 'exit_order_config'):
            ExitOrderConfig.objects.create(strategy=obj)
            
        # Refresh to get the new reverse relationships
        obj.refresh_from_db()
        return obj
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a strategy."""
        strategy = self.get_object()
        strategy.status = 'ARCHIVED'
        strategy.save()
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive a strategy back to draft."""
        strategy = self.get_object()
        if strategy.status == 'ARCHIVED':
            strategy.status = 'DRAFT'
            strategy.save()
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='tunable-parameters')
    def tunable_parameters(self, request, pk=None):
        """Get a flat list of all optimizable parameter paths for this strategy."""
        strategy = self.get_object()
        # Serialize snapshot
        snapshot = StrategySnapshotService._serialize_strategy(strategy)
        params = StrategySnapshotService.extract_tunable_parameters(snapshot)
        return Response(params)


class EntryOrderConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for entry order configuration."""
    serializer_class = EntryOrderConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return EntryOrderConfig.objects.filter(strategy__user=self.request.user)


class ReEntryRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for re-entry rules."""
    serializer_class = ReEntryRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ReEntryRule.objects.filter(strategy__user=self.request.user)


class ExitOrderConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for exit order configuration."""
    serializer_class = ExitOrderConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ExitOrderConfig.objects.filter(strategy__user=self.request.user)
