"""
Views for the backtesting app.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db import transaction
from .models import (
    BacktestRun, BacktestMetrics, MonteCarloRun
)
from .serializers import (
    BacktestRunSerializer, BacktestRunListSerializer, BacktestRunDetailSerializer,
    BacktestTradeSerializer, BacktestMetricsSerializer, EquityCurvePointSerializer,
    MonteCarloRunSerializer, MonteCarloResultSerializer
)
from common.enums import BacktestStatus
from .services import create_backtest, start_backtest, publish_backtest_update, notify_backtest_result


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

    @transaction.atomic
    def perform_destroy(self, instance):
        from commercial.usage import complete_usage, reject_request
        instance = BacktestRun.objects.select_for_update().get(pk=instance.pk)
        if instance.status in {"QUEUED", "RUNNING"} or (instance.started_at and not instance.completed_at):
            reject_request("work_still_running", "Cancel this backtest and wait for it to stop before deleting it.")
        complete_usage("backtest", instance.pk, "CANCELLED")
        instance.delete()

    @action(detail=False, methods=['post'])
    def estimate(self, request):
        from commercial.usage import estimate_backtest_workload
        from strategies.services import StrategySnapshotService
        serializer = BacktestRunSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["strategy"].user_id != request.user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Select your own strategy.")
        snapshot = StrategySnapshotService._serialize_strategy(data["strategy"])
        from .services import backtest_configuration
        draft = BacktestRun(config_snapshot=snapshot, parameters=data.get("parameters", {}))
        return Response(estimate_backtest_workload(request.user, backtest_configuration(draft), data["start_date"], data["end_date"]))

    @action(detail=True, methods=['post'], url_path='estimate-rerun')
    def estimate_rerun(self, request, pk=None):
        from commercial.usage import estimate_backtest_workload
        from .services import backtest_configuration
        run = self.get_object()
        return Response(estimate_backtest_workload(request.user, backtest_configuration(run), run.start_date, run.end_date))

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a backtest run (triggers Celery task)."""
        run = self.get_object()
        start_backtest(run)

        return Response({'success': True, 'message': 'Backtest started', 'status': run.status})

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def rerun(self, request, pk=None):
        """Clone an existing backtest run and start it immediately."""
        run = self.get_object()

        # Clone fields
        from .services import backtest_configuration
        serializer = BacktestRunSerializer(data={"strategy": run.strategy_id, "name": f"{run.name} (Rerun)",
            "start_date": run.start_date, "end_date": run.end_date, "initial_capital": run.initial_capital,
            "slippage_pct": run.slippage_pct, "charge_profile": run.charge_profile_id,
            "include_charges": run.include_charges, "estimate_token": request.data.get("estimate_token", "")},
            context={"request": request, "charge_profile_snapshot": run.charge_profile_snapshot})
        serializer.is_valid(raise_exception=True)
        new_run = create_backtest(serializer, request.user, approved_snapshot=backtest_configuration(run), charge_profile_snapshot=run.charge_profile_snapshot)
        start_backtest(new_run)

        serializer = self.get_serializer(new_run)
        return Response({'success': True, 'message': 'Backtest cloned and started successfully.', 'run': serializer.data})

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        """Cancel a running backtest."""
        run = BacktestRun.objects.select_for_update().get(pk=self.get_object().pk)
        if run.status not in ['PENDING', 'QUEUED', 'RUNNING']:
            return Response({'error': 'Backtest is no longer active'}, status=400)

        updated = BacktestRun.objects.filter(pk=run.pk, status__in=[BacktestStatus.PENDING, BacktestStatus.QUEUED, BacktestStatus.RUNNING]).update(
            status=BacktestStatus.CANCELLED, completed_at=None if run.started_at else timezone.now(), progress_message="Backtest cancelled."
        )
        if not updated:
            return Response({'error': 'Backtest is no longer running.'}, status=status.HTTP_409_CONFLICT)
        run.refresh_from_db()
        from commercial.usage import complete_usage
        complete_usage("backtest", run.pk, run.status)
        publish_backtest_update(run)
        notify_backtest_result(run)

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

    @transaction.atomic
    def perform_create(self, serializer):
        from commercial.usage import require_request_limits, reserve_usage
        import uuid
        user = self.request.user
        payload = {**serializer.validated_data, "backtest_run": serializer.validated_data["backtest_run"].pk}
        key = self.request.headers.get("Idempotency-Key") or f"mc:{uuid.uuid4()}"
        policy = require_request_limits(user, mc_simulations=serializer.validated_data.get("num_simulations", 1000))
        run = serializer.save()
        reserve_usage(user, "monte_carlo", key, payload, resource=run, policy=policy)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def start(self, request, pk=None):
        """Start a Monte Carlo simulation."""
        run = self.get_object()
        if run.status != 'PENDING':
            return Response({'error': 'Simulation already started'}, status=400)

        updated = MonteCarloRun.objects.filter(pk=run.pk, status=BacktestStatus.PENDING).update(
            status=BacktestStatus.QUEUED,
            error_message="",
            completed_at=None,
        )
        if not updated:
            return Response({'error': 'Simulation has already been started.'}, status=status.HTTP_409_CONFLICT)
        run.refresh_from_db()

        from commercial.usage import queue_compute_work
        queue_compute_work("backtesting.run_monte_carlo", run.pk)

        return Response({'success': True, 'message': 'Monte Carlo simulation started', 'status': run.status})

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        run = self.get_object()
        updated = MonteCarloRun.objects.filter(pk=run.pk, status__in=['PENDING', 'QUEUED']).update(
            status=BacktestStatus.CANCELLED, completed_at=timezone.now())
        if not updated:
            return Response({'error': 'Only pending or queued simulations can be cancelled.'}, status=409)
        from commercial.usage import complete_usage
        complete_usage('monte_carlo', run.pk, BacktestStatus.CANCELLED)
        return Response({'success': True, 'status': BacktestStatus.CANCELLED})

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get Monte Carlo results."""
        run = self.get_object()
        results = run.results.all()
        serializer = MonteCarloResultSerializer(results, many=True)
        return Response(serializer.data)
