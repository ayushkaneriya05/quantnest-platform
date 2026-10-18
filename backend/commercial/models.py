import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class CatalogRevision(models.Model):
    revision = models.CharField(max_length=80, unique=True)
    specification = models.JSONField()
    published_at = models.DateTimeField(null=True, blank=True, editable=False)
    is_active = models.BooleanField(default=False, editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["is_active"], condition=Q(is_active=True), name="one_active_catalog")]

    def __str__(self):
        return self.revision

    def clean(self):
        from django.core.exceptions import ValidationError
        from .catalog import validate_catalog_specification
        validate_catalog_specification(self.specification, self.revision)
        if self.pk:
            previous = CatalogRevision.objects.filter(pk=self.pk, published_at__isnull=False).first()
            if previous and (previous.revision != self.revision or previous.specification != self.specification):
                raise ValidationError("Published terms are immutable. Clone this revision to make changes.")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class Subscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    plan = models.CharField(max_length=20, default="explore")
    catalog = models.ForeignKey(CatalogRevision, on_delete=models.PROTECT)
    provider_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    status = models.CharField(max_length=30, default="free")
    period_start = models.DateTimeField(null=True, blank=True)
    paid_through = models.DateTimeField(null=True, blank=True)
    cancel_at_end = models.BooleanField(default=False)
    scheduled_plan = models.CharField(max_length=20, blank=True)
    founding_price_until = models.DateTimeField(null=True, blank=True)
    protected_price_minor = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.catalog_id and self.plan not in self.catalog.specification["plans"]:
            raise ValidationError({"plan": "Choose a plan in the selected purchased catalog."})
        if self.status == "active" and (not self.period_start or not self.paid_through or self.paid_through <= self.period_start):
            raise ValidationError("An active paid period needs its start and a later paid-through time.")


class PriceMapping(models.Model):
    catalog = models.ForeignKey(CatalogRevision, on_delete=models.PROTECT)
    plan = models.CharField(max_length=20)
    provider_plan_id = models.CharField(max_length=100)
    total_minor = models.PositiveIntegerField()
    tax_bps = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["catalog", "plan", "total_minor"], name="unique_catalog_provider_price")]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.plan not in {"build", "pro"} or not self.provider_plan_id.startswith("plan_"):
            raise ValidationError("Choose Build/Pro and the Razorpay plan_ identifier.")
        if self.catalog_id and not self.catalog.published_at:
            raise ValidationError("Publish the catalog before mapping a provider price.")


class PaymentAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=160)
    request_hash = models.CharField(max_length=64)
    catalog = models.ForeignKey(CatalogRevision, on_delete=models.PROTECT)
    plan = models.CharField(max_length=20)
    kind = models.CharField(max_length=20, default="subscription")
    base_minor = models.PositiveIntegerField()
    tax_minor = models.PositiveIntegerField(default=0)
    total_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=25, default="pending")
    provider_order_id = models.CharField(max_length=100, unique=True, null=True)
    provider_subscription_id = models.CharField(max_length=100, unique=True, null=True)
    error_code = models.CharField(max_length=80, blank=True)
    billing_details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "idempotency_key"], name="unique_checkout_request")]
        indexes = [models.Index(fields=["status", "updated_at"], name="checkout_reconcile_idx")]


class RenewalTerms(models.Model):
    """Approved future terms, retained after the provider changes the current plan."""
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT)
    mapping = models.ForeignKey(PriceMapping, on_delete=models.PROTECT)
    effective_after = models.DateTimeField()
    base_minor = models.PositiveIntegerField()
    tax_minor = models.PositiveIntegerField()
    total_minor = models.PositiveIntegerField()
    state = models.CharField(max_length=25, default="preparing")
    created_at = models.DateTimeField(auto_now_add=True)


class Payment(models.Model):
    attempt = models.ForeignKey(PaymentAttempt, on_delete=models.PROTECT, related_name="payments")
    provider_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=25)
    amount_minor = models.PositiveIntegerField()
    fee_minor = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="INR")
    captured_at = models.DateTimeField(null=True)
    applied_at = models.DateTimeField(null=True)
    period_start = models.DateTimeField(null=True)
    period_end = models.DateTimeField(null=True)
    billing_snapshot = models.JSONField(default=dict)


class Invoice(models.Model):
    number = models.CharField(max_length=80, unique=True)
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    snapshot = models.JSONField()
    issued_at = models.DateTimeField(auto_now_add=True)


class RefundRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT)
    reason = models.TextField(max_length=3000)
    status = models.CharField(max_length=25, default="requested")
    provider_id = models.CharField(max_length=100, unique=True, null=True)
    provider_idempotency_key = models.CharField(max_length=100, blank=True, editable=False)
    amount_minor = models.PositiveIntegerField(default=0)
    credit_note = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["payment"], condition=~Q(status="rejected"), name="one_open_refund_per_payment")]


class RefundRecord(models.Model):
    provider_id = models.CharField(max_length=100, unique=True)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT)
    amount_minor = models.PositiveIntegerField()
    status = models.CharField(max_length=25)
    credit_note = models.JSONField(default=dict)
    observed_at = models.DateTimeField(default=timezone.now)


class Dispute(models.Model):
    provider_id = models.CharField(max_length=100, unique=True)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT)
    status = models.CharField(max_length=25)
    amount_minor = models.PositiveIntegerField()
    deducted_minor = models.PositiveIntegerField(default=0)
    respond_by = models.DateTimeField(null=True)
    observed_at = models.DateTimeField(auto_now=True)


class UsageBucket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    feature = models.CharField(max_length=40)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    limit = models.PositiveIntegerField()
    used = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "feature", "period_start"], name="unique_usage_period")]


class UsageReservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.ForeignKey(UsageBucket, on_delete=models.PROTECT, related_name="reservations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=160)
    request_hash = models.CharField(max_length=64)
    amount = models.PositiveIntegerField()
    state = models.CharField(max_length=20, default="reserved")
    resource_type = models.CharField(max_length=40, blank=True)
    resource_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "idempotency_key"], name="unique_usage_request")]
        indexes = [models.Index(fields=["resource_type", "resource_id"], name="usage_resource_idx")]


