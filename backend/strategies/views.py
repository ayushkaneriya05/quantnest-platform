from common.pagination import StandardPagination
from django.db.models import Count, Q
"""
Views for the strategies app.
"""
from rest_framework import viewsets, status, permissions
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from brokers.models import BrokerCredential
from live_trading.services import LiveExecutionService
from .models import Strategy, StrategyTag, StrategyVersion
from .serializers import (
    StrategyListSerializer, StrategyDetailSerializer, StrategyCreateSerializer,
    StrategyVersionSerializer, StrategyVersionListSerializer, StrategyTagSerializer,
)
from .services import StrategySnapshotService, StrategyDeploymentService


class StrategyTagViewSet(viewsets.ModelViewSet):
    """ViewSet for strategy tags."""
    queryset = StrategyTag.objects.all()
    serializer_class = StrategyTagSerializer
    permission_classes = [permissions.IsAuthenticated]


class StrategyViewSet(viewsets.ModelViewSet):
    pagination_class = StandardPagination
    """ViewSet for CRUD operations on strategies."""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get', 'put'])
    @transaction.atomic
    def definition(self, request, pk=None):
        from .definitions import current_document, revision, validate_definition, compile_preview
        from rest_framework.exceptions import ValidationError
        strategy = self.get_object()
        strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
        current = current_document(strategy)
        if request.method == 'PUT':
            if request.data.get('revision') != revision(current):
                return Response({'detail': 'This strategy changed in another tab. Reload before saving.'}, status=409)
            try:
                document = validate_definition(request.data.get('document'))
                preview = compile_preview(strategy, document)
            except (ValueError, TypeError, KeyError) as exc:
                raise ValidationError(str(exc)) from None
            # No runtime refresh: running sessions continue using their pinned
            # saved version until the user explicitly deploys another version.
            from django.utils import timezone
            strategy.definition = document
            Strategy.objects.filter(pk=strategy.pk).update(definition=document, updated_at=timezone.now())
            StrategySnapshotService.create_snapshot(strategy, user=request.user,
                change_notes='Saved Strategy Studio definition')
            return Response({'document': document, 'revision': revision(document), 'preview': preview})
        # Compact authoring metadata is returned once, outside the execution path.
        from instruments.models import Instrument
        instrument_ids = {watch['instrument_id'] for watch in current['watchlist_instruments']}
        instruments = list(Instrument.objects.filter(pk__in=instrument_ids).values(
            'id', 'name', 'exchange', 'instrument_type', 'expiry_date', 'lot_size', 'tick_size', 'is_active'))
        return Response({'document': current, 'revision': revision(current),
                         'instruments': instruments})

    @action(detail=True, methods=['post'], url_path='validate-definition')
    def validate_definition(self, request, pk=None):
        from .definitions import validate_definition, compile_preview
        from rest_framework.exceptions import ValidationError
        strategy = self.get_object()
        try:
            document = validate_definition(request.data.get('document'))
            return Response({'document': document, 'preview': compile_preview(strategy, document)})
        except (ValueError, TypeError, KeyError) as exc:
            raise ValidationError(str(exc)) from None

    def get_queryset(self):
        """Filter strategies by current user."""
        qs = Strategy.objects.filter(user=self.request.user).select_related('user').prefetch_related('tags')
        if self.action == 'list':
            qs = qs.defer('definition')
        if self.action in {'list', 'summary'}:
            search = self.request.query_params.get('search', '')[:100]
            if search:
                qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
            if self.action == 'list' and self.request.query_params.get('status'):
                from rest_framework.fields import ChoiceField
                value = ChoiceField(choices=Strategy._meta.get_field('status').choices).run_validation(self.request.query_params['status'])
                qs = qs.filter(status=value)
        return qs.order_by('-created_at', '-id')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        counts = {row['status']: row['count'] for row in self.get_queryset().values('status').annotate(count=Count('id')).order_by()}
        return Response({'total': sum(counts.values()), 'statuses': counts})

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
            definition=original.definition,
        )
        new_strategy.tags.set(original.tags.all())

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
        """List metadata only; previews fetch one snapshot and its true predecessor."""
        versions = self.get_object().versions.select_related('created_by').defer('config_snapshot').order_by('-version_number', '-id')
        page = self.paginate_queryset(versions)
        return self.get_paginated_response(StrategyVersionListSerializer(page, many=True).data)

    @action(detail=True, methods=['get'], url_path=r'versions/(?P<version_id>[0-9]+)')
    def version(self, request, pk=None, version_id=None):
        from django.shortcuts import get_object_or_404
        version = get_object_or_404(self.get_object().versions.select_related('created_by', 'strategy'), pk=version_id)
        return Response(StrategyVersionSerializer(version).data)

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
