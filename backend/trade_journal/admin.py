from django.contrib import admin
from .models import JournalEntry


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "source", "execution_quality", "updated_at"]
    list_filter = ["source"]
    search_fields = ["title", "user__username"]
    readonly_fields = ["user", "source", "terminal_trade", "paper_trade", "live_trade", "created_at", "updated_at"]
