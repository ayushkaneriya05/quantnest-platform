"""
Views for the backtesting app.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from .models import (
    BacktestRun, BacktestMetrics, MonteCarloRun
)
from .serializers import (
    BacktestRunSerializer, BacktestRunListSerializer, BacktestRunDetailSerializer,
    BacktestTradeSerializer, BacktestMetricsSerializer, EquityCurvePointSerializer,
    MonteCarloRunSerializer, MonteCarloResultSerializer
)
from common.enums import BacktestStatus
from .services import create_backtest, start_backtest
from .tasks import _notify_backtest_result, run_backtest_task, run_monte_carlo_task
import logging

logger = logging.getLogger(__name__)


def _queue_task(task, obj):
    try:
        task.delay(obj.pk)
        return True
    except Exception as exc:
        logger.warning("Unable to queue %s(%s): %s", task.name, obj.pk, exc)
        return False


class BacktestRunViewSet(viewsets.ModelViewSet):
    """ViewSet for backtest runs."""
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    
    def get_queryset(self):
        queryset = BacktestRun.objects.filter(user=self.request.user).select_related('strategy')
        if self.action == 'list' and self.request.query_params.get('status'):
            queryset = queryset.filter(status=self.request.query_params['status'])
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BacktestRunListSerializer
        if self.action == 'retrieve':
            return BacktestRunDetailSerializer
        return BacktestRunSerializer
    
    def perform_create(self, serializer):
        create_backtest(serializer, self.request.user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a backtest run (triggers Celery task)."""
        run = self.get_object()
        if run.status != BacktestStatus.PENDING:
            return Response({'error': f'Backtest cannot be started in {run.status} status'}, status=400)

        start_backtest(run)
        
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
                        "message": run.progress_message,
                        "timestamp": timezone.now().isoformat(),
                    }
                }
                async_to_sync(channel_layer.group_send)(group_name, message_data)
        except Exception as e:
            logger.warning(f"Failed to broadcast backtest start: {e}")

        run.refresh_from_db()
        if run.status == BacktestStatus.PENDING and run.error_message:
            return Response(
                {'error': run.error_message},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({'success': True, 'message': 'Backtest started', 'status': run.status})

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
            charge_profile=run.charge_profile,
            include_charges=run.include_charges,
            parameters=run.parameters,
            config_snapshot=run.config_snapshot,
            status=BacktestStatus.PENDING,
        )
        new_run.started_at = timezone.now()
        new_run.status = BacktestStatus.RUNNING
        new_run.save(update_fields=['status', 'started_at'])
        if not _queue_task(run_backtest_task, new_run):
            new_run.status = BacktestStatus.FAILED
            new_run.error_message = 'Backtest queue is unavailable. Start a Celery worker and try again.'
            new_run.save(update_fields=['status', 'error_message'])
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
        
        updated = BacktestRun.objects.filter(pk=run.pk, status=BacktestStatus.RUNNING).update(
            status=BacktestStatus.CANCELLED, completed_at=timezone.now(), progress_message="Backtest cancelled."
        )
        if not updated:
            return Response({'error': 'Backtest is no longer running.'}, status=status.HTTP_409_CONFLICT)
        run.refresh_from_db()
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"user_{request.user.id}_backtest",
                    {
                        "type": "backtest.progress",
                        "message": {
                            "run_id": run.id,
                            "status": run.status,
                            "progress_pct": run.progress_pct,
                            "message": run.progress_message,
                            "timestamp": timezone.now().isoformat(),
                        },
                    },
                )
        except Exception as exc:
            logger.warning("Failed to broadcast backtest cancellation: %s", exc)
        _notify_backtest_result(run)
        
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
            response = paginator.get_paginated_response(serializer.data)
            response.data['instrument_options'] = list(
                run.trades.order_by().values_list('instrument__symbol', flat=True).distinct().order_by('instrument__symbol')
            )
            return response
            
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
        
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get metrics for a backtest run."""
        run = self.get_object()
        try:
            metrics = run.metrics
            return Response(BacktestMetricsSerializer(metrics).data)
        except BacktestMetrics.DoesNotExist:
            return Response({})

class MonteCarloRunViewSet(viewsets.ModelViewSet):
    """ViewSet for Monte Carlo runs."""
    serializer_class = MonteCarloRunSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    
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
        
        updated = MonteCarloRun.objects.filter(pk=run.pk, status=BacktestStatus.PENDING).update(
            status=BacktestStatus.RUNNING,
            error_message="",
            completed_at=None,
        )
        if not updated:
            return Response({'error': 'Simulation has already been started.'}, status=status.HTTP_409_CONFLICT)
        run.refresh_from_db()

        if not _queue_task(run_monte_carlo_task, run):
            MonteCarloRun.objects.filter(pk=run.pk, status=BacktestStatus.RUNNING).update(
                status=BacktestStatus.PENDING,
                error_message="Monte Carlo queue is unavailable. Start the Celery broker/worker and try again.",
            )
            return Response(
                {'error': 'Monte Carlo queue is unavailable. Start the Celery broker/worker and try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({'success': True, 'message': 'Monte Carlo simulation started', 'status': run.status})
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get Monte Carlo results."""
        run = self.get_object()
        results = run.results.all()
        serializer = MonteCarloResultSerializer(results, many=True)
        return Response(serializer.data)
