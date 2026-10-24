from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models.deletion import ProtectedError
from django.db.models.signals import post_save
from django.dispatch import receiver
from common.encryption import EncryptedTextField
from django.utils import timezone

from common.enums import BrokerName
from common.models import BaseTimestampModel


class BrokerCredential(BaseTimestampModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="broker_credentials",
    )
    broker_name = models.CharField(max_length=20, choices=BrokerName.choices)
    label = models.CharField(max_length=80, blank=True)
    client_id = models.CharField(max_length=120, blank=True, help_text="Owner's broker App ID, distinct from the trading account ID")
    api_secret = EncryptedTextField(blank=True, help_text="Owner's App Secret, encrypted at rest")
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
    access_token = EncryptedTextField()
    token_expiry = models.DateTimeField()
    is_valid = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "broker_session"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.credential.broker_name} session {self.id}"




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
    withdrawable_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    net_equity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    snapshot_time = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "broker_funds_snapshot"
        ordering = ["-snapshot_time", "-created_at"]

    def __str__(self):
        return f"{self.credential} funds @ {self.snapshot_time:%Y-%m-%d %H:%M:%S}"


class BrokerChargeProfile(BaseTimestampModel):
    """Stores reusable trading costs for backtests and Paper simulation.

    Each profile captures all components of Indian market trading costs:
    brokerage, STT, exchange charges, SEBI fees, stamp duty, and GST.
    Users can create named profiles without connecting a broker account.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='charge_profiles',
        help_text='Owner of this charge profile'
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
        max_digits=6, decimal_places=4, default=0.05,
        help_text='STT on futures (sell side only) as % of turnover'
    )
    stt_options_sell_pct = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.15,
        help_text='STT on options (sell side, on premium) as % of turnover'
    )
    ctt_futures_sell_pct = models.DecimalField(max_digits=6, decimal_places=4, default=0,
        help_text='Configured commodity futures sell tax rate; set the rate applicable to the contract')
    ctt_options_sell_pct = models.DecimalField(max_digits=6, decimal_places=4, default=0,
        help_text='Configured commodity options sell tax rate; set the rate applicable to the contract')

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
        constraints = [
            models.UniqueConstraint(
                fields=['user'], condition=models.Q(is_default=True),
                name='unique_default_charge_profile_per_user',
            ),
        ]

    @transaction.atomic
    def set_default(self):
        """Switch the user's default as one transaction."""
        get_user_model().objects.select_for_update().get(pk=self.user_id)
        type(self).objects.filter(user_id=self.user_id, is_default=True).exclude(pk=self.pk).update(is_default=False)
        self.is_default = True
        self.save(update_fields=['is_default', 'updated_at'])

    @transaction.atomic
    def delete(self, *args, **kwargs):
        get_user_model().objects.select_for_update().get(pk=self.user_id)
        self.refresh_from_db(fields=['is_default'])
        if self.is_default:
            raise ProtectedError('Set another charge profile as default before deleting this one.', [self])
        return super().delete(*args, **kwargs)

    def __str__(self):
        default_tag = ' [Default]' if self.is_default else ''
        return f"{self.name}{default_tag} ({self.user.username})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid='brokers.create_default_charge_profile')
def create_default_charge_profile(sender, instance, created, raw, **kwargs):
    """Provision simulation costs for every new account, including social signups."""
    if created and not raw:
        BrokerChargeProfile.objects.create(user=instance, name='QuantNest', is_default=True)
