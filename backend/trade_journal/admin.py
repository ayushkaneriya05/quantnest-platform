from django.contrib import admin

from .models import JournalEntry, MistakeTag, TradingInsight


@admin.register(MistakeTag)
class MistakeTagAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "category"]
    list_filter = ["category"]


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "strategy", "title", "rule_followed", "setup_quality", "execution_quality", "created_at"]
    list_filter = ["rule_followed"]


@admin.register(TradingInsight)
class TradingInsightAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "insight_type", "title", "generated_at"]
