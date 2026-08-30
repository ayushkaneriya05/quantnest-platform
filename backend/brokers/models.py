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
    """Simplified order settings for MARKET orders only."""
    broker_credential = models.OneToOneField(
        "BrokerCredential",
        on_delete=models.CASCADE,
        related_name="order_settings",
        null=True,
        blank=True,
    )
    order_timeout_seconds = models.PositiveIntegerField(default=30)

    class Meta:
        db_table = "broker_order_settings"

    def __str__(self):
        username = self.broker_credential.user.username if self.broker_credential and self.broker_credential.user else "Unknown"
        return f"Order Settings - {username}"


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


class BrokerChargeProfile(BaseTimestampModel):
    """Stores a complete brokerage charge profile for realistic cost simulation.

    Each profile captures all components of Indian market trading costs:
    brokerage, STT, exchange charges, SEBI fees, stamp duty, and GST.
    Users can create multiple profiles for different brokers/plans.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='charge_profiles',
        help_text='Owner of this charge profile'
    )
    broker_credential = models.ForeignKey(
        'BrokerCredential',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='charge_profiles',
        help_text='Optional link to a specific broker credential'
    )
    name = models.CharField(
        max_length=100,
        help_text='Display name (e.g., "Zerodha Equity", "Fyers F&O")'
    )

    # --- Brokerage ---
    brokerage_per_order = models.DecimalField(
        max_digits=10, decimal_places=2, default=20,
        help_text='Flat brokerage per executed order in INR'
    )
    brokerage_pct = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.03,
        help_text='Brokerage as percentage of turnover (e.g., 0.03 = 0.03%)'
    )
    brokerage_cap = models.DecimalField(
        max_digits=10, decimal_places=2, default=20,
        help_text='Maximum brokerage per order in INR (cap)'
    )

    # --- STT (Securities Transaction Tax) ---
    stt_eq_delivery_pct = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.1,
        help_text='STT on equity delivery (buy + sell) as % of turnover'
    )
    stt_eq_intraday_pct = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.025,
        help_text='STT on equity intraday (sell side only) as % of turnover'
    )
    stt_futures_pct = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.02,
        help_text='STT on futures (sell side only) as % of turnover'
    )
    stt_options_sell_pct = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.1,
        help_text='STT on options (sell side, on premium) as % of turnover'
    )

    # --- Exchange Transaction Charges ---
    exchange_txn_pct = models.DecimalField(
        max_digits=8, decimal_places=6, default=0.00345,
        help_text='Exchange transaction charge for equity as % of turnover'
    )
    exchange_txn_fo_pct = models.DecimalField(
        max_digits=8, decimal_places=6, default=0.05,
        help_text='Exchange transaction charge for F&O as % of turnover'
    )

    # --- Regulatory Charges ---
    sebi_turnover_pct = models.DecimalField(
        max_digits=10, decimal_places=8, default=0.0001,
        help_text='SEBI turnover fee as % of turnover'
    )
    stamp_duty_pct = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.003,
        help_text='Stamp duty on buy side as % of turnover'
    )
    gst_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=18.00,
        help_text='GST percentage applied on brokerage + exchange charges'
    )

    # --- Default Flag ---
    is_default = models.BooleanField(
        default=False,
        help_text='If True, this profile is used by default for new backtests/paper trades'
    )

    class Meta:
        db_table = 'broker_charge_profiles'
        ordering = ['-is_default', '-created_at']
        unique_together = ['user', 'name']

    def __str__(self):
        default_tag = ' [Default]' if self.is_default else ''
        return f"{self.name}{default_tag} ({self.user.username})"
