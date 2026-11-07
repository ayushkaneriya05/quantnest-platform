from common.pagination import StandardPagination
from django.db.models import Q
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer
from .services import NotificationService


class NotificationViewSet(mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    pagination_class = StandardPagination
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        if self.action == 'list':
            search = self.request.query_params.get('search', '')[:100]
            if search:
                qs = qs.filter(Q(title__icontains=search) | Q(message__icontains=search))
            state = self.request.query_params.get('filter', 'all')
            from rest_framework.fields import ChoiceField
            state = ChoiceField(choices=['all', 'unread', 'read']).run_validation(state)
            if state != 'all':
                qs = qs.filter(is_read=state == 'read')
            if self.request.query_params.get('type'):
                from common.enums import NotificationType
                kind = ChoiceField(choices=NotificationType.choices).run_validation(self.request.query_params['type'])
                qs = qs.filter(type=kind)
        return qs.order_by('-created_at', '-id')

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = NotificationService.mark_read(self.get_object())
        return Response(self.get_serializer(notification).data)

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


class NotificationPreferenceViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_queryset(self):
        NotificationService.ensure_preferences(self.request.user)
        return NotificationPreference.objects.filter(user=self.request.user).order_by("type")
