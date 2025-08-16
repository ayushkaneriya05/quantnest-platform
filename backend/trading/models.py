# backend/trading/models.py
from decimal import Decimal
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class PaperAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("100000.00"))
    equity = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("100000.00"))
    margin_used = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0.00"))

    def __str__(self):
        return f"Account({self.user_id})"


class PaperOrder(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_PARTIAL = "PARTIAL"
    STATUS_FILLED = "FILLED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "PENDING"),
        (STATUS_PARTIAL, "PARTIAL"),
        (STATUS_FILLED, "FILLED"),
        (STATUS_CANCELLED, "CANCELLED"),
    ]

    ORDER_MARKET = "MARKET"
    ORDER_LIMIT = "LIMIT"
    ORDER_SL = "SL"
    ORDER_SLM = "SL-M"

    ORDER_TYPES = [
        (ORDER_MARKET, "Market"),
        (ORDER_LIMIT, "Limit"),
        (ORDER_SL, "Stop-Limit"),
        (ORDER_SLM, "Stop-Market"),
    ]

    PRODUCT_MIS = "MIS"
    PRODUCT_NRML = "NRML"
    PRODUCT_CNC = "CNC"

    PRODUCT_TYPES = [
        (PRODUCT_MIS, "MIS"),
        (PRODUCT_NRML, "NRML"),
        (PRODUCT_CNC, "CNC"),
    ]

    ORDER_TAG_ENTRY = "ENTRY"
    ORDER_TAG_TP = "TP"
    ORDER_TAG_SL = "SL"
    ORDER_TAG_COVER_SL = "COVER_SL"
    ORDER_TAG_BRACKET_CHILD = "BRACKET_CHILD"

    ORDER_TAGS = [
        (ORDER_TAG_ENTRY, "Entry"),
        (ORDER_TAG_TP, "TakeProfit"),
        (ORDER_TAG_SL, "StopLoss"),
        (ORDER_TAG_COVER_SL, "CoverStop"),
        (ORDER_TAG_BRACKET_CHILD, "BracketChild"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=32, db_index=True)
    side = models.CharField(max_length=4)  # 'BUY' or 'SELL'
    qty = models.IntegerField()
    order_type = models.CharField(max_length=10, choices=ORDER_TYPES, default=ORDER_MARKET)
    product_type = models.CharField(max_length=8, choices=PRODUCT_TYPES, default=PRODUCT_NRML)
    price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    trigger_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    filled_qty = models.IntegerField(default=0)
    avg_fill_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Bracket/OCO fields
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    order_tag = models.CharField(max_length=32, choices=ORDER_TAGS, default=ORDER_TAG_ENTRY)
    oco_group = models.CharField(max_length=64, null=True, blank=True)
    tp_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    sl_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

    # New: Stop-Market marker and stored stop trigger price (for SL-M behavior)
    is_slm = models.BooleanField(default=False)
    stop_trigger_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"Order({self.id} {self.symbol} {self.side} {self.qty} @ {self.price})"

    def remaining_qty(self):
        return max(0, self.qty - (self.filled_qty or 0))

    def create_oco_group(self):
        if not self.oco_group:
            self.oco_group = str(uuid.uuid4())
            self.save(update_fields=["oco_group"])


class PaperTrade(models.Model):
    order = models.ForeignKey(PaperOrder, on_delete=models.CASCADE, related_name="trades")
    qty = models.IntegerField()
    price = models.DecimalField(max_digits=18, decimal_places=6)
    ts = models.DateTimeField(auto_now_add=True)


class PaperPosition(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=32, db_index=True)
    qty = models.IntegerField()
    avg_price = models.DecimalField(max_digits=18, decimal_places=6)
    realized_pnl = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0.0"))
    unrealized_pnl = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0.0"))
    # Position-level SL/TP
    sl_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    tp_price = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Position({self.user_id} {self.symbol} {self.qty} @ {self.avg_price})"


class AuditLog(models.Model):
    """
    Simple audit log for order lifecycle events.
    """
    ACTION_CREATED = "CREATED"
    ACTION_MODIFIED = "MODIFIED"
    ACTION_CANCELLED = "CANCELLED"
    ACTION_TRIGGERED = "TRIGGERED"
    ACTION_EXECUTED = "EXECUTED"

    ACTION_CHOICES = [
        (ACTION_CREATED, "Created"),
        (ACTION_MODIFIED, "Modified"),
        (ACTION_CANCELLED, "Cancelled"),
        (ACTION_TRIGGERED, "Triggered"),
        (ACTION_EXECUTED, "Executed"),
    ]

    order = models.ForeignKey(PaperOrder, on_delete=models.CASCADE, related_name="audit_logs", null=True)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Audit({self.order_id} {self.action} {self.timestamp.isoformat()})"
