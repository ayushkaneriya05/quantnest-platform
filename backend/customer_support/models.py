import uuid
from django.conf import settings
from django.db import models, transaction
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.utils import timezone


from .catalog import REQUEST_TYPES, TICKET_STATUS_LABELS


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    name = models.CharField(max_length=120, blank=True)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    subject = models.CharField(max_length=180)
    body = models.TextField(max_length=10000)
    status = models.CharField(max_length=25, default="received", choices=list(TICKET_STATUS_LABELS.items()))
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_tickets")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} ({self.email})"


class Reply(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    body = models.TextField(max_length=10000)
    staff = models.BooleanField(default=False)
    provider_message_id = models.CharField(max_length=200, unique=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Consent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    purpose = models.CharField(max_length=30)
    policy_revision = models.CharField(max_length=80)
    source = models.CharField(max_length=100)
    state = models.CharField(max_length=20, default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True)
    withdrawn_at = models.DateTimeField(null=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["email", "purpose"], name="unique_contact_consent")]


class EmailEvent(models.Model):
    event_id = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)


class Engagement(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.PROTECT)
    stage = models.CharField(max_length=25, default="requirements", choices=[(value, value.replace('_', ' ').title()) for value in
        ("requirements", "quoted", "accepted", "implementation", "acceptance", "completed", "paused", "cancelled")])
    active_slot = models.PositiveSmallIntegerField(unique=True, null=True, blank=True, editable=False)
    scope = models.TextField()
    acceptance_criteria = models.TextField()
    ownership_terms = models.TextField()
    support_allowance = models.TextField(blank=True)
    change_requests = models.JSONField(default=list, blank=True)
    delivery_cost_minor = models.PositiveIntegerField(default=0)
    maintenance_minor = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Engagement #{self.pk}"
    def clean(self):
        if self.ticket_id and self.ticket.request_type not in {"custom", "private"}:
            raise ValidationError({"ticket": "Select a Custom development or Private deployment request."})
        if not isinstance(self.change_requests, list):
            raise ValidationError({"change_requests": "Enter a list of agreed change requests."})
        if self.stage in {"accepted", "implementation", "acceptance"} and Engagement.objects.filter(active_slot=1).exclude(pk=self.pk).exists():
            raise ValidationError("Finish or pause the active custom project before activating another.")
    def save(self, *args, **kwargs):
        self.active_slot = 1 if self.stage in {"accepted", "implementation", "acceptance"} else None
        fields = kwargs.get("update_fields")
        if fields is not None and "stage" in fields:
            kwargs["update_fields"] = set(fields) | {"active_slot"}
        super().save(*args, **kwargs)


class Quotation(models.Model):
    engagement = models.ForeignKey(Engagement, on_delete=models.PROTECT, related_name="quotes")
    revision = models.PositiveIntegerField(editable=False)
    total_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="INR")
    terms = models.JSONField()
    valid_until = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True, editable=False)
    scope_snapshot = models.JSONField(default=dict, editable=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, editable=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["engagement", "revision"], name="unique_quote_revision")]

    def __str__(self):
        return f"Quotation #{self.pk}, revision {self.revision}"

    def clean(self):
        if self.total_minor is not None and self.total_minor < 3:
            raise ValidationError({"total_minor": "The total must support three positive payment milestones."})
        if self.currency != "INR":
            raise ValidationError({"currency": "Current project checkout supports INR."})
        if not isinstance(self.terms, dict) or not self.terms:
            raise ValidationError({"terms": "Provide the agreed commercial terms as a non-empty object."})
        if self._state.adding and self.valid_until and self.valid_until <= timezone.now():
            raise ValidationError({"valid_until": "Choose a future quotation expiry."})

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.clean()
            with transaction.atomic():
                engagement = Engagement.objects.select_for_update().get(pk=self.engagement_id)
                self.revision = (engagement.quotes.aggregate(latest=Max("revision"))["latest"] or 0) + 1
                self.scope_snapshot = {name: getattr(engagement, name) for name in
                    ("scope", "acceptance_criteria", "ownership_terms", "support_allowance")}
                return super().save(*args, **kwargs)
        previous = Quotation.objects.get(pk=self.pk)
        protected = ("engagement_id", "revision", "total_minor", "currency", "terms", "valid_until", "scope_snapshot", "approved_by_id")
        if any(getattr(previous, name) != getattr(self, name) for name in protected):
            raise ValidationError("Issued quotations are immutable. Issue a new revision for changed scope or terms.")
        if previous.accepted_at and self.accepted_at != previous.accepted_at:
            raise ValidationError("A customer's recorded quotation acceptance cannot be changed.")
        return super().save(*args, **kwargs)

class Milestone(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.PROTECT, related_name="milestones")
    sequence = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=160)
    amount_minor = models.PositiveIntegerField()
    approved_for_payment = models.BooleanField(default=False)
    payment_attempt = models.OneToOneField("commercial.PaymentAttempt", null=True, blank=True, on_delete=models.PROTECT)
    paid_at = models.DateTimeField(null=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["quotation", "sequence"], name="unique_project_milestone")]

    def clean(self):
        if not self.pk:
            return
        previous = Milestone.objects.get(pk=self.pk)
        if previous.payment_attempt_id or previous.paid_at:
            protected = ("quotation_id", "sequence", "title", "amount_minor", "approved_for_payment")
            if any(getattr(previous, name) != getattr(self, name) for name in protected):
                raise ValidationError("A milestone with a checkout keeps its approved terms. Resolve that payment before agreeing changes.")


class ErasureRequest(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
