"""
Views for the backtesting app.
"""
from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from kombu.exceptions import OperationalError
from .models import (
    BacktestRun, BacktestMetrics, MonteCarloRun
)
from .serializers import (
    BacktestRunSerializer, BacktestRunListSerializer, BacktestRunDetailSerializer,
    BacktestTradeSerializer, BacktestMetricsSerializer, EquityCurvePointSerializer,
    MonteCarloRunSerializer, MonteCarloResultSerializer
)
from common.enums import BacktestStatus
from strategies.services import StrategySnapshotService
from .tasks import run_backtest_task, run_monte_carlo_task
from .analytics import BacktestAnalytics
import logging

logger = logging.getLogger(__name__)


import threading
from backend.celery import app as celery_app

def _run_task_with_broker_fallback(task, object_id, object_to_refresh, failure_reset=None):
    """
    Try to dispatch via Celery broker if workers are active; fall back to in-process background thread otherwise.
    """
    try:
        # Check if any Celery workers are active
        workers = celery_app.control.ping(timeout=0.5)
        if workers:
            task.delay(object_id)
            return False
            
        logger.warning("No active Celery workers found for task %s(%s). Falling back to background thread.", task.name, object_id)
    except Exception as exc:
        logger.warning("Celery broker unavailable for task %s(%s): %s", task.name, object_id, exc)

    # Fallback: Run asynchronously in a background thread so the HTTP request doesn't block
    if getattr(settings, "DEBUG", False):
        def _run_in_thread():
            try:
                task.apply(args=(object_id,))
            except Exception as e:
                logger.exception("Background thread task execution failed: %s", e)
                if object_to_refresh:
                    try:
                        object_to_refresh.refresh_from_db()
                        if hasattr(object_to_refresh, 'status'):
                            object_to_refresh.status = 'FAILED'
                        if hasattr(object_to_refresh, 'error_message'):
                            object_to_refresh.error_message = f"Task failed: {str(e)}"
                        object_to_refresh.save()

                        # Broadcast the error via WebSocket
                        try:
                            from asgiref.sync import async_to_sync
                            from channels.layers import get_channel_layer
                            channel_layer = get_channel_layer()
                            if channel_layer and hasattr(object_to_refresh, 'user_id'):
                                group_name = f"user_{object_to_refresh.user_id}_backtest"
                                message_data = {
                                    "type": "backtest.error",
                                    "message": {
                                        "run_id": object_to_refresh.id,
                                        "status": "FAILED",
                                        "error": str(e)
                                    }
                                }
                                async_to_sync(channel_layer.group_send)(group_name, message_data)
                        except Exception as ws_e:
                            logger.exception("Failed to broadcast backtest error: %s", ws_e)

                    except Exception as db_e:
                        logger.exception("Failed to update task status in DB: %s", db_e)
        
        thread = threading.Thread(target=_run_in_thread)
        thread.start()
        return True

    # In production without workers/broker, reset status
    if failure_reset:
        for field, value in failure_reset.items():
            setattr(object_to_refresh, field, value)
        object_to_refresh.save(update_fields=list(failure_reset.keys()))
    raise OperationalError("Celery broker/workers are unavailable.")


class BacktestRunViewSet(viewsets.ModelViewSet):
    """ViewSet for backtest runs."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return BacktestRun.objects.filter(user=self.request.user).select_related('strategy')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BacktestRunListSerializer
        if self.action == 'retrieve':
            return BacktestRunDetailSerializer
        return BacktestRunSerializer
    
    def perform_create(self, serializer):
        strategy = serializer.validated_data['strategy']
        if strategy.user_id != self.request.user.id and not strategy.allow_backtest:
            raise ValidationError({"strategy": "Backtesting is disabled for this strategy."})
        if not strategy.watchlist_instruments.exists():
            raise ValidationError({"strategy": "Strategy has no watchlist instruments."})
        if not strategy.rule_groups.filter(rule_type='ENTRY', is_active=True, rules__is_active=True).exists():
            raise ValidationError({"strategy": "Strategy needs at least one active entry rule before backtesting."})

        # Create an immutable snapshot
        version = StrategySnapshotService.create_snapshot(
            strategy, 
            user=self.request.user,
            change_notes=f"Auto-snapshot for backtest: {serializer.validated_data.get('name', 'Unnamed')}"
        )

        serializer.save(
            user=self.request.user, 
            strategy_version=version,
            config_snapshot=version.config_snapshot,
            risk_profile_snapshot={},
        )
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a backtest run (triggers Celery task)."""
        run = self.get_object()
        if run.status not in ['PENDING', 'FAILED', 'CANCELLED']:
            return Response({'error': f'Backtest cannot be started in {run.status} status'}, status=400)
        
        run.status = 'RUNNING'
        run.started_at = timezone.now()
        run.error_message = ""
        run.progress_pct = 0
        run.save()
        
        # Broadcast that backtest has started
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            if channel_layer:
                group_name = f"user_{request.user.id}_backtest"
                message_data = {
                    "type": "backtest.progress",
                    "message": {
                        "run_id": run.id,
                        "status": "RUNNING",
                        "progress_pct": 0,
                        "message": "Backtest started, loading data...",
                        "timestamp": timezone.now().isoformat(),
                    }
                }
                async_to_sync(channel_layer.group_send)(group_name, message_data)
        except Exception as e:
            logger.warning(f"Failed to broadcast backtest start: {e}")

        try:
            ran_inline = _run_task_with_broker_fallback(
                run_backtest_task,
                run.id,
                run,
                failure_reset={
                    'status': BacktestStatus.PENDING,
                    'started_at': None,
                    'error_message': 'Task broker is unavailable. Start a Celery worker/broker or retry in DEBUG mode.'
                },
            )
        except OperationalError:
            return Response(
                {'error': 'Backtest queue is unavailable. Start the Celery broker/worker and try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        message = 'Backtest completed in local fallback mode' if ran_inline else 'Backtest started'
        return Response({'success': True, 'message': message, 'status': run.status})

    @action(detail=True, methods=['post'])
    def rerun(self, request, pk=None):
        """Clone an existing backtest run and start it immediately."""
        run = self.get_object()
        
        # Clone fields
        new_run = BacktestRun.objects.create(
            strategy=run.strategy,
            user=run.user,
            name=f"{run.name} (Rerun)",
            start_date=run.start_date,
            end_date=run.end_date,
            strategy_version=run.strategy_version,
            initial_capital=run.initial_capital,
            slippage_pct=run.slippage_pct,
            brokerage_per_trade=run.brokerage_per_trade,
            brokerage_pct=run.brokerage_pct,
            parameters=run.parameters,
            config_snapshot=run.config_snapshot,
            risk_profile_snapshot=run.risk_profile_snapshot,
            status='RUNNING',
            started_at=timezone.now(),
        )
        
        try:
            ran_inline = _run_task_with_broker_fallback(
                run_backtest_task,
                new_run.id,
                new_run,
                failure_reset={
                    'status': 'PENDING',
                    'started_at': None,
                    'error_message': 'Task broker is unavailable. Start a Celery worker/broker or retry in DEBUG mode.'
                },
            )
        except OperationalError:
            new_run.status = 'FAILED'
            new_run.error_message = 'Backtest queue is unavailable. Start the Celery broker/worker and try again.'
            new_run.save()
            return Response(
                {'error': 'Backtest queue is unavailable. Start the Celery broker/worker and try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = self.get_serializer(new_run)
        return Response({'success': True, 'message': 'Backtest cloned and started successfully.', 'run': serializer.data})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running backtest."""
        run = self.get_object()
        if run.status != 'RUNNING':
            return Response({'error': 'Backtest not running'}, status=400)
        
        run.status = 'CANCELLED'
        run.completed_at = timezone.now()
        run.save()
        
        return Response({'success': True, 'message': 'Backtest cancelled'})
    
    @action(detail=True, methods=['get'])
    def trades(self, request, pk=None):
        """Get all trades for a backtest run."""
        run = self.get_object()
        trades = run.trades.all()
        
        trade_filter = request.query_params.get('filter')
        if trade_filter == 'winning':
            trades = trades.filter(net_pnl__gt=0)
        elif trade_filter == 'losing':
            trades = trades.filter(net_pnl__lt=0)
            
        instrument = request.query_params.get('instrument')
        if instrument and instrument != 'all':
            trades = trades.filter(instrument__symbol=instrument)
            
        search = request.query_params.get('search')
        if search:
            trades = trades.filter(instrument__symbol__icontains=search)
        
        class TradePagination(PageNumberPagination):
            page_size = 50
            page_size_query_param = 'page_size'
            
        paginator = TradePagination()
        page = paginator.paginate_queryset(trades, request, view=self)
        if page is not None:
            serializer = BacktestTradeSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        serializer = BacktestTradeSerializer(trades, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='equity_curve')
    def equity_curve(self, request, pk=None):
        """Get equity curve data for charting."""
        run = self.get_object()
        points = run.equity_curve.order_by('timestamp')
        
        count = points.count()
        if count > 1000:
            step = count // 1000
            ids = list(points.values_list('id', flat=True))[::step]
            points = points.filter(id__in=ids).order_by('timestamp')
            
        serializer = EquityCurvePointSerializer(points, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['get'], url_path='charges_timeline')
    def charges_timeline(self, request, pk=None):
        """Get lightweight timeline of charges for frontend gross P&L calculations."""
        run = self.get_object()
        trades = run.trades.filter(exit_time__isnull=False).only('exit_time', 'charges_json').order_by('exit_time')
        
        timeline = []
        for t in trades:
            try:
                charges_json = t.charges_json or {}
                if isinstance(charges_json, str):
                    import json
                    charges_json = json.loads(charges_json)
                
                charges = float(charges_json.get('total_charges', 0))
                if charges > 0:
                    exit_time = t.exit_time
                    timeline.append({
                        'exitTime': int(exit_time.timestamp() * 1000),
                        'charges': charges
                    })
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error parsing charges for trade {t.id}: {e}")
                continue
        
        return Response(timeline)
    
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get metrics for a backtest run."""
        run = self.get_object()
        try:
            metrics = run.metrics
            return Response(BacktestMetricsSerializer(metrics).data)
        except BacktestMetrics.DoesNotExist:
            return Response({})

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        run = self.get_object()
        analytics = BacktestAnalytics(run.id)
        return Response(analytics.full_report())


class MonteCarloRunViewSet(viewsets.ModelViewSet):
    """ViewSet for Monte Carlo runs."""
    serializer_class = MonteCarloRunSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return MonteCarloRun.objects.filter(
            backtest_run__user=self.request.user
        ).select_related('backtest_run')
        
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a Monte Carlo simulation."""
        run = self.get_object()
        if run.status != 'PENDING':
            return Response({'error': 'Simulation already started'}, status=400)
        
        run.status = 'RUNNING'
        run.save()

        try:
            ran_inline = _run_task_with_broker_fallback(
                run_monte_carlo_task,
                run.id,
                run,
                failure_reset={
                    'status': BacktestStatus.PENDING,
                },
            )
        except OperationalError:
            return Response(
                {'error': 'Monte Carlo queue is unavailable. Start the Celery broker/worker and try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        message = 'Monte Carlo simulation completed in local fallback mode' if ran_inline else 'Monte Carlo simulation started'
        return Response({'success': True, 'message': message, 'status': run.status})
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get Monte Carlo results."""
        run = self.get_object()
        results = run.results.all()
        serializer = MonteCarloResultSerializer(results, many=True)
        return Response(serializer.data)
