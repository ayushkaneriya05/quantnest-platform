from django.contrib import admin

from .models import AuditLog, ComplianceCheck, StrategyApproval


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "action", "entity_type", "entity_name", "timestamp"]
    list_filter = ["action", "entity_type"]


@admin.register(StrategyApproval)
class StrategyApprovalAdmin(admin.ModelAdmin):
    list_display = ["id", "strategy", "requested_by", "approved_by", "status", "requested_at", "decided_at"]
    list_filter = ["status"]


@admin.register(ComplianceCheck)
class ComplianceCheckAdmin(admin.ModelAdmin):
    list_display = ["id", "strategy", "check_type", "passed", "checked_at"]
    list_filter = ["passed", "check_type"]
