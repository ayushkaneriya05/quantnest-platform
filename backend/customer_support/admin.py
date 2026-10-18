from django.contrib import admin
from django.conf import settings
from django.utils import timezone
from common.admin import ImmutableAdmin
from . import models
from .services import queue_support_email


class ReplyInline(admin.TabularInline):
    model = models.Reply
    extra = 0
    readonly_fields = ["created_at", "author", "staff", "provider_message_id"]
    can_delete = False
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(models.Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "request_type", "status", "assignee", "created_at"]
    list_filter = ["request_type", "status"]
    search_fields = ["subject", "email"]
    inlines = [ReplyInline]
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for reply in instances:
            reply.author, reply.staff = request.user, True
            reply.save()
            models.Ticket.objects.filter(pk=reply.ticket_id).update(status="awaiting_customer", updated_at=timezone.now())
            from .integrations import get_ticket_reply_address
            queue_support_email(to=reply.ticket.email, reply_to=get_ticket_reply_address(reply.ticket),
                subject=f"QuantNest reply: {reply.ticket.subject}", body=reply.body + f"\n\nReference: {reply.ticket_id}\n{settings.QUANTNEST_SUPPORT_EMAIL}")
        formset.save_m2m()


class EngagementAdmin(admin.ModelAdmin):
    list_display = ["ticket", "stage", "delivery_cost_minor", "maintenance_minor"]
    readonly_fields = ["active_slot", "updated_at"]


admin.site.register(models.Engagement, EngagementAdmin)
@admin.register(models.Quotation)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ["id", "engagement", "revision", "total_minor", "currency", "valid_until", "accepted_at"]
    readonly_fields = ["revision", "approved_by", "accepted_at", "scope_snapshot"]
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in obj._meta.fields] if obj else self.readonly_fields
    def save_model(self, request, obj, form, change):
        obj.approved_by = request.user
        super().save_model(request, obj, form, change)
        ticket = obj.engagement.ticket
        queue_support_email(to=ticket.email,
            subject=f"QuantNest quotation ready: {ticket.subject}",
            body=f"Quotation #{obj.pk}, revision {obj.revision}, is ready for your review.\n"
                f"Sign in with {ticket.email} at {settings.FRONTEND_URL.rstrip('/')}/support to review its scope, total and terms.\n"
                "Acceptance and milestone payments are completed in your workspace.")
    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and obj is None
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ["quotation", "sequence", "title", "amount_minor", "approved_for_payment", "paid_at"]
    readonly_fields = ["quotation", "sequence", "title", "amount_minor", "payment_attempt", "paid_at"]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
for model in [models.Consent, models.EmailEvent]:
    admin.site.register(model, ImmutableAdmin)
admin.site.register(models.ErasureRequest, ImmutableAdmin)
