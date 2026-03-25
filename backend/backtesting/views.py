"""
Views for the backtesting app.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import (
    BacktestRun, BacktestTrade, BacktestMetrics, EquityCurvePoint,
    OptimizationRun, OptimizationResult, MonteCarloRun, MonteCarloResult
)
from .serializers import (
    BacktestRunSerializer, BacktestRunListSerializer, BacktestRunDetailSerializer,
    BacktestTradeSerializer, BacktestMetricsSerializer, EquityCurvePointSerializer,
    OptimizationRunSerializer, OptimizationResultSerializer,
    MonteCarloRunSerializer, MonteCarloResultSerializer
)


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
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a backtest run (triggers Celery task)."""
        run = self.get_object()
        if run.status != 'PENDING':
            return Response({'error': 'Backtest already started'}, status=400)
        
        run.status = 'RUNNING'
        run.started_at = timezone.now()
        run.save()
        
        # TODO: Trigger Celery task here
        # from .tasks import run_backtest
        # run_backtest.delay(run.id)
        
        return Response({'success': True, 'message': 'Backtest started'})
    
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
        serializer = BacktestTradeSerializer(trades, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def equity_curve(self, request, pk=None):
        """Get equity curve data for charting."""
        run = self.get_object()
        points = run.equity_curve.all()
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


class OptimizationRunViewSet(viewsets.ModelViewSet):
    """ViewSet for optimization runs."""
    serializer_class = OptimizationRunSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return OptimizationRun.objects.filter(user=self.request.user).select_related('strategy')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start an optimization run."""
        run = self.get_object()
        if run.status != 'PENDING':
            return Response({'error': 'Optimization already started'}, status=400)
        
        run.status = 'RUNNING'
        run.started_at = timezone.now()
        run.save()
        
        # TODO: Trigger Celery task
        
        return Response({'success': True, 'message': 'Optimization started'})
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get all results from an optimization run."""
        run = self.get_object()
        results = run.results.all().order_by('-sharpe')[:100]  # Top 100 by Sharpe
        serializer = OptimizationResultSerializer(results, many=True)
        return Response(serializer.data)


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
        
        # TODO: Trigger Celery task
        
        return Response({'success': True, 'message': 'Monte Carlo simulation started'})
    
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get Monte Carlo results."""
        run = self.get_object()
        results = run.results.all()
        serializer = MonteCarloResultSerializer(results, many=True)
        return Response(serializer.data)
