"""
Views for the strategies app.
"""
from rest_framework import viewsets, status, permissions
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from brokers.models import BrokerCredential
from live_trading.services import LiveExecutionService
from rules_engine.models import PositionSizingRule, TimeRule, RuleGroup, Rule
from instruments.models import WatchlistInstrument, ExecutionRoute
from .models import Strategy, StrategyTag, EntryOrderConfig, ExitOrderConfig, StrategyVersion
from .serializers import (
    StrategyListSerializer, StrategyDetailSerializer, StrategyCreateSerializer,
    StrategyVersionSerializer, StrategyTagSerializer,
    EntryOrderConfigSerializer, ExitOrderConfigSerializer
)
from .services import StrategySnapshotService, StrategyDeploymentService


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
            'user', 'entry_order_config', 'exit_order_config', 'position_sizing_rule'
        ).prefetch_related('tags')

    def get_serializer_class(self):
        if self.action == 'list':
            return StrategyListSerializer
        elif self.action == 'create':
            return StrategyCreateSerializer
        return StrategyDetailSerializer

    def destroy(self, request, *args, **kwargs):
        """Delete a strategy, blocking if it has associated data."""
        from django.core.exceptions import ValidationError

        strategy = self.get_object()
        try:
            strategy.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            # Check what data exists for structured response
            has_paper = (
                strategy.paper_sessions.exists()
                or strategy.capital_allocations.exists()
                or strategy.paper_positions.exists()
                or strategy.paper_orders.exists()
                or strategy.paper_trades.exists()
            )
            has_live = (
                strategy.live_sessions.exists()
                or strategy.live_allocations.exists()
                or strategy.live_positions.exists()
                or strategy.live_orders.exists()
                or strategy.live_trades.exists()
            )
            has_backtest = strategy.backtest_runs.exists()
            return Response(
                {
                    'error': str(e.message),
                    'has_paper_data': has_paper,
                    'has_live_data': has_live,
                    'has_backtest_data': has_backtest,
                    'suggestion': 'archive',
                },
                status=status.HTTP_409_CONFLICT,
            )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def clone(self, request, pk=None):
        """Clone an existing strategy."""
        original = self.get_object()
        from commercial.usage import require_inventory_capacity
        require_inventory_capacity(request.user, strategies=1)

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
            paper_trading_enabled=original.paper_trading_enabled,
            live_trading_enabled=original.live_trading_enabled,
        )
        new_strategy.tags.set(original.tags.all())

        def copy_fields(instance, excluded):
            return {
                field.attname: getattr(instance, field.attname)
                for field in instance._meta.concrete_fields
                if field.name not in excluded and field.primary_key is False
            }

        for relation_name, model in (
            ('entry_order_config', EntryOrderConfig),
            ('exit_order_config', ExitOrderConfig),
            ('position_sizing_rule', PositionSizingRule),
            ('time_rule', TimeRule),
        ):
            model.objects.update_or_create(
                strategy=new_strategy,
                defaults=copy_fields(getattr(original, relation_name),
                                     {'strategy', 'created_at', 'updated_at'}),
            )

        for group in original.rule_groups.prefetch_related('rules'):
            cloned_group = RuleGroup.objects.create(
                strategy=new_strategy,
                **copy_fields(group, {'id', 'strategy', 'created_at', 'updated_at'}),
            )
            for rule in group.rules.all():
                Rule.objects.create(
                    rule_group=cloned_group,
                    **copy_fields(rule, {'id', 'rule_group', 'created_at', 'updated_at'}),
                )

        for watched in original.watchlist_instruments.prefetch_related('execution_routes'):
            cloned_watch = WatchlistInstrument.objects.create(strategy=new_strategy, instrument_id=watched.instrument_id)
            for route in watched.execution_routes.all():
                ExecutionRoute.objects.create(
                    watchlist_instrument=cloned_watch,
                    **copy_fields(route, {'id', 'watchlist_instrument', 'created_at', 'updated_at'}),
                )

        # The creation signal records defaults; replace that snapshot with the cloned config.
        new_strategy.versions.all().delete()
        StrategySnapshotService.create_snapshot(new_strategy, user=request.user, change_notes=f'Cloned from {original.name}')

        serializer = StrategyDetailSerializer(new_strategy, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def activate(self, request, pk=None):
        """Activate a draft or paused strategy."""
        strategy = Strategy.objects.select_for_update().get(pk=pk, user=request.user)
        if strategy.status == 'ARCHIVED':
            return Response({'error': 'Unarchive this strategy before activating it.'}, status=status.HTTP_400_BAD_REQUEST)
        if strategy.status != 'ACTIVE':
            try:
                StrategyDeploymentService.validate_strategy_lifecycle(strategy)
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)
            strategy.status = 'ACTIVE'
            strategy.save(update_fields=['status', 'updated_at'])
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='deploy-paper')
    def deploy_paper(self, request, pk=None):
        strategy = self.get_object()
        from rest_framework.fields import DecimalField, IntegerField
        from decimal import Decimal
        from paper_trading.services import PaperExecutionService
        from paper_trading.serializers import PaperTradingSessionSerializer
        from paper_trading.models import PaperAccount
        amount = DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01")).run_validation(
            request.data.get("allocation_amount")
        )
        version_id = IntegerField(min_value=1).run_validation(request.data.get("version_id"))
        try:
            version = StrategyVersion.objects.get(pk=version_id, strategy=strategy)
            session = PaperExecutionService.deploy_session(
                user=request.user, strategy=strategy, version=version, allocation_amount=amount,
                slippage_pct=request.data.get("slippage_pct", 0),
                charge_profile_id=request.data.get("charge_profile"),
                include_charges=request.data.get("include_charges", True),
            )
            session.account = PaperAccount.objects.with_totals().get(pk=session.account_id)
            return Response(PaperTradingSessionSerializer(session).data, status=status.HTTP_201_CREATED)
        except StrategyVersion.DoesNotExist:
            return Response({"error": "Select a saved version of this strategy."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='deploy-live')
    def deploy_live(self, request, pk=None):
        from rest_framework.fields import DecimalField, IntegerField
        from decimal import Decimal
        strategy = self.get_object()
        broker_id = IntegerField(min_value=1).run_validation(request.data.get("broker_credential"))
        version_id = IntegerField(min_value=1).run_validation(request.data.get("version_id"))
        amount = DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0.01")).run_validation(
            request.data.get("allocation_amount")
        )
        try:
            credential = BrokerCredential.objects.get(pk=broker_id, user=request.user, is_verified=True)
            version = StrategyVersion.objects.get(pk=version_id, strategy=strategy)
            session = LiveExecutionService.deploy_session(
                user=request.user, strategy=strategy, version=version,
                allocation_amount=amount, broker_credential=credential,
            )
            return Response({
                "session_id": session.pk, "allocation_id": session.allocation_id,
                "broker_credential": session.broker_credential_id, "status": session.status,
                "message": "Strategy deployed to Live trading",
            }, status=status.HTTP_201_CREATED)
        except BrokerCredential.DoesNotExist:
            return Response({"error": "Select your own verified broker account."}, status=status.HTTP_400_BAD_REQUEST)
        except StrategyVersion.DoesNotExist:
            return Response({"error": "Select a saved version of this strategy."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def pause(self, request, pk=None):
        """Pause strategy-level activation only when no execution session exists."""
        strategy = Strategy.objects.select_for_update().get(pk=pk, user=request.user)
        if strategy.status != 'ACTIVE':
            return Response({'error': 'Only active strategies can be paused.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            StrategyDeploymentService.validate_strategy_lifecycle(strategy)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)
        strategy.status = 'PAUSED'
        strategy.save(update_fields=['status', 'updated_at'])
        return Response(StrategyDetailSerializer(strategy, context={'request': request}).data)

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
        versions = list(strategy.versions.select_related('created_by').order_by('-version_number'))
        previous = {version.pk: versions[index + 1] if index + 1 < len(versions) else None for index, version in enumerate(versions)}
        serializer = StrategyVersionSerializer(versions, many=True, context={'previous_versions': previous})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def archive(self, request, pk=None):
        """Archive a strategy."""
        strategy = Strategy.objects.select_for_update().get(pk=pk, user=request.user)
        try:
            StrategyDeploymentService.validate_strategy_lifecycle(strategy)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)
        strategy.status = 'ARCHIVED'
        strategy.save(update_fields=['status', 'updated_at'])
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def unarchive(self, request, pk=None):
        """Unarchive a strategy back to draft."""
        strategy = Strategy.objects.select_for_update().get(pk=pk, user=request.user)
        if strategy.status == 'ARCHIVED':
            try:
                StrategyDeploymentService.validate_strategy_lifecycle(strategy)
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_409_CONFLICT)
            strategy.status = 'DRAFT'
            strategy.save()
        serializer = StrategyDetailSerializer(strategy, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='halt-and-archive')
    def halt_and_archive(self, request, pk=None):
        """Close all open positions and archive the strategy.

        This is a destructive action: all open live positions are closed
        at market price, and the strategy status is set to ARCHIVED.
        """
        strategy = self.get_object()

        from paper_trading.models import PaperTradingSession
        if PaperTradingSession.objects.filter(strategy=strategy, status__in=['RUNNING', 'PAUSED', 'STOPPING', 'ERROR']).exists():
            return Response(
                {'error': 'Stop all running or paused paper sessions before archiving this strategy.'},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            from .services import StrategyLifecycleService
            result = StrategyLifecycleService.halt_and_archive(strategy, request.user)
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except RuntimeError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_409_CONFLICT
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EntryOrderConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for entry order configuration."""
    serializer_class = EntryOrderConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        return EntryOrderConfig.objects.filter(strategy__user=self.request.user)



class ExitOrderConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for exit order configuration."""
    serializer_class = ExitOrderConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        return ExitOrderConfig.objects.filter(strategy__user=self.request.user)
