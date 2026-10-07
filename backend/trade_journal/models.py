from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from common.models import BaseTimestampModel


class JournalEntry(BaseTimestampModel):
    class Source(models.TextChoices):
        TERMINAL = "TERMINAL", "Terminal"
        PAPER = "PAPER", "Paper"
        LIVE = "LIVE", "Live"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="journal_entries")
    source = models.CharField(max_length=10, choices=Source.choices)
    terminal_trade = models.OneToOneField("trading.ClosedPositionLog", on_delete=models.CASCADE, null=True, blank=True, related_name="journal_entry")
    paper_trade = models.OneToOneField("paper_trading.PaperTrade", on_delete=models.CASCADE, null=True, blank=True, related_name="journal_entry")
    live_trade = models.OneToOneField("live_trading.LiveTrade", on_delete=models.CASCADE, null=True, blank=True, related_name="journal_entry")
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    mistake_tags = models.JSONField(default=list, blank=True)
    lessons_learned = models.TextField(blank=True)
    execution_quality = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        db_table = "journal_entry"
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["user", "source", "-updated_at"], name="journal_user_source_idx")]
        constraints = [
            models.CheckConstraint(condition=models.Q(execution_quality__isnull=True) | models.Q(execution_quality__gte=1, execution_quality__lte=5), name="journal_rating_range"),
            models.CheckConstraint(condition=(
                models.Q(source="TERMINAL", terminal_trade__isnull=False, paper_trade__isnull=True, live_trade__isnull=True) |
                models.Q(source="PAPER", paper_trade__isnull=False, terminal_trade__isnull=True, live_trade__isnull=True) |
                models.Q(source="LIVE", live_trade__isnull=False, terminal_trade__isnull=True, paper_trade__isnull=True)
            ), name="journal_source_matches_trade"),
        ]

    def __str__(self):
        return self.title

