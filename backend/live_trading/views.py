from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from brokers.models import BrokerCredential
from strategies.models import Strategy

from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, SlippageRecord, TradingSession
from .serializers import (
    ExecutionLogSerializer,
    LiveOrderSerializer,
    LivePositionSerializer,
    LiveStrategyAllocationSerializer,
    SlippageRecordSerializer,
    TradingSessionSerializer,
)
from .services import LiveExecutionService


class TradingSessionViewSet(viewsets.ModelViewSet):
    serializer_class = TradingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TradingSession.objects.filter(user=self.request.user).select_related("strategy", "broker_credential")

    @action(detail=False, methods=["post"])
    def deploy(self, request):
        strategy = Strategy.objects.get(id=request.data.get("strategy"), user=request.user)
        credential = None
        if request.data.get("broker_credential"):
            credential = BrokerCredential.objects.get(id=request.data["broker_credential"], user=request.user)
        session = LiveExecutionService.deploy_strategy(
            request.user,
            strategy,
            credential,
            allocation_amount=request.data.get("allocation_amount"),
            allocation_percentage=request.data.get("allocation_percentage"),
        )
        return Response(self.get_serializer(session).data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(LiveExecutionService.session_summary(request.user))

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        return Response(self.get_serializer(LiveExecutionService.pause_session(self.get_object())).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        return Response(self.get_serializer(LiveExecutionService.resume_session(self.get_object())).data)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        session = LiveExecutionService.stop_session(self.get_object(), close_positions=bool(request.data.get("close_positions")))
        return Response(self.get_serializer(session).data)

    @action(detail=False, methods=["post"], url_path="stop-all")
    def stop_all(self, request):
        sessions = LiveExecutionService.stop_all_sessions(
            request.user,
            close_positions=bool(request.data.get("close_positions")),
        )
        return Response(self.get_serializer(sessions, many=True).data)

    @action(detail=True, methods=["post"], url_path="run-once")
    def run_once(self, request, pk=None):
        return Response({"processed": LiveExecutionService.execute_session_once(self.get_object(), symbol=request.data.get("symbol"))})

    @action(detail=True, methods=["post"], url_path="update-allocation")
    def update_allocation(self, request, pk=None):
        session = self.get_object()
        allocation = LiveExecutionService.update_allocation(
            request.user,
            session.strategy,
            session.broker_credential,
            allocation_amount=request.data.get("allocation_amount"),
            allocation_percentage=request.data.get("allocation_percentage"),
        )
        return Response(LiveStrategyAllocationSerializer(allocation).data)

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        session = self.get_object()
        result = LiveExecutionService.sync_account_state(request.user, credential=session.broker_credential, force=True)
        orders = LiveExecutionService.sync_open_orders(session, symbol=request.data.get("symbol"), force=True)
        return Response({"synced_orders": len(orders), "account_state": result})


class LiveOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LiveOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LiveOrder.objects.filter(user=self.request.user).select_related("strategy", "session", "portfolio", "broker_credential", "instrument")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = LiveExecutionService.cancel_open_order(self.get_object())
        return Response(self.get_serializer(order).data)


class LivePositionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LivePositionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LivePosition.objects.filter(user=self.request.user).select_related("strategy", "instrument")


class ExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExecutionLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ExecutionLog.objects.filter(order__user=self.request.user).select_related("order", "order__instrument")


class SlippageRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SlippageRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SlippageRecord.objects.filter(order__user=self.request.user).select_related("order", "order__instrument")


class LiveStrategyAllocationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LiveStrategyAllocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = LiveStrategyAllocation.objects.filter(user=self.request.user).select_related("strategy", "broker_credential", "portfolio")
        broker_id = self.request.query_params.get("broker_credential")
        if broker_id:
            queryset = queryset.filter(broker_credential_id=broker_id)
        strategy_id = self.request.query_params.get("strategy")
        if strategy_id:
            queryset = queryset.filter(strategy_id=strategy_id)
        return queryset
