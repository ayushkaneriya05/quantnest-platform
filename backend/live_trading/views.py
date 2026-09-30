from decimal import Decimal

from django.db.models import Count, DecimalField, Exists, ExpressionWrapper, F, IntegerField, OuterRef, Prefetch, Q, Subquery, Sum, Value, When, Case
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from brokers.models import BrokerSession
from common.enums import OrderStatus

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


class LiveTradingPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class TradingSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TradingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        decimal_field = DecimalField(max_digits=18, decimal_places=4)
        zero_money = Value(Decimal("0"), output_field=decimal_field)
        active_statuses = [OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL, "UNKNOWN"]

        open_positions = LivePosition.objects.filter(allocation_id=OuterRef("pk"), quantity__gt=0)
        used_capital = open_positions.order_by().values("allocation_id").annotate(
            total=Sum(ExpressionWrapper(F("quantity") * F("avg_price"), output_field=decimal_field))
        ).values("total")[:1]
        unrealized_pnl = open_positions.order_by().values("allocation_id").annotate(
            total=Sum("unrealized_pnl")
        ).values("total")[:1]
        realized_pnl = LiveTrade.objects.filter(allocation_id=OuterRef("pk")).order_by().values(
            "allocation_id"
        ).annotate(total=Sum("realized_pnl")).values("total")[:1]
        reserved_value = ExpressionWrapper(
            Greatest(F("pending_quantity"), F("quantity") - F("filled_quantity"))
            * Coalesce(F("price"), zero_money),
            output_field=decimal_field,
        )
        reserved_capital = LiveOrder.objects.filter(
            allocation_id=OuterRef("pk"), status__in=active_statuses
        ).order_by().values("allocation_id").annotate(total=Sum(reserved_value)).values("total")[:1]
        allocation_trades = LiveTrade.objects.filter(allocation_id=OuterRef("pk")).order_by().values(
            "allocation_id"
        ).annotate(total=Count("id")).values("total")[:1]

        allocation_queryset = LiveStrategyAllocation.objects.select_related(
            "strategy", "broker_credential", "deployed_version"
        ).annotate(
            annotated_used_capital=Coalesce(Subquery(used_capital, output_field=decimal_field), zero_money),
            annotated_reserved_capital=Coalesce(Subquery(reserved_capital, output_field=decimal_field), zero_money),
            annotated_realized_pnl=Coalesce(Subquery(realized_pnl, output_field=decimal_field), zero_money),
            annotated_unrealized_pnl=Coalesce(Subquery(unrealized_pnl, output_field=decimal_field), zero_money),
            annotated_trade_count=Coalesce(Subquery(allocation_trades, output_field=IntegerField()), Value(0)),
        ).annotate(
            annotated_available_capital=Greatest(
                zero_money,
                F("allocated_capital") - F("annotated_used_capital") - F("annotated_reserved_capital") + F("annotated_realized_pnl"),
            ),
            annotated_total_pnl=F("annotated_realized_pnl") + F("annotated_unrealized_pnl"),
        )

        allocation_positions_count = LivePosition.objects.filter(
            allocation_id=OuterRef("allocation_id"), quantity__gt=0
        ).order_by().values("allocation_id").annotate(total=Count("id")).values("total")[:1]
        legacy_positions_count = LivePosition.objects.filter(
            allocation__isnull=True,
            user_id=OuterRef("user_id"),
            strategy_id=OuterRef("strategy_id"),
            broker_credential_id=OuterRef("broker_credential_id"),
            quantity__gt=0,
        ).order_by().values("user_id").annotate(total=Count("id")).values("total")[:1]
        active_orders_count = LiveOrder.objects.filter(
            session_id=OuterRef("pk"), status__in=active_statuses
        ).order_by().values("session_id").annotate(total=Count("id")).values("total")[:1]

        return TradingSession.objects.filter(user=self.request.user).select_related(
            "strategy", "broker_credential"
        ).annotate(
            annotated_open_positions=Case(
                When(allocation_id__isnull=True, then=Coalesce(Subquery(legacy_positions_count), Value(0))),
                default=Coalesce(Subquery(allocation_positions_count), Value(0)),
                output_field=IntegerField(),
            ),
            annotated_active_orders=Coalesce(Subquery(active_orders_count), Value(0)),
            annotated_broker_session_valid=Exists(BrokerSession.objects.filter(
                credential_id=OuterRef("broker_credential_id"),
                is_valid=True,
                token_expiry__gt=timezone.now(),
            )),
        ).prefetch_related(Prefetch("allocation", queryset=allocation_queryset, to_attr="prefetched_allocation"))

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(LiveExecutionService.session_summary(request.user))

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        session = self.get_object()
        if session.status != "RUNNING":
            raise ValidationError({"status": f"Cannot pause a session in {session.status} state."})
        return Response(self.get_serializer(LiveExecutionService.pause_session(session)).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        session = self.get_object()
        if session.status != "PAUSED":
            raise ValidationError({"status": f"Only paused sessions can be resumed; current state is {session.status}."})
        try:
            session = LiveExecutionService.resume_session(session)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        session = self.get_object()
        if session.status != "STOPPED":
            raise ValidationError({"status": f"Only stopped sessions can be started; current state is {session.status}."})
        try:
            session = LiveExecutionService.resume_session(session)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(session).data)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        session = self.get_object()
        close_positions = bool(request.data.get("close_positions"))
        if session.status == "STOPPED" and not close_positions:
            return Response(self.get_serializer(session).data)
        if session.status not in {"RUNNING", "PAUSED", "ERROR", "STOPPING", "STOPPED"}:
            raise ValidationError({"status": f"Cannot stop a session in {session.status} state."})
        if session.status == "STOPPING":
            raise ValidationError({"status": "Session is already stopping; reconcile broker state before sending another close request."})
        session = LiveExecutionService.stop_session(session, close_positions=close_positions)
        return Response(self.get_serializer(session).data)


    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """
        Manual sync endpoint. Updated to use new BrokerReconciliationService.
        """
        session = self.get_object()
        from live_trading.reconciliation_service import BrokerReconciliationService
        
        try:
            reconciliation_service = BrokerReconciliationService(session)
            orders_result = reconciliation_service.reconcile_orders()
            # positions_result = reconciliation_service.reconcile_positions()
            
            return Response({
                "synced_orders": orders_result.get("matched", 0) + orders_result.get("created", 0),
                # "synced_positions": positions_result.get("updated", 0) + positions_result.get("created", 0),
                "account_state": {
                    "orders": orders_result,
                    "positions": positions_result
                }
            })
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LiveOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LiveOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LiveTradingPagination

    def get_queryset(self):
        queryset = LiveOrder.objects.filter(user=self.request.user).select_related("strategy", "session", "broker_credential", "instrument")
        for field in ("status", "session", "allocation"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{f"{field}_id" if field != "status" else field: value})
        return queryset

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
    pagination_class = LiveTradingPagination

    def get_queryset(self):
        queryset = LivePosition.objects.filter(user=self.request.user, quantity__gt=0).select_related("strategy", "instrument", "broker_credential")
        for field in ("strategy", "allocation", "broker_credential"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{f"{field}_id": value})
        return queryset

    @action(detail=False, methods=["get"])
    def summary(self, request):
        stats = self.get_queryset().aggregate(
            count=Count("id"),
            total_unrealized_pnl=Sum("unrealized_pnl"),
            profitable=Count("id", filter=Q(unrealized_pnl__gt=0)),
            losing=Count("id", filter=Q(unrealized_pnl__lt=0)),
        )
        stats["unrealized_pnl"] = stats.pop("total_unrealized_pnl") or Decimal("0")
        return Response(stats)


class LiveTradeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LiveTradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LiveTradingPagination

    def get_queryset(self):
        queryset = LiveTrade.objects.filter(user=self.request.user).select_related(
            "strategy", "allocation", "broker_credential", "instrument", "exit_order"
        )
        for field in ("strategy", "allocation", "broker_credential"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{f"{field}_id": value})
        return queryset

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
    pagination_class = LiveTradingPagination

    def get_queryset(self):
        queryset = ExecutionLog.objects.filter(order__user=self.request.user).select_related("order", "order__instrument", "order__broker_credential").order_by("-created_at")   
        event_type = self.request.query_params.get("event_type")
        order_id = self.request.query_params.get("order")
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        return queryset


class SlippageRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SlippageRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LiveTradingPagination

    def get_queryset(self):
        queryset = SlippageRecord.objects.filter(order__user=self.request.user).select_related("order", "order__instrument", "order__broker_credential").order_by("-created_at")
        order_id = self.request.query_params.get("order")
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        return queryset


class LiveStrategyAllocationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LiveStrategyAllocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = LiveStrategyAllocation.objects.filter(user=self.request.user).select_related("strategy", "broker_credential", "deployed_version")
        broker_id = self.request.query_params.get("broker_credential")
        if broker_id:
            queryset = queryset.filter(broker_credential_id=broker_id)
        strategy_id = self.request.query_params.get("strategy")
        if strategy_id:
            queryset = queryset.filter(strategy_id=strategy_id)
        return queryset

    @action(detail=True, methods=["post"], url_path="update-allocation")
    def update_allocation(self, request, pk=None):
        allocation = self.get_object()
        allocation = LiveExecutionService.update_allocation(
            allocation=allocation,
            allocation_amount=request.data.get("allocation_amount"),
            allocation_percentage=request.data.get("allocation_percentage"),
        )
        return Response(LiveStrategyAllocationSerializer(allocation).data)

    @action(detail=True, methods=['post'], url_path='deploy-version')
    def deploy_version(self, request, pk=None):
        """Hot-swap the deployed strategy version on a live allocation."""
        allocation = self.get_object()
        version_id = request.data.get('version_id')

        if not version_id:
            return Response(
                {'error': 'version_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from strategies.models import StrategyVersion
            version = StrategyVersion.objects.get(
                id=version_id,
                strategy=allocation.strategy
            )
        except StrategyVersion.DoesNotExist:
            return Response(
                {'error': 'Invalid version for this strategy'},
                status=status.HTTP_404_NOT_FOUND
            )

        allocation.deployed_version = version
        allocation.save(update_fields=['deployed_version', 'updated_at'])

        session = getattr(allocation, "session", None)
        if session and session.status == "RUNNING":
            LiveExecutionService._publish_execution_event("VERSION_CHANGE", session, "live")

        serializer = self.get_serializer(allocation)
        return Response(serializer.data)
