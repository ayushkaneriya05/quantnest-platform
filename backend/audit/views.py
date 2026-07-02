from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from strategies.models import Strategy

from .models import AuditLog, ComplianceCheck, StrategyApproval
from .serializers import (
    AuditLogSerializer,
    AuditStatsSerializer,
    ComplianceCheckSerializer,
    StrategyApprovalSerializer,
)
from .services import AuditService


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["entity_type", "entity_name", "action"]
    ordering_fields = ["timestamp", "action", "entity_type"]
    ordering = ["-timestamp"]

    def get_queryset(self):
        qs = AuditLog.objects.filter(user=self.request.user).select_related("user")

        # Optional query-param filters
        action_filter = self.request.query_params.get("action")
        if action_filter:
            qs = qs.filter(action=action_filter)

        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        return qs

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Return audit dashboard statistics."""
        user = request.user
        today = timezone.now().date()
        logs_qs = AuditLog.objects.filter(user=user)

        total_logs = logs_qs.count()
        today_logs = logs_qs.filter(timestamp__date=today).count()

        approvals_qs = StrategyApproval.objects.filter(
            Q(requested_by=user) | Q(approved_by=user)
        )
        pending_approvals = approvals_qs.filter(status="PENDING").count()
        approved_count = approvals_qs.filter(status="APPROVED").count()
        rejected_count = approvals_qs.filter(status="REJECTED").count()

        compliance_qs = ComplianceCheck.objects.filter(strategy__user=user)
        total_compliance = compliance_qs.count()
        passed_compliance = compliance_qs.filter(passed=True).count()
        compliance_pass_rate = round((passed_compliance / total_compliance) * 100, 1) if total_compliance > 0 else 0

        # Breakdowns
        action_breakdown = dict(
            logs_qs.values_list("action")
            .annotate(count=Count("id"))
            .values_list("action", "count")
        )
        entity_breakdown = dict(
            logs_qs.values_list("entity_type")
            .annotate(count=Count("id"))
            .values_list("entity_type", "count")
        )

        recent = logs_qs.order_by("-timestamp")[:10]

        data = {
            "total_logs": total_logs,
            "today_logs": today_logs,
            "pending_approvals": pending_approvals,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "total_compliance_checks": total_compliance,
            "compliance_pass_rate": compliance_pass_rate,
            "action_breakdown": action_breakdown,
            "entity_breakdown": entity_breakdown,
            "recent_activity": AuditLogSerializer(recent, many=True).data,
        }
        return Response(data)

    @action(detail=False, methods=["get"])
    def export(self, request):
        """Return all audit logs for the user in a flat list (for CSV export on frontend)."""
        qs = self.get_queryset()[:5000]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class StrategyApprovalViewSet(viewsets.ModelViewSet):
    serializer_class = StrategyApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StrategyApproval.objects.filter(
            Q(requested_by=self.request.user) | Q(approved_by=self.request.user)
        ).select_related("strategy", "requested_by", "approved_by")

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs.order_by("-requested_at")

    def perform_create(self, serializer):
        strategy = Strategy.objects.get(
            id=serializer.validated_data["strategy"].id,
            user=self.request.user,
        )
        serializer.instance = AuditService.request_strategy_approval(
            strategy, self.request.user, serializer.validated_data.get("comments", "")
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        approval = self.get_object()
        if approval.status != "PENDING":
            return Response(
                {"detail": f"Cannot approve — current status is {approval.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = AuditService.decide_approval(
            approval, request.user, "APPROVED", request.data.get("comments", "")
        )
        return Response(self.get_serializer(result).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        approval = self.get_object()
        if approval.status != "PENDING":
            return Response(
                {"detail": f"Cannot reject — current status is {approval.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = AuditService.decide_approval(
            approval, request.user, "REJECTED", request.data.get("comments", "")
        )
        return Response(self.get_serializer(result).data)

    @action(detail=True, methods=["post"], url_path="run-compliance")
    def run_compliance(self, request, pk=None):
        approval = self.get_object()
        checks = AuditService.run_compliance_checks(approval.strategy)
        return Response(ComplianceCheckSerializer(checks, many=True).data)


class ComplianceCheckViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ComplianceCheckSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ComplianceCheck.objects.filter(
            strategy__user=self.request.user
        ).select_related("strategy")

        strategy_id = self.request.query_params.get("strategy")
        if strategy_id:
            qs = qs.filter(strategy_id=strategy_id)

        passed_filter = self.request.query_params.get("passed")
        if passed_filter is not None:
            qs = qs.filter(passed=passed_filter.lower() == "true")

        return qs.order_by("-checked_at")

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Per-strategy compliance summary for all user strategies."""
        strategies = Strategy.objects.filter(user=request.user)
        results = []
        for strat in strategies:
            summary = AuditService.get_compliance_summary(strat)
            summary["strategy_id"] = strat.id
            summary["strategy_name"] = strat.name
            summary["strategy_status"] = strat.status
            summary["strategy_visibility"] = strat.visibility
            results.append(summary)
        return Response(results)
