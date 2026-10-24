from django.contrib import admin
from django.conf import settings
from django.utils import timezone
from common.admin import ImmutableAdmin
from . import models
from .services import queue_support_email


class ReplyInline(admin.TabularInline):
    model = models.Reply
    extra = 0
    readonly_fields = ["created_at", "author", "staff"]
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
            queue_support_email(to=reply.ticket.email,
                subject=f"QuantNest reply: {reply.ticket.subject}", body=reply.body + f"\n\nReference: {reply.ticket_id}\n{settings.QUANTNEST_SUPPORT_EMAIL}")
        formset.save_m2m()


admin.site.register(models.ErasureRequest, ImmutableAdmin)
