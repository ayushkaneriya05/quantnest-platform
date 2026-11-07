"""Durable boundaries for the local execution workers.

CRUD accepts commands here. Account checkpoints and existing order/position/trade
tables are committed together by the writer, never by the tick evaluation loop.
"""
import uuid

from django.db import models
from django.utils import timezone

from common.enums import ExecutionMode, ExecutionCommandType, SettlementKind


class AccountCheckpoint(models.Model):
    mode = models.CharField(max_length=12, choices=ExecutionMode.choices)
    account_id = models.PositiveBigIntegerField()
    revision = models.PositiveBigIntegerField(default=0)
    state = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['mode', 'account_id'], name='execution_account_checkpoint')]


class Command(models.Model):
    id = models.BigAutoField(primary_key=True)
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    mode = models.CharField(max_length=12, choices=ExecutionMode.choices)
    account_id = models.PositiveBigIntegerField()
    kind = models.CharField(max_length=12, choices=ExecutionCommandType.choices)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    applied_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['id']
        indexes = [models.Index(fields=['applied_at', 'id'], name='execution_pending_commands')]


class EvaluationCheckpoint(models.Model):
    """Small path-dependent rule state; indicator history stays in the data layer."""
    mode = models.CharField(max_length=12, choices=ExecutionMode.choices)
    session_id = models.PositiveBigIntegerField()
    route_id = models.CharField(max_length=80, default='')
    leg_id = models.CharField(max_length=80, default='')
    version_id = models.PositiveBigIntegerField()
    position_revision = models.PositiveBigIntegerField()
    state = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['mode', 'session_id', 'route_id', 'leg_id'], name='execution_unit_checkpoint')]


class RouteOwnership(models.Model):
    """Reporting identity; a dated contract is a binding, not a position owner."""
    route_id = models.CharField(max_length=80, default='')
    leg_id = models.CharField(max_length=80, default='')

    class Meta:
        abstract = True


class SettlementPrice(models.Model):
    """Reviewed source evidence, never inferred from a quote or candle close."""
    instrument = models.ForeignKey('instruments.Instrument', on_delete=models.PROTECT)
    kind = models.CharField(max_length=8, choices=SettlementKind.choices)
    effective_at = models.DateTimeField()
    available_at = models.DateTimeField()
    value = models.DecimalField(max_digits=24, decimal_places=8)
    source = models.CharField(max_length=500)
    cash_settled = models.BooleanField(default=False)
    fee_per_unit = models.DecimalField(max_digits=24, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['effective_at', 'pk']
        constraints = [models.UniqueConstraint(fields=['instrument', 'effective_at', 'kind'], name='execution_settlement_price')]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            from django.core.exceptions import ValidationError
            raise ValidationError('Settlement evidence is immutable. Review corrections separately.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.instrument_id} / {self.kind} / {self.effective_at.isoformat()}'


class SettlementPosting(RouteOwnership):
    """One sourced payment per owned position cycle, committed with its checkpoint."""
    identity = models.CharField(max_length=300, unique=True)
    price = models.ForeignKey(SettlementPrice, on_delete=models.PROTECT, related_name='postings')
    command = models.OneToOneField(Command, on_delete=models.PROTECT, null=True)
    mode = models.CharField(max_length=12, choices=ExecutionMode.choices)
    account_id = models.PositiveBigIntegerField()
    session_id = models.PositiveBigIntegerField()
    quantity = models.IntegerField()
    opened_at = models.DateTimeField()
    gross = models.DecimalField(max_digits=24, decimal_places=8)
    fees = models.DecimalField(max_digits=24, decimal_places=8)
    cash_change = models.DecimalField(max_digits=24, decimal_places=8)
    revision = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        indexes = [models.Index(fields=['mode', 'account_id'], name='execution_settlement_account')]
