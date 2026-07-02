from django.conf import settings
from django.db import models
from django.utils import timezone

from common.enums import BrokerName, OrderStatus
from common.models import BaseTimestampModel


class BrokerCredential(BaseTimestampModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="broker_credentials",
    )
    broker_name = models.CharField(max_length=20, choices=BrokerName.choices)
    label = models.CharField(max_length=80, blank=True)
    client_id = models.CharField(max_length=120)
    api_key = models.TextField(blank=True)
    api_secret = models.TextField(blank=True)
    totp_secret = models.CharField(max_length=128, blank=True)
    permissions = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    last_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "broker_credential"
        unique_together = ["user", "broker_name", "client_id"]
        ordering = ["-updated_at"]

    def __str__(self):
        return self.label or f"{self.broker_name} - {self.client_id}"


class BrokerSession(BaseTimestampModel):
    credential = models.ForeignKey(
        BrokerCredential,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    token_expiry = models.DateTimeField()
    is_valid = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "broker_session"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.credential.broker_name} session {self.id}"


class OrderSettings(BaseTimestampModel):
    PARTIAL_FILL_ACTIONS = [
        ("ACCEPT", "Accept Partial Fill"),
        ("CANCEL_REMAINING", "Cancel Remaining Quantity"),
        ("RETRY_REMAINING", "Retry Remaining Quantity"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="broker_order_settings",
    )
    default_slippage_pct = models.DecimalField(max_digits=6, decimal_places=3, default=0.10)
    order_timeout_seconds = models.PositiveIntegerField(default=30)
    max_retries = models.PositiveIntegerField(default=2)
    retry_delay_ms = models.PositiveIntegerField(default=500)
    partial_fill_action = models.CharField(
        max_length=20,
        choices=PARTIAL_FILL_ACTIONS,
        default="ACCEPT",
    )
    use_amo_orders = models.BooleanField(default=False)
    primary_broker = models.CharField(
        max_length=20,
        choices=BrokerName.choices,
        default=BrokerName.FYERS,
    )

    class Meta:
        db_table = "broker_order_settings"

    def __str__(self):
        return f"Order Settings - {self.user.username}"


class OrderReconciliation(BaseTimestampModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="order_reconciliations",
    )
    broker_order_id = models.CharField(max_length=128)
    internal_order_id = models.CharField(max_length=128)
    broker_status = models.CharField(max_length=20, choices=OrderStatus.choices)
    internal_status = models.CharField(max_length=20, choices=OrderStatus.choices)
    discrepancy_type = models.CharField(max_length=80, blank=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "broker_order_reconciliation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.internal_order_id} vs {self.broker_order_id}"


class BrokerAPILog(BaseTimestampModel):
    credential = models.ForeignKey(
        BrokerCredential,
        on_delete=models.CASCADE,
        related_name="api_logs",
        null=True,
        blank=True,
    )
    endpoint = models.CharField(max_length=255)
    request_data = models.JSONField(default=dict, blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    status_code = models.PositiveIntegerField(default=200)
    latency_ms = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "broker_api_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.endpoint} [{self.status_code}]"


class BrokerFundsSnapshot(BaseTimestampModel):
    credential = models.ForeignKey(
        BrokerCredential,
        on_delete=models.CASCADE,
        related_name="fund_snapshots",
    )
    cash_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    available_margin = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    used_margin = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    collateral = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    withdrawable_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_equity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    raw_payload = models.JSONField(default=dict, blank=True)
    snapshot_time = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "broker_funds_snapshot"
        ordering = ["-snapshot_time", "-created_at"]

    def __str__(self):
        return f"{self.credential} funds @ {self.snapshot_time:%Y-%m-%d %H:%M:%S}"
