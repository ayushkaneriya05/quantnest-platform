from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from analytics.views import TradePagination
from .models import AuditLog
from common.enums import ActivityResource
from .serializers import AuditLogSerializer


class ActivityFilters(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=100, allow_blank=True)
    action = serializers.ChoiceField(choices=[value for value, label in AuditLog.ACTIONS], required=False)
    entity_type = serializers.ChoiceField(choices=ActivityResource.choices, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, data):
        if data.get("date_from") and data.get("date_to") and data["date_from"] > data["date_to"]:
            raise serializers.ValidationError("The start date must be before the end date.")
        return data


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AuditLogSerializer
    pagination_class = TradePagination

    def get_queryset(self):
        qs = AuditLog.objects.filter(user=self.request.user)
        if self.action not in {"list", "stats"}:
            return qs
        filters = ActivityFilters(data=self.request.query_params.dict())
        filters.is_valid(raise_exception=True)
        data = filters.validated_data
        for field in ("action", "entity_type"):
            if field in data:
                qs = qs.filter(**{field: data[field]})
        if data.get("search"):
            qs = qs.filter(Q(entity_name__icontains=data["search"]) | Q(reason__icontains=data["search"]))
        if data.get("date_from"):
            qs = qs.filter(timestamp__date__gte=data["date_from"])
        if data.get("date_to"):
            qs = qs.filter(timestamp__date__lte=data["date_to"])
        return qs

    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = self.get_queryset()
        return Response({"events": qs.count(), "today": qs.filter(timestamp__date=timezone.localdate()).count(),
                         "actions": [{"value": value, "label": label} for value, label in AuditLog.ACTIONS],
                         "entity_types": [{"value": value, "label": label} for value, label in ActivityResource.choices],
                         "action_breakdown": list(qs.order_by().values("action").annotate(count=Count("id")))})
