import hmac

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import (
    action,
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .actions import confirm_action, propose_action
from .evaluation import SCREEN_OPERAND_TYPES
from .models import ACTIVE_RUN_STATUSES, ResearchAction, ResearchRun, ResearchSession
from .serializers import (
    ResearchActionSerializer,
    ResearchRunSerializer,
    ResearchSessionSerializer,
    RunRequestSerializer,
)
from .services import accept_run, update_active_run
from .tool_registry import execute_tool


class ResearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


class ResearchSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ResearchSessionSerializer
    pagination_class = ResearchPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = ResearchSession.objects.filter(user=self.request.user)
        if self.action == "list":
            if self.request.query_params.get("search"):
                queryset = queryset.filter(title__icontains=self.request.query_params["search"])
            if self.request.query_params.get("kind"):
                queryset = queryset.filter(kind=self.request.query_params["kind"])
        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            if serializer.validated_data.get("kind") == "SCREEN":
                from commercial.usage import require_inventory_capacity

                require_inventory_capacity(self.request.user, saved_screens=1)
            serializer.save(user=self.request.user)

    @transaction.atomic
    def perform_destroy(self, instance):
        get_user_model().objects.select_for_update().get(pk=self.request.user.pk)
        if instance.runs.filter(status__in=ACTIVE_RUN_STATUSES).exists():
            raise ValidationError("Cancel the active turn before deleting this conversation.")
        instance.delete()

    @transaction.atomic
    def perform_update(self, serializer):
        if "kind" in serializer.validated_data:
            get_user_model().objects.select_for_update().get(pk=self.request.user.pk)
            serializer.instance.refresh_from_db(fields=["kind"])
        if serializer.instance.kind == "SCREEN" and serializer.validated_data.get("kind") == "CHAT":
            raise ValidationError(
                "Saved screens keep their type. Delete a screen to release its saved-screen capacity."
            )
        if serializer.instance.kind != "SCREEN" and serializer.validated_data.get("kind") == "SCREEN":
            from commercial.usage import require_inventory_capacity

            require_inventory_capacity(self.request.user, saved_screens=1)
        serializer.save()


class ResearchRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ResearchRunSerializer
    pagination_class = ResearchPagination

    def get_queryset(self):
        queryset = ResearchRun.objects.filter(user=self.request.user).prefetch_related("actions")
        if self.action == "list":
            if self.request.query_params.get("session"):
                queryset = queryset.filter(session_id=self.request.query_params["session"])
            if self.request.query_params.get("active") == "true":
                queryset = queryset.filter(status__in=ACTIVE_RUN_STATUSES)
            return queryset.order_by("-created_at", "-id")
        return queryset

    def create(self, request):
        serializer = RunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        run, created = accept_run(request.user, data, request.data)
        return Response(ResearchRunSerializer(run).data, status=202 if created else 200)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        run = self.get_object()
        run = (
            update_active_run(
                run.pk,
                status=ResearchRun.Status.CANCELLED,
                progress_message="Research cancelled",
                completed_at=timezone.now(),
            )
            or self.get_object()
        )
        return Response(ResearchRunSerializer(run).data)

    @action(detail=True, methods=["get"], url_path="evidence/(?P<evidence_id>E[0-9]+)")
    def evidence(self, request, pk=None, evidence_id=None):
        item = next((value for value in self.get_object().evidence if value["evidence_id"] == evidence_id), None)
        if item is None:
            from rest_framework.exceptions import NotFound

            raise NotFound("Evidence was not recorded for this turn.")
        return Response(item)

    @action(detail=True, methods=["post"], url_path="propose-action")
    def propose(self, request, pk=None):
        action = propose_action(
            self.get_object().pk, request.user, request.data.get("action_type"), request.data.get("payload", {})
        )
        return Response(ResearchActionSerializer(action).data, status=201)


class ResearchActionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ResearchActionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ResearchPagination

    def get_queryset(self):
        return ResearchAction.objects.filter(run__user=self.request.user)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        action = confirm_action(self.get_object().pk, request.user)
        action.refresh_from_db()
        return Response(ResearchActionSerializer(action).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def research_schema(request):
    from brokers.models import BrokerChargeProfile

    today = timezone.localdate()
    from commercial.usage import get_account_policy

    allowances = get_account_policy(request.user)["limits"]
    return Response(
        {
            "screen_operand_types": SCREEN_OPERAND_TYPES,
            "limits": {
                "instruments": allowances.get("research_instruments"),
                "backtests": allowances.get("backtest_attachments"),
                "tool_calls": settings.RESEARCH_MAX_TOOL_CALLS,
                "timeout_seconds": settings.RESEARCH_TIMEOUT_SECONDS,
            },
            "defaults": {"timeframe": "1D"},
            "backtest_defaults": {
                "name": "Research experiment",
                "start_date": today.replace(month=1, day=1).isoformat(),
                "end_date": today.isoformat(),
                "initial_capital": "100000.00",
                "slippage_pct": "0.05",
                "include_charges": True,
            },
            "default_charge_profile": BrokerChargeProfile.objects.filter(user=request.user, is_default=True)
            .values_list("id", flat=True)
            .first(),
            "service_configured": bool(settings.RESEARCH_SERVICE_TOKEN),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def allowance(request):
    from .services import research_allowance

    return Response(research_allowance(request.user))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def research_tool(request):
    secret = settings.RESEARCH_SERVICE_TOKEN
    if not secret or not hmac.compare_digest(request.headers.get("X-Research-Service-Token", ""), secret):
        raise PermissionDenied("Invalid research service credentials.")
    try:
        scope = signing.loads(
            request.headers.get("X-Research-Run-Token", ""),
            salt="research-run",
            max_age=settings.RESEARCH_TIMEOUT_SECONDS,
        )
    except signing.BadSignature:
        raise PermissionDenied("Invalid or expired research run token.")
    run = get_object_or_404(
        ResearchRun, pk=scope["run_id"], user_id=scope["user_id"], status=ResearchRun.Status.RUNNING
    )
    if not run.started_at or (timezone.now() - run.started_at).total_seconds() > settings.RESEARCH_TIMEOUT_SECONDS:
        raise PermissionDenied("Research deadline exceeded.")
    evidence = execute_tool(run, request.data.get("name"), request.data.get("arguments", {}))
    from .tool_registry import compact_evidence

    return Response(compact_evidence(evidence))
