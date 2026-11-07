from decimal import Decimal

from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Sum, Subquery, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from common.pagination import StandardPagination
from rest_framework.exceptions import ValidationError
from rest_framework.fields import IntegerField as IdentifierField
from brokers.models import BrokerSession
from common.enums import OrderStatus
from execution.order_reports import ACTIVE

from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, LiveTrade, SlippageRecord, TradingSession
from .serializers import (
    ExecutionLogSerializer,
    LiveOrderSerializer,
    LivePositionSerializer,
    LiveTradeSerializer,
    LiveStrategyAllocationSerializer,
    SlippageRecordSerializer,
    TradingSessionSerializer,
)
from .services import LiveExecutionService


class TradingSessionViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination
    serializer_class = TradingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        sessions = TradingSession.objects.filter(user=self.request.user)
        # Count orders only for displayed sessions; a list COUNT does not need
        # to group every session with its complete order history.
        active_orders = LiveOrder.objects.filter(session_id=OuterRef('pk'), status__in=ACTIVE).order_by().values('session_id').annotate(total=Count('id')).values('total')[:1]
        session_status = self.request.query_params.get("status")
        if session_status:
            from common.enums import ExecutionSessionStatus
            from rest_framework.fields import ChoiceField
            session_status = ChoiceField(choices=ExecutionSessionStatus.choices).run_validation(session_status)
            sessions = sessions.filter(status=session_status)
        return sessions.select_related(
            "strategy", "broker_credential"
        ).annotate(
            annotated_active_orders=Coalesce(Subquery(active_orders, output_field=IntegerField()), 0),
            annotated_broker_session_valid=Exists(BrokerSession.objects.filter(
                credential_id=OuterRef("broker_credential_id"),
                is_valid=True,
                token_expiry__gt=timezone.now(),
            )),
        ).prefetch_related(Prefetch("allocation", queryset=LiveStrategyAllocation.objects.with_totals())).order_by('-created_at', '-id')

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(LiveExecutionService.session_summary(request.user))

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        session = self.get_object()
        try:
            session = LiveExecutionService.pause_session(session)
        except ValueError as exc:
            raise ValidationError(str(exc)) from None
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        session = self.get_object()
        try:
            session = LiveExecutionService.resume_session(session)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        session = self.get_object()
        from rest_framework.fields import BooleanField
        close_positions = BooleanField().run_validation(request.data.get('close_positions', False))
        if session.status in {"STOPPED", "STOPPING"} and not close_positions:
            return Response(self.get_serializer(session).data)
        session = LiveExecutionService.stop_session(session, close_positions=close_positions)
        return Response(self.get_serializer(self.get_object()).data)


    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """
        Reconcile owned orders; positions and trades are derived from their fills.
        """
        session = self.get_object()
        from live_trading.order_processor import reconcile_orders

        try:
            result = reconcile_orders(session.broker_credential)
            return Response({"synced_orders": result["matched"], "orders": result})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LiveOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LiveOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = LiveOrder.objects.filter(user=self.request.user).select_related("strategy", "session", "broker_credential", "instrument")
        for field in ("status", "session", "allocation"):
            value = self.request.query_params.get(field)
            if value:
                if field != "status":
                    value = IdentifierField(min_value=1).run_validation(value)
                queryset = queryset.filter(**{f"{field}_id" if field != "status" else field: value})
        return queryset.order_by('-placed_at', '-id')

    @action(detail=False, methods=["get"])
    def summary(self, request):
        orders = self.get_queryset()
        counts = orders.aggregate(
            total=Count("id"),
            filled=Count("id", filter=Q(status=OrderStatus.FILLED)),
            partial=Count("id", filter=Q(status=OrderStatus.PARTIAL_FILL)),
            active=Count("id", filter=Q(status__in=[OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL, "UNKNOWN"])),
            rejected=Count("id", filter=Q(status=OrderStatus.REJECTED)),
            cancelled=Count("id", filter=Q(status=OrderStatus.CANCELLED)),
        )
        return Response(counts)


class LivePositionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LivePositionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = LivePosition.objects.filter(user=self.request.user, quantity__gt=0).select_related(
            "strategy", "instrument", "broker_credential"
        ).order_by("-opened_at", "-pk")
        for field in ("strategy", "allocation", "broker_credential"):
            value = self.request.query_params.get(field)
            if value:
                value = IdentifierField(min_value=1).run_validation(value)
                queryset = queryset.filter(**{f"{field}_id": value})
        return queryset

    @action(detail=False, methods=["get"])
    def summary(self, request):
        from common.valuation import position_totals
        return Response(position_totals(self.get_queryset()))


class LiveTradeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LiveTradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = LiveTrade.objects.filter(user=self.request.user).select_related(
            "strategy", "allocation", "broker_credential", "instrument", "exit_order"
        )
        for field in ("strategy", "allocation", "broker_credential"):
            value = self.request.query_params.get(field)
            if value:
                value = IdentifierField(min_value=1).run_validation(value)
                queryset = queryset.filter(**{f"{field}_id": value})
        return queryset.order_by('-exit_time', '-id')

    @action(detail=False, methods=["get"])
    def summary(self, request):
        stats = self.get_queryset().aggregate(
            count=Count("id"),
            winning=Count("id", filter=Q(realized_pnl__gt=0)),
            losing=Count("id", filter=Q(realized_pnl__lt=0)),
            total_realized_pnl=Sum("realized_pnl"),
        )
        stats["realized_pnl"] = stats.pop("total_realized_pnl") or Decimal("0")
        return Response(stats)


class ExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExecutionLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = ExecutionLog.objects.filter(order__user=self.request.user).select_related("order", "order__instrument", "order__broker_credential").order_by("-created_at", "-pk")
        event_type = self.request.query_params.get("event_type")
        order_id = self.request.query_params.get("order")
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if order_id:
            queryset = queryset.filter(order_id=IdentifierField(min_value=1).run_validation(order_id))
        return queryset


class SlippageRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SlippageRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = SlippageRecord.objects.filter(order__user=self.request.user).select_related("order", "order__instrument", "order__broker_credential").order_by("-created_at", "-pk")
        order_id = self.request.query_params.get("order")
        if order_id:
            queryset = queryset.filter(order_id=IdentifierField(min_value=1).run_validation(order_id))
        return queryset


class LiveStrategyAllocationViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination
    serializer_class = LiveStrategyAllocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = LiveStrategyAllocation.objects.with_totals().filter(user=self.request.user)
        broker_id = self.request.query_params.get("broker_credential")
        if broker_id:
            queryset = queryset.filter(broker_credential_id=IdentifierField(min_value=1).run_validation(broker_id))
        strategy_id = self.request.query_params.get("strategy")
        if strategy_id:
            queryset = queryset.filter(strategy_id=IdentifierField(min_value=1).run_validation(strategy_id))
        return queryset

    @action(detail=True, methods=["post"], url_path="update-allocation")
    def update_allocation(self, request, pk=None):
        allocation = self.get_object()
        from rest_framework.fields import DecimalField as AmountField
        amount = AmountField(max_digits=15, decimal_places=2, min_value=Decimal("0.01")).run_validation(
            request.data.get("allocation_amount")
        )
        try:
            allocation = LiveExecutionService.update_allocation(
                allocation=allocation,
                allocation_amount=amount,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from None
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=['post'], url_path='deploy-version')
    def deploy_version(self, request, pk=None):
        from django.shortcuts import get_object_or_404
        from rest_framework.fields import IntegerField
        from strategies.models import StrategyVersion
        from strategies.services import StrategyDeploymentService
        allocation = self.get_object()
        version_id = IntegerField(min_value=1).run_validation(request.data.get('version_id'))
        version = get_object_or_404(StrategyVersion, pk=version_id, strategy=allocation.strategy)
        try:
            allocation = StrategyDeploymentService.change_version(allocation, version, 'live', request.user)
        except ValueError as exc:
            raise ValidationError(str(exc)) from None
        return Response(self.get_serializer(self.get_object()).data)
