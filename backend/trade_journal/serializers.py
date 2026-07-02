from rest_framework import serializers

from .models import JournalEntry, MistakeTag, TradingInsight


class MistakeTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = MistakeTag
        fields = ["id", "name", "category", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class JournalEntrySerializer(serializers.ModelSerializer):
    strategy_name = serializers.CharField(source="strategy.name", read_only=True)
    symbol = serializers.SerializerMethodField()
    trade_source = serializers.SerializerMethodField()
    live_order_status = serializers.CharField(source="live_order.status", read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "paper_trade",
            "live_order",
            "strategy",
            "strategy_name",
            "symbol",
            "trade_source",
            "live_order_status",
            "title",
            "notes",
            "emotion_before",
            "emotion_after",
            "setup_quality",
            "execution_quality",
            "rule_followed",
            "mistake_tags",
            "lessons_learned",
            "ai_feedback",
            "screenshot_urls",
            "chart_snapshot_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_symbol(self, obj):
        if obj.paper_trade and obj.paper_trade.instrument:
            return obj.paper_trade.instrument.sym_ticker
        if obj.live_order and obj.live_order.instrument:
            return obj.live_order.instrument.sym_ticker
        return ""

    def get_trade_source(self, obj):
        if obj.paper_trade_id:
            return "PAPER"
        if obj.live_order_id:
            return "LIVE"
        return "MANUAL"


class TradingInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingInsight
        fields = ["id", "insight_type", "title", "description", "related_trades", "generated_at", "created_at", "updated_at"]
        read_only_fields = ["generated_at", "created_at", "updated_at"]
