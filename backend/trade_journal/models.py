from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class MistakeTag(BaseTimestampModel):
    CATEGORIES = [
        ("ENTRY", "Entry"),
        ("EXIT", "Exit"),
        ("RISK", "Risk"),
        ("PSYCHOLOGY", "Psychology"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="RISK")

    class Meta:
        db_table = "journal_mistake_tag"
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class JournalEntry(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="journal_entries")
    paper_trade = models.OneToOneField("paper_trading.PaperTrade", on_delete=models.SET_NULL, null=True, blank=True, related_name="journal_entry")
    live_order = models.ForeignKey("live_trading.LiveOrder", on_delete=models.SET_NULL, null=True, blank=True, related_name="journal_entries")
    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.SET_NULL, null=True, blank=True, related_name="journal_entries")
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    emotion_before = models.CharField(max_length=60, blank=True)
    emotion_after = models.CharField(max_length=60, blank=True)
    setup_quality = models.PositiveIntegerField(default=3)
    execution_quality = models.PositiveIntegerField(default=3)
    rule_followed = models.BooleanField(default=True)
    mistake_tags = models.JSONField(default=list, blank=True)
    lessons_learned = models.TextField(blank=True)
    ai_feedback = models.TextField(blank=True)
    screenshot_urls = models.JSONField(default=list, blank=True)
    chart_snapshot_url = models.URLField(blank=True)

    class Meta:
        db_table = "journal_entry"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class TradingInsight(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trading_insights")
    insight_type = models.CharField(max_length=80)
    title = models.CharField(max_length=200)
    description = models.TextField()
    related_trades = models.JSONField(default=list, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trading_insight"
        ordering = ["-generated_at"]

