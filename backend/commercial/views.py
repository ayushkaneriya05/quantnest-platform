import json
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from . import billing
from copy import deepcopy
from .models import PaymentAttempt, Invoice, PriceMapping
from .provider import ProviderUnavailable
from .usage import get_account_policy, get_account_usage, reject_request


@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])
def get_public_catalog(request):
    from .catalog import LIMIT_LABELS, PLANS, get_active_catalog
    from customer_support.catalog import get_support_specification
    data = deepcopy(get_active_catalog().specification)
    data["features"] = [{key: feature[key] for key in ("code", "name", "documentation", "description")}
                        for feature in data["features"]]
    # JSONB does not preserve object order; use the canonical catalog plan order.
    data["plans"] = {code: data["plans"][code] for code in PLANS}
    for unused in ("data_source", "broker", "research_budget"):
        data.pop(unused, None)
    data["support"] = get_support_specification()
    data["limit_labels"] = LIMIT_LABELS
    data["checkout_available"] = settings.BILLING_ENABLED
    for plan in data["plans"].values():
        plan["checkout_available"] = bool(data["checkout_available"])
    data["tax_bps"] = settings.BILLING_TAX_BPS
    data["live"] = "not-offered"  # Override old published catalog marketing without changing purchased terms.
    data["execution_enabled_scopes"] = sorted(settings.EXECUTION_ENABLED_SCOPES)
    data["contact"] = {"name": settings.QUANTNEST_LEGAL_NAME, "email": settings.QUANTNEST_SUPPORT_EMAIL,
                       "hours": settings.QUANTNEST_SUPPORT_HOURS}
    return Response(data)


class AccountView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        policy = get_account_policy(request.user)
        data = get_account_usage(request.user, policy=policy)
        data["invoices"] = list(Invoice.objects.filter(user=request.user).order_by("-issued_at").values("id", "number", "snapshot", "issued_at")[:50])
        data["checkouts"] = [billing.get_checkout_data(row) for row in PaymentAttempt.objects.filter(user=request.user).select_related("catalog").order_by("-created_at")[:10]]
        from .catalog import get_active_catalog
        # Quote the active catalog in every workspace; checkout availability is separate.
        active = policy["catalog"]
        if active is None or not active.is_active:
            active = get_active_catalog()
        data["checkout_terms"] = {code: billing.calculate_billing_totals(active, code, policy["subscription"]) for code in ("build", "pro")}
        mappings = set(PriceMapping.objects.filter(catalog=active, tax_bps=settings.BILLING_TAX_BPS)
                       .values_list("plan", "total_minor"))
        for code, totals in data["checkout_terms"].items():
            totals["automatic_renewal_available"] = settings.BILLING_ENABLED and (code, totals["total_minor"]) in mappings
        return Response(data)


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    manual = False
    def post(self, request):
        attempt = billing.create_checkout(request.user, request.data, request.headers.get("Idempotency-Key"), manual=self.manual)
        return Response(billing.get_checkout_data(attempt), status=202 if attempt.status == "creating" else 200)


class RenewalView(CheckoutView):
    manual = True


class PaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    def post(self, request):
        payment_id = request.data.get("payment_id", "")
        if not isinstance(payment_id, str) or not payment_id.startswith("pay_") or len(payment_id) > 100:
            reject_request("invalid_payment", "Provide the payment identifier returned by Checkout.")
        payment = billing.verify_payment(payment_id, user=request.user)
        return Response({"status": payment.status, "applied": bool(payment.applied_at)})


class CancelView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        billing.cancel_subscription_renewal(request.user)
        return Response(get_account_usage(request.user))


class ChangeView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        billing.schedule_plan_change(request.user, request.data.get("plan"), request.data.get("approved_total_minor"))
        return Response(get_account_usage(request.user))


class RefundView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(list(request.user.refundrequest_set.values("id", "payment__provider_id", "reason", "status", "amount_minor", "credit_note", "created_at")))
    def post(self, request):
        row = billing.request_refund(request.user, request.data.get("payment_id"), request.data.get("reason", ""))
        return Response({"id": row.pk, "status": row.status}, status=201)


class InvoiceView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, pk):
        row = get_object_or_404(Invoice, pk=pk, user=request.user)
        if request.query_params.get("download") == "html":
            from .invoices import render_invoice_html
            return render_invoice_html(row)
        response = Response({"number": row.number, "issued_at": row.issued_at, **row.snapshot})
        response["Cache-Control"] = "no-store"
        return response


class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    def post(self, request):
        body = request.body
        if len(body) > 262144 or not billing.is_webhook_signature_valid(body, request.headers.get("X-Razorpay-Signature", "")):
            return Response({"code": "invalid_webhook_signature"}, status=403)
        try:
            payload = json.loads(body)
            event_type = payload["event"]
            entities = payload.get("payload", {})
            if not isinstance(event_type, str) or not event_type or len(event_type) > 80 or not isinstance(entities, dict):
                raise ValueError()
            for name in ("payment", "refund", "dispute", "subscription"):
                entity = entities.get(name, {})
                if not isinstance(entity, dict) or not isinstance(entity.get("entity", {}), dict):
                    raise ValueError()
        except (ValueError, TypeError, KeyError):
            return Response({"code": "invalid_event"}, status=400)
        try:
            billing.process_payment_webhook(payload)
        except ProviderUnavailable:
            return Response({"code": "payment_provider_unavailable"}, status=503)
        return Response({"received": True})


