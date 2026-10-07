import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def preserve_reviews(apps, schema_editor):
    Entry = apps.get_model("trade_journal", "JournalEntry")
    PaperTrade = apps.get_model("paper_trading", "PaperTrade")
    LiveTrade = apps.get_model("live_trading", "LiveTrade")
    for entry in Entry.objects.all().iterator(chunk_size=500):
        extra = []
        source, paper_id, live_id = "TERMINAL", None, None
        if entry.paper_trade_id:
            source = "PAPER"
            if PaperTrade.objects.filter(pk=entry.paper_trade_id, account__user_id=entry.user_id).exists():
                paper_id = entry.paper_trade_id
        elif entry.live_order_id:
            source = "LIVE"
            matches = list(LiveTrade.objects.filter(exit_order_id=entry.live_order_id, user_id=entry.user_id).values_list("id", flat=True)[:2])
            if len(matches) == 1 and not Entry.objects.filter(live_trade_id=matches[0]).exists():
                live_id = matches[0]
            extra.append(f"Imported execution review: order #{entry.live_order_id}.")
        for field, label in (("emotion_before", "Emotion before"), ("emotion_after", "Emotion after"),
                             ("ai_feedback", "Imported feedback (unverified)"), ("chart_snapshot_url", "Chart reference")):
            value = getattr(entry, field)
            if value:
                extra.append(f"{label}: {value}")
        extra.append(f"Original setup rating: {entry.setup_quality}/5. Rule followed (self-reported): {entry.rule_followed}.")
        if entry.screenshot_urls:
            extra.append("Screenshot references: " + str(entry.screenshot_urls))
        rating = entry.execution_quality if entry.execution_quality and 1 <= entry.execution_quality <= 5 else None
        if entry.execution_quality and rating is None:
            extra.append(f"Original execution rating: {entry.execution_quality}.")
        Entry.objects.filter(pk=entry.pk).update(source=source, paper_trade_id=paper_id, live_trade_id=live_id,
            execution_quality=rating, notes="\n\n".join(filter(None, [entry.notes, "\n".join(extra)])))


class Migration(migrations.Migration):
    dependencies = [("trade_journal", "0001_initial"), ("live_trading", "0022_remove_executionlog_fill_price_and_more"),
                    ("trading", "0006_position_created_at_alter_order_position_link_and_more")]
    operations = [
        migrations.AddField(model_name="journalentry", name="source",
            field=models.CharField(choices=[("TERMINAL", "Terminal"), ("PAPER", "Paper"), ("LIVE", "Live")], default="TERMINAL", max_length=10), preserve_default=False),
        migrations.AddField(model_name="journalentry", name="terminal_trade",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="journal_entry", to="trading.closedpositionlog")),
        migrations.AddField(model_name="journalentry", name="live_trade",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="journal_entry", to="live_trading.livetrade")),
        migrations.RunPython(preserve_reviews, migrations.RunPython.noop),
        *[migrations.RemoveField(model_name="journalentry", name=field) for field in
          ("live_order", "strategy", "emotion_before", "emotion_after", "setup_quality", "rule_followed", "ai_feedback", "screenshot_urls", "chart_snapshot_url")],
        migrations.AlterField(model_name="journalentry", name="execution_quality",
            field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
        migrations.DeleteModel(name="TradingInsight"),
        migrations.DeleteModel(name="MistakeTag"),
        migrations.AlterModelOptions(name="journalentry", options={"ordering": ["-updated_at", "-id"]}),
        migrations.AddIndex(model_name="journalentry", index=models.Index(fields=["user", "source", "-updated_at"], name="journal_user_source_idx")),
        migrations.AddConstraint(model_name="journalentry", constraint=models.CheckConstraint(
            condition=models.Q(execution_quality__isnull=True) | models.Q(execution_quality__gte=1, execution_quality__lte=5), name="journal_rating_range")),
        migrations.AddConstraint(model_name="journalentry", constraint=models.CheckConstraint(condition=(
            models.Q(source="TERMINAL", paper_trade__isnull=True, live_trade__isnull=True) |
            models.Q(source="PAPER", terminal_trade__isnull=True, live_trade__isnull=True) |
            models.Q(source="LIVE", terminal_trade__isnull=True, paper_trade__isnull=True)), name="journal_source_matches_trade")),
    ]
