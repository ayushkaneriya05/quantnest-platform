import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from commercial.usage import reject_request
from .models import Ticket, Reply
from .serializers import TicketSerializer, ReplyInput
from .services import queue_ticket_acknowledgement
from .integrations import require_form_verification


class EnquiryView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    def post(self, request):
        require_form_verification(request.data.get("turnstile_token"), request, "enquiry")
        serializer = TicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            ticket = serializer.save()
            queue_ticket_acknowledgement(ticket)
        return Response({"id": ticket.pk, "status": ticket.status, "message": "Your request has been received."}, status=201)


class TicketPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 20


class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    pagination_class = TicketPagination
    def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user).prefetch_related("replies").order_by("-updated_at", "-pk")
    def create(self, request):
        serializer = self.get_serializer(data={**request.data, "email": request.user.email})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            ticket = serializer.save(user=request.user)
            queue_ticket_acknowledgement(ticket)
        return Response(self.get_serializer(ticket).data, status=201)
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reply(self, request, pk=None):
        ticket = self.get_object()
        serializer = ReplyInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        Reply.objects.create(ticket=ticket, author=request.user, body=serializer.validated_data["body"])
        ticket.status = "awaiting_support"
        ticket.save(update_fields=["status", "updated_at"])
        ticket._prefetched_objects_cache = {}
        return Response(self.get_serializer(ticket).data)


class ClientErrorThrottle(AnonRateThrottle):
    rate = "60/hour"
    scope = "client-errors"


class ClientErrorView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ClientErrorThrottle]

    def post(self, request):
        category = request.data.get("category")
        if set(request.data) != {"category"} or not isinstance(category, str) or category not in {"render_failure", "app_failure", "load_failure"}:
            reject_request("invalid_report", "Only content-free application error categories are accepted.")
        logging.getLogger(__name__).error("Client application error category=%s", category)
        return Response({"received": True})
