import hmac
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from common.enums_view import get_enum_metadata
from .models import ResearchSession, ResearchRun, ResearchAction
from .serializers import ResearchSessionSerializer, ResearchRunSerializer, RunRequestSerializer, ResearchActionSerializer
from .services import ACTIVE, publish_run, update_active_run
from .context import resolve_context
from .actions import propose_action, confirm_action
from .validation import json_data
from .tools import execute_tool, _screen_config
from .presets import screening_presets
from .evaluation import SCREEN_OPERAND_TYPES


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

    def perform_destroy(self, instance):
        if instance.runs.filter(status__in=ACTIVE).exists():
            raise ValidationError("Cancel the active turn before deleting this conversation.")
        instance.delete()

    @transaction.atomic
    def perform_update(self, serializer):
        if "kind" in serializer.validated_data:
            get_user_model().objects.select_for_update().get(pk=self.request.user.pk)
            serializer.instance.refresh_from_db(fields=["kind"])
        if serializer.instance.kind == "SCREEN" and serializer.validated_data.get("kind") == "CHAT":
            raise ValidationError("Saved screens keep their type. Delete a screen to release its saved-screen capacity.")
        if serializer.instance.kind != "SCREEN" and serializer.validated_data.get("kind") == "SCREEN":
            from commercial.usage import require_inventory_capacity
            require_inventory_capacity(self.request.user, saved_screens=1)
        serializer.save()


class ResearchRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ResearchRunSerializer
    pagination_class = ResearchPagination

    def get_throttles(self):
        if self.action == "create":
            from .throttles import ResearchAdmissionThrottle
            return [ResearchAdmissionThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        queryset = ResearchRun.objects.filter(user=self.request.user).prefetch_related("actions")
        if self.action == "list":
            if self.request.query_params.get("session"):
                queryset = queryset.filter(session_id=self.request.query_params["session"])
            if self.request.query_params.get("active") == "true":
                queryset = queryset.filter(status__in=ACTIVE)
            return queryset.order_by("-created_at", "-id")
        return queryset

    def create(self, request):
        serializer = RunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            previous = ResearchRun.objects.filter(user=request.user, request_id=data["request_id"]).first()
            if previous:
                from commercial.usage import hash_payload, reject_request
                if previous.request.get("_request_hash") != hash_payload(request.data):
                    reject_request("idempotency_conflict", "This research request identifier was already used with different inputs.")
                return Response(ResearchRunSerializer(previous).data)
            if ResearchRun.objects.filter(user=request.user, status__in=ACTIVE).exists():
                raise ValidationError("Wait for your active research turn or cancel it before starting another.")
            session = get_object_or_404(ResearchSession, pk=data["session"], user=request.user) if data.get("session") else None
            context = resolve_context(request.user, data, session.context if session else None)
            context["refresh"] = data["refresh"]
            from commercial.usage import hash_payload
            context["_request_hash"] = hash_payload(request.data)
            from commercial.usage import (
                reserve_usage,
                require_request_limits,
                require_inventory_capacity,
            )
            policy = require_request_limits(request.user, research_instruments=len(context.get("instrument_ids", [])),
                                            backtest_attachments=len(context.get("backtest_ids", [])))
            if data["mode"] == "SCREEN" and (not session or session.kind != "SCREEN"):
                require_inventory_capacity(request.user, policy=policy, saved_screens=1)
            feature = "screens" if data["mode"] == "SCREEN" else "research_turns"
            if session:
                previous_draft = session.runs.filter(status="COMPLETED", result__has_key="draft").order_by("-id").first()
                if previous_draft:
                    context["draft_context"] = {"run_id": previous_draft.pk,
                        "evidence_id": previous_draft.result.get("draft_evidence_id"), "draft": previous_draft.result["draft"]}
            if data["mode"] == "SCREEN":
                if not context["instrument_ids"]:
                    raise ValidationError("Select a watchlist or stocks to screen.")
                screen = _screen_config(data["screen"])
                group = screen["rule_groups"][0]
                context["screen"] = {"timeframe": screen["time_rule"]["candle_timeframe"],
                                     "logical_operator": group["logical_operator"], "conditions": group["rules"]}
                context["timeframe"] = context["screen"]["timeframe"]
            if not session:
                session = ResearchSession.objects.create(user=request.user,
                    kind="SCREEN" if data["mode"] == "SCREEN" else "CHAT", title=(data.get("prompt") or "Market screen")[:160])
            elif data["mode"] == "SCREEN" and session.kind != "SCREEN":
                session.kind = "SCREEN"
            run = ResearchRun.objects.create(session=session, user=request.user, request_id=data["request_id"],
                mode=data["mode"], prompt=data.get("prompt", ""), request=json_data(context), as_of=timezone.now())
            reserve_usage(request.user, feature, f"research:{data['request_id']}", {"request": request.data}, resource=run, policy=policy)
            session.context = json_data({key: context[key] for key in
                ("strategy_id", "backtest_ids", "instrument_ids", "instruments", "timeframe", "use_watchlist", "screen", "source_run_id", "execution_review", "execution_evidence") if key in context})
            session.save(update_fields=["context", "kind", "updated_at"])
            publish_run(run)
            from commercial.usage import queue_compute_work
            queue_compute_work("research.start_research", run.pk)
        run.refresh_from_db()
        return Response(ResearchRunSerializer(run).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        run = self.get_object()
        run = update_active_run(run.pk, status=ResearchRun.Status.CANCELLED,
            progress_message="Research cancelled", completed_at=timezone.now() if not run.started_at else None) or self.get_object()
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
        action = propose_action(self.get_object().pk, request.user, request.data.get("action_type"), request.data.get("payload", {}))
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
    from strategies.models import Strategy
    from django.db.models import F
    today = timezone.localdate()
    from commercial.usage import get_account_policy
    allowances = get_account_policy(request.user)["limits"]
    return Response({"enums": get_enum_metadata(), "presets": screening_presets(),
        "screen_operand_types": SCREEN_OPERAND_TYPES,
        "limits": {"instruments": allowances.get("research_instruments"), "backtests": allowances.get("backtest_attachments"), "tool_calls": 8, "timeout_seconds": 600},
        "defaults": {"timeframe": "1D"},
        "backtest_defaults": {"name": "Research experiment", "start_date": today.replace(month=1, day=1).isoformat(),
                              "end_date": today.isoformat(), "initial_capital": "100000.00", "slippage_pct": "0.05", "include_charges": True},
        "charge_profiles": list(BrokerChargeProfile.objects.filter(user=request.user).values("id", "name", "is_default")),
        "strategies": list(Strategy.objects.filter(user=request.user).values("id", "name", timeframe=F("time_rule__candle_timeframe"))),
        "service_configured": bool(settings.RESEARCH_SERVICE_TOKEN)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def research_tool(request):
    secret = settings.RESEARCH_SERVICE_TOKEN
    if not secret or not hmac.compare_digest(request.headers.get("X-Research-Service-Token", ""), secret):
        raise PermissionDenied("Invalid research service credentials.")
    try:
        scope = signing.loads(request.headers.get("X-Research-Run-Token", ""), salt="research-run", max_age=600)
    except signing.BadSignature:
        raise PermissionDenied("Invalid or expired research run token.")
    run = get_object_or_404(ResearchRun, pk=scope["run_id"], user_id=scope["user_id"], status=ResearchRun.Status.RUNNING)
    if not run.started_at or (timezone.now() - run.started_at).total_seconds() > 600:
        raise PermissionDenied("Research deadline exceeded.")
    evidence = execute_tool(run, request.data.get("name"), request.data.get("arguments", {}))
    # Charts stay in backend artifacts; the language model needs observations, not every chart point.
    data = evidence["data"]
    if data.get("rows"):
        data = {**data, "rows": [{key: value for key, value in row.items() if key not in {"chart", "coverage"}} for row in data["rows"]]}
    return Response({**evidence, "data": data})
