from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class AuditLog(BaseTimestampModel):
    ACTIONS = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("DEPLOY", "Deploy"),
        ("PAUSE", "Pause"),
        ("STOP", "Stop"),
        ("APPROVE", "Approve"),
        ("REJECT", "Reject"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=20, choices=ACTIONS)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=80, blank=True)
    entity_name = models.CharField(max_length=255, blank=True)
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=128, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]


class StrategyApproval(BaseTimestampModel):
    STATUSES = [("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")]

    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="approvals")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategy_approval_requests")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="strategy_approvals_given")
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    comments = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "strategy_approval"
        ordering = ["-requested_at"]


class ComplianceCheck(BaseTimestampModel):
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="compliance_checks")
    check_type = models.CharField(max_length=80)
    passed = models.BooleanField(default=True)
    details = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "compliance_check"
        ordering = ["-checked_at"]

