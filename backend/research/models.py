import uuid

from django.conf import settings
from django.db import models
from common.models import BaseTimestampModel


class ResearchSession(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=160)
    context = models.JSONField(default=dict)
    kind = models.CharField(max_length=12, choices=[("CHAT", "Conversation"), ("SCREEN", "Saved screen")], default="CHAT")

    class Meta:
        ordering = ["-updated_at", "-id"]


class ResearchRun(BaseTimestampModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Queued"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    session = models.ForeignKey(ResearchSession, on_delete=models.CASCADE, related_name="runs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_id = models.UUIDField(default=uuid.uuid4)
    mode = models.CharField(max_length=10, choices=[("RESEARCH", "Research"), ("SCREEN", "Screen")])
    prompt = models.TextField(blank=True)
    request = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    progress_message = models.CharField(max_length=255, default="Queued for research")
    evidence = models.JSONField(default=list)
    result = models.JSONField(default=dict)
    usage = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=1)
    tool_attempts = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    as_of = models.DateTimeField()
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    created_strategy = models.ForeignKey("strategies.Strategy", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "request_id"], name="research_request_unique"),
            models.UniqueConstraint(fields=["user"], condition=models.Q(status__in=["PENDING", "RUNNING"]), name="research_one_active_run"),
        ]


class ResearchAction(BaseTimestampModel):
    class Type(models.TextChoices):
        CREATE_DRAFT = "CREATE_DRAFT", "Create strategy draft"
        ADD_TO_WATCHLIST = "ADD_TO_WATCHLIST", "Add to terminal watchlist"
        START_BACKTEST = "START_BACKTEST", "Start backtest"

    class Status(models.TextChoices):
        PROPOSED = "PROPOSED", "Awaiting confirmation"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    run = models.ForeignKey(ResearchRun, on_delete=models.CASCADE, related_name="actions")
    action_type = models.CharField(max_length=20, choices=Type.choices)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROPOSED)
    resource_ids = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
