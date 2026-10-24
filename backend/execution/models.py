"""Durable boundaries for the local execution workers.

CRUD accepts commands here. Account checkpoints and existing order/position/trade
tables are committed together by the writer, never by the tick evaluation loop.
"""
import uuid

from django.db import models
from django.utils import timezone

from common.enums import ExecutionMode, ExecutionCommandType


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
    instrument_id = models.PositiveBigIntegerField()
    version_id = models.PositiveBigIntegerField()
    position_revision = models.PositiveBigIntegerField()
    state = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['mode', 'session_id', 'instrument_id'], name='execution_unit_checkpoint')]
