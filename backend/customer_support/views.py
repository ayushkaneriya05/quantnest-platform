import json
import hashlib
import logging
from functools import partial
from django.conf import settings
from django.core import signing
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from core.request_views import ObjectAPIView as APIView, ObjectRequestMixin
from rest_framework.pagination import PageNumberPagination
from commercial.usage import reject_request
from .models import Ticket, Reply, Consent, EmailEvent, Quotation
from .serializers import TicketSerializer, ReplyInput
from .tasks import sync_newsletter_task
from .services import create_milestone_checkout, queue_ticket_acknowledgement
from .integrations import require_form_verification, is_brevo_webhook_authenticated, request_brevo


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


class TicketViewSet(ObjectRequestMixin, viewsets.ReadOnlyModelViewSet):
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


class ConsentView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    def get(self, request):
        subscribed = request.user.is_authenticated and Consent.objects.filter(
            user=request.user, purpose="marketing", state="confirmed").exists()
        return Response({"marketing": subscribed, "policy_revision": settings.PRIVACY_POLICY_REVISION})
    def post(self, request):
        purpose = request.data.get("purpose")
        if type(request.data.get("granted")) is not bool:
            reject_request("invalid_consent", "Choose whether to grant or withdraw this consent.")
        if purpose != "marketing":
            reject_request("invalid_consent", "Only product update email consent is supported.")
        email = request.user.email if request.user.is_authenticated else request.data.get("email", "")
        try:
            validate_email(email)
        except Exception:
            reject_request("invalid_email", "Enter a valid email address.")
        if not request.user.is_authenticated:
            require_form_verification(request.data.get("turnstile_token"), request, "newsletter")
        granted = request.data.get("granted") is True
        if not granted and not request.user.is_authenticated:
            reject_request("withdrawal_token_required", "Use the unsubscribe link in your email to withdraw consent.")
        if request.data.get("policy_revision") != settings.PRIVACY_POLICY_REVISION:
            reject_request("policy_changed", "Review the current privacy notice before consenting.")
        with transaction.atomic():
            consent, _ = Consent.objects.update_or_create(email=email.lower(), purpose=purpose, defaults={
                "user": request.user if request.user.is_authenticated else None,
                "policy_revision": settings.PRIVACY_POLICY_REVISION, "source": "customer-site",
                "state": "pending" if granted else "withdrawn",
                "confirmed_at": None,
                "withdrawn_at": None if granted else timezone.now(), "requested_at": timezone.now()})
            transaction.on_commit(partial(sync_newsletter_task.delay, consent.pk), robust=True)
        return Response({"state": consent.state})


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


class NewsletterConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    def post(self, request):
        try:
            data = signing.loads(request.data.get("token", ""), salt="newsletter-confirm", max_age=86400)
            consent = Consent.objects.get(pk=data["consent_id"], requested_at=data["requested_at"], purpose="marketing", state__in=["pending", "confirmed"])
        except (signing.BadSignature, Consent.DoesNotExist, KeyError, TypeError):
            reject_request("confirmation_invalid", "This confirmation has expired or is no longer pending.")
        if consent.state == "confirmed":
            return Response({"state": "confirmed"})
        from urllib.parse import quote
        contact = request_brevo("GET", "contacts/" + quote(consent.email, safe=""))
        if settings.BREVO_NEWSLETTER_LIST_ID not in contact.get("listIds", []) or contact.get("emailBlacklisted"):
            reject_request("confirmation_pending", "Complete the confirmation link sent by Brevo before continuing.")
        changed = Consent.objects.filter(pk=consent.pk, requested_at=consent.requested_at, state="pending").update(state="confirmed", confirmed_at=timezone.now())
        if not changed and not Consent.objects.filter(pk=consent.pk, requested_at=consent.requested_at, state="confirmed").exists():
            reject_request("confirmation_invalid", "This confirmation was replaced or withdrawn. Request a new email if you want to subscribe.")
        return Response({"state": "confirmed"})


class BrevoWebhookView(APIView):
    allow_list_payload = True
    skip_object_validation = True
    authentication_classes = []
    permission_classes = [AllowAny]
    def post(self, request):
        if not is_brevo_webhook_authenticated(request) or len(request.body) > 262144:
            return Response({"code": "invalid_webhook"}, status=403)
        data = request.data
        rows = data if isinstance(data, list) else [data]
        if len(rows) > 100 or any(not isinstance(item, dict) for item in rows):
            return Response({"code": "invalid_webhook_payload"}, status=400)
        for item in rows:
            event = str(item.get("event", ""))[:40]
            email = item.get("email", "")
            event_id = hashlib.sha256(json.dumps(item, sort_keys=True, default=str).encode()).hexdigest()
            _, created = EmailEvent.objects.get_or_create(event_id=event_id, defaults={"category": event, "email": email})
            if created and event in {"unsubscribed", "spam", "hard_bounce", "hardBounce"}:
                Consent.objects.filter(email__iexact=email, purpose="marketing").update(state="withdrawn", withdrawn_at=timezone.now())
        return Response({"received": True})


class InboundEmailView(APIView):
    skip_object_validation = True
    authentication_classes = []
    permission_classes = [AllowAny]
    def post(self, request):
        if not is_brevo_webhook_authenticated(request) or len(request.body) > 262144:
            return Response({"code": "invalid_webhook"}, status=403)
        if not isinstance(request.data, dict):
            return Response({"code": "invalid_webhook_payload"}, status=400)
        rows = request.data.get("items", [])
        if not isinstance(rows, list) or len(rows) > 20 or any(not isinstance(item, dict) for item in rows):
            return Response({"code": "invalid_webhook_payload"}, status=400)
        for item in rows:
            # Only signed Reply-To addresses identify tickets. Sender text is not an account credential.
            recipients = item.get("To", [])
            if isinstance(recipients, str):
                recipients = [{"Address": recipients}]
            if not isinstance(recipients, list):
                continue
            for recipient in recipients:
                if not isinstance(recipient, dict):
                    continue
                address = recipient.get("Address", "")
                from .integrations import get_ticket_from_reply_address
                ticket = get_ticket_from_reply_address(address)
                if not ticket:
                    continue
                sender = item.get("From", {})
                sender = sender.get("Address", "") if isinstance(sender, dict) else sender
                if not isinstance(sender, str) or sender.casefold() != ticket.email.casefold() or ticket.status == "closed":
                    continue
                body = str(item.get("RawTextBody") or item.get("ExtractedMarkdownMessage") or "")[:10000]
                identity = item.get("MessageId") or json.dumps(item, sort_keys=True, default=str)
                message_id = hashlib.sha256((str(identity) + str(ticket.pk)).encode()).hexdigest()
                if body:
                    with transaction.atomic():
                        _, created = Reply.objects.get_or_create(provider_message_id=message_id, defaults={"ticket": ticket, "body": body, "staff": False})
                        if created:
                            Ticket.objects.filter(pk=ticket.pk).update(status="awaiting_support", updated_at=timezone.now())
        return Response({"received": True})


class QuoteAcceptView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        quote = get_object_or_404(Quotation, pk=pk, engagement__ticket__user=request.user)
        return Response({"id": quote.pk, "revision": quote.revision, "total_minor": quote.total_minor, "currency": quote.currency,
            "terms": quote.terms, **quote.scope_snapshot,
            "valid_until": quote.valid_until, "accepted_at": quote.accepted_at,
            "milestones": list(quote.milestones.values("id", "sequence", "title", "amount_minor", "approved_for_payment", "paid_at"))})
    def post(self, request, pk):
        from .models import Milestone
        with transaction.atomic():
            quote = get_object_or_404(Quotation.objects.select_for_update(), pk=pk, engagement__ticket__user=request.user)
            if quote.valid_until <= timezone.now() and not quote.accepted_at:
                reject_request("quotation_expired", "Request an updated quotation.")
            if not quote.accepted_at:
                if request.data.get("accepted") is not True:
                    reject_request("acceptance_required", "Confirm that you accept the quotation's scope and commercial terms.")
                from .models import Engagement
                engagement = Engagement.objects.select_for_update().get(pk=quote.engagement_id)
                if Quotation.objects.filter(engagement=engagement, accepted_at__isnull=False).exclude(pk=quote.pk).exists():
                    reject_request("quote_already_accepted", "This engagement already has an accepted quotation. Agree a change request separately.")
                engagement.stage = "accepted"
                try:
                    with transaction.atomic():
                        engagement.save(update_fields=["stage", "updated_at"])
                except IntegrityError:
                    reject_request("project_capacity", "Another project has just been accepted. Contact support for the next available delivery slot.")
                quote.accepted_at = timezone.now()
                quote.save(update_fields=["accepted_at"])
                first = quote.total_minor * 40 // 100
                amounts = [("Commencement", first), ("Acceptance milestone", first), ("Handover", quote.total_minor - first * 2)]
                Milestone.objects.bulk_create(Milestone(quotation=quote, sequence=i, title=title, amount_minor=amount)
                                              for i, (title, amount) in enumerate(amounts, 1))
        return Response({"accepted_at": quote.accepted_at})


class MilestoneCheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        from commercial.billing import get_checkout_data
        attempt = create_milestone_checkout(request.user, pk, request.data, request.headers.get("Idempotency-Key", ""))
        return Response(get_checkout_data(attempt))


class QuoteListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(list(Quotation.objects.filter(engagement__ticket__user=request.user).order_by("-pk").values("id", "revision", "total_minor", "currency", "valid_until", "accepted_at")[:50]))
