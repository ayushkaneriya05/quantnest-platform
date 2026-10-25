from copy import deepcopy
from functools import partial
from decimal import Decimal
from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from common.admin import ImmutableAdmin
from .catalog import (
    LIMIT_LABELS,
    LIMIT_DIVISORS,
    PLANS,
    publish_catalog,
    get_catalog_specification,
    validate_catalog_specification,
)
from . import models


class CatalogForm(forms.ModelForm):
    """Ordinary form fields keep plan editing out of Python and raw JSON."""

    class Meta:
        model = models.CatalogRevision
        fields = ["revision"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.instance.specification or get_catalog_specification()
        for code in PLANS:
            plan = data["plans"][code]
            self.fields[f"{code}_name"] = forms.CharField(label="Customer name", initial=plan["name"], max_length=80)
            self.fields[f"{code}_price"] = forms.IntegerField(label="Monthly price (paise)", initial=plan["price_minor"], min_value=0,
                help_text="49900 means ₹499. Explore must remain 0.")
            for key, label in LIMIT_LABELS.items():
                divisor = LIMIT_DIVISORS[key]
                self.fields[f"{code}_{key}"] = forms.DecimalField(label=label,
                    initial=Decimal(plan["limits"].get(key, 0)) / divisor, min_value=0,
                    decimal_places=3 if divisor > 1 else 0,
                    help_text=f"One credit = {divisor:,} reported AI tokens." if divisor > 1 else "")
        self.fields["credit_candles"] = forms.IntegerField(label="Source candles per backtest credit", min_value=1, initial=data["credit_candles"],
            help_text="Existing approved previews retain their saved unit when work settles.")

    def clean(self):
        values = super().clean()
        if self.errors or self.instance.published_at:
            return values
        data = deepcopy(self.instance.specification or get_catalog_specification())
        data["revision"] = values["revision"]
        for code in PLANS:
            data["plans"][code].update(name=values[f"{code}_name"], price_minor=values[f"{code}_price"],
                limits={key: int(values[f"{code}_{key}"] * LIMIT_DIVISORS[key]) for key in LIMIT_LABELS})
        data["credit_candles"] = values["credit_candles"]
        validate_catalog_specification(data, values["revision"])
        self.instance.specification = data
        return values


@admin.register(models.CatalogRevision)
class CatalogAdmin(admin.ModelAdmin):
    form = CatalogForm
    list_display = ["revision", "is_active", "published_at"]
    readonly_fields = ["is_active", "published_at", "specification"]
    actions = ["clone_revision", "activate_revision"]

    def get_form(self, request, obj=None, **kwargs):
        # Declare the generated fields before Django builds its ModelForm;
        # __init__ then fills their values from this revision's snapshot.
        fields = CatalogForm(instance=obj).fields
        kwargs["form"] = type("CatalogEditor", (CatalogForm,), dict(fields))
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if obj and obj.published_at:
            return [("Published snapshot", {"fields": ["revision", "is_active", "published_at", "specification"],
                "description": "Clone this revision, edit the draft, then publish it. Existing paid periods keep their purchased snapshot."})]
        sections = [("Draft revision", {"fields": ["revision", "credit_candles"],
            "description": "Save, then select Publish selected revision from the catalog list. No code change or restart is needed."})]
        sections += [(PLANS[code]["name"], {"fields": [f"{code}_name", f"{code}_price", *[f"{code}_{key}" for key in LIMIT_LABELS]]}) for code in PLANS]
        return sections

    def get_readonly_fields(self, request, obj=None):
        return [*self.readonly_fields, "revision"] if obj and obj.published_at else self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return obj is not None and obj.published_at is None

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (obj is None or obj.published_at is None)

    @admin.action(description="Clone selected revision as an editable draft", permissions=["change"])
    def clone_revision(self, request, queryset):
        for original in queryset:
            revision = f"{original.revision[:35]}-{timezone.now():%Y%m%d%H%M%S%f}"
            data = deepcopy(original.specification)
            data["revision"] = revision
            for plan in data["plans"].values():
                plan["limits"] = {key: plan["limits"].get(key, 0) for key in LIMIT_LABELS}
            models.CatalogRevision.objects.create(revision=revision, specification=data)
        self.message_user(request, "Draft created. Open it, edit the plan fields, save, then publish it.", messages.SUCCESS)

    @admin.action(description="Publish selected revision for new purchases and Explore", permissions=["change"])
    def activate_revision(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one revision to publish.", messages.ERROR)
            return
        publish_catalog(queryset.get())
        self.message_user(request, "Catalog published. Explore and new checkouts use it; existing paid periods keep their snapshot.", messages.SUCCESS)


@admin.register(models.RefundRequest)
class RefundAdmin(admin.ModelAdmin):
    list_display = ["user", "payment", "status", "amount_minor", "created_at"]
    readonly_fields = [field.name for field in models.RefundRequest._meta.fields]
    actions = ["approve_refund", "reject_refund"]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    @admin.action(description="Approve or retry refunds for provider processing", permissions=["change"])
    def approve_refund(self, request, queryset):
        from .tasks import process_refund_task
        for row in queryset:
            with transaction.atomic():
                row = models.RefundRequest.objects.select_for_update().get(pk=row.pk)
                if row.status not in {"eligible", "review", "approved", "provider_pending", "pending"}:
                    continue
                if row.status in {"eligible", "review"}:
                    row.status = "approved"
                    row.save(update_fields=["status"])
                transaction.on_commit(partial(process_refund_task.delay, row.pk))
        self.message_user(request, "Refunds queued. Provider processing is authoritative.", messages.SUCCESS)

    @admin.action(description="Reject selected requests awaiting review", permissions=["change"])
    def reject_refund(self, request, queryset):
        queryset.filter(status__in=["eligible", "review"]).update(status="rejected")
        self.message_user(request, "Unsubmitted requests rejected. Provider refunds were not changed.", messages.SUCCESS)


for model in [models.Payment, models.Invoice, models.UsageReservation,
              models.RenewalTerms, models.UsageBucket, models.RefundRecord, models.Dispute]:
    admin.site.register(model, ImmutableAdmin)
@admin.register(models.Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "paid_through", "cancel_at_end"]


class PriceMappingForm(forms.ModelForm):
    class Meta:
        model = models.PriceMapping
        fields = "__all__"

    def clean(self):
        values = super().clean()
        if self.errors:
            return values
        from .provider import request_razorpay, ProviderUnavailable
        try:
            plan = request_razorpay("GET", "plans/" + values["provider_plan_id"])
        except ProviderUnavailable:
            raise forms.ValidationError("The provider plan could not be verified. Check Razorpay configuration before saving.") from None
        if (plan.get("item", {}).get("amount") != values["total_minor"] or plan.get("item", {}).get("currency") != "INR"
                or plan.get("period") != "monthly" or plan.get("interval") != 1):
            raise forms.ValidationError("The provider plan must match this INR total and renew once per month.")
        return values


@admin.register(models.PriceMapping)
class PriceMappingAdmin(admin.ModelAdmin):
    form = PriceMappingForm
    list_display = ["catalog", "plan", "provider_plan_id", "total_minor", "tax_bps"]
    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and obj is None
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.PaymentAttempt)
class PaymentAttemptAdmin(ImmutableAdmin):
    list_display = ["id", "user", "kind", "plan", "status", "updated_at"]
    list_filter = ["status", "kind"]
    actions = ["reconcile_attempts"]
    def has_reconcile_permission(self, request):
        return request.user.has_perm("commercial.change_paymentattempt")
    @admin.action(description="Discover and reconcile selected provider checkouts", permissions=["reconcile"])
    def reconcile_attempts(self, request, queryset):
        from .reconciliation import reconcile_checkout_attempt
        if queryset.count() > 20:
            self.message_user(request, "Select at most 20 checkouts at a time.", messages.ERROR)
            return
        for attempt in queryset:
            try:
                reconcile_checkout_attempt(attempt)
            except Exception as exc:
                self.message_user(request, f"Checkout {attempt.pk}: {type(exc).__name__}. Check provider configuration and retry reconciliation.", messages.ERROR)
        self.message_user(request, "Provider reconciliation finished. No new orders or mandates were created.", messages.INFO)



