from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import DailySummaryScheduleSerializer, NotificationPreferenceSerializer, NotificationSerializer
from .services import NotificationService


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related("strategy")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        return Response(self.get_serializer(NotificationService.mark_read(self.get_object())).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        return Response({"marked": NotificationService.mark_all_read(request.user)})

    @action(detail=False, methods=["delete"], url_path="delete-read")
    def delete_read(self, request):
        count, _ = self.get_queryset().filter(is_read=True).delete()
        return Response({"deleted": count})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(NotificationService.summary(request.user))


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        NotificationService.ensure_preferences(self.request.user)
        return NotificationPreference.objects.filter(user=self.request.user).order_by("notification_type")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DailySummaryScheduleViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(DailySummaryScheduleSerializer(NotificationService.get_summary_schedule(request.user)).data)

    def partial_update(self, request, pk=None):
        schedule = NotificationService.get_summary_schedule(request.user)
        serializer = DailySummaryScheduleSerializer(schedule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
