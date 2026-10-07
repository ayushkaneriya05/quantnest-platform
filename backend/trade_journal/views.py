from django.db import IntegrityError, transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from analytics.views import TradePagination, request_filters
from .models import JournalEntry
from .serializers import JournalEntrySerializer
from .services import journal_summary


class JournalEntryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = JournalEntrySerializer
    pagination_class = TradePagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = JournalEntry.objects.filter(user=self.request.user)
        if self.action == "list":
            filters = request_filters(self.request)
            qs = qs.filter(source=filters["source"])
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save(user=request.user)
        except IntegrityError:
            return Response({"message": "This trade already has a review. Open it to make changes."}, status=status.HTTP_409_CONFLICT)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        return Response(journal_summary(request.user, request_filters(request)))
