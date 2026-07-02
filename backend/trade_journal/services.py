from django.db import transaction

from live_trading.models import LiveOrder
from paper_trading.models import PaperTrade

from .models import JournalEntry, TradingInsight


class TradeJournalService:
    @staticmethod
    @transaction.atomic
    def bootstrap_recent_entries(user, limit=20):
        created_entries = []

        recent_paper_trades = PaperTrade.objects.filter(account__user=user).select_related("strategy", "instrument").order_by("-exit_time")[:limit]
        for trade in recent_paper_trades:
            entry, created = JournalEntry.objects.get_or_create(
                user=user,
                paper_trade=trade,
                defaults={
                    "strategy": trade.strategy,
                    "title": f"{trade.instrument.sym_ticker} paper trade review",
                    "notes": "",
                    "lessons_learned": "",
                },
            )
            if created:
                created_entries.append(entry)

        recent_live_orders = LiveOrder.objects.filter(
            user=user,
            status__in=["PARTIAL_FILL", "FILLED"],
        ).select_related("strategy", "instrument").order_by("-executed_at")[:limit]
        for order in recent_live_orders:
            existing = JournalEntry.objects.filter(user=user, live_order=order).first()
            if existing:
                continue
            entry = JournalEntry.objects.create(
                user=user,
                live_order=order,
                strategy=order.strategy,
                title=f"{order.instrument.sym_ticker} live execution review",
                notes="",
                lessons_learned="",
            )
            created_entries.append(entry)

        return created_entries

    @staticmethod
    @transaction.atomic
    def generate_insights(user):
        entries = JournalEntry.objects.filter(user=user)
        insights = []

        related_ids = [entry.id for entry in entries[:20]]

        rule_breaks = entries.filter(rule_followed=False).count()
        TradingInsight.objects.filter(user=user, insight_type="RULE_DISCIPLINE").delete()
        if rule_breaks:
            insights.append(
                TradingInsight.objects.create(
                    user=user,
                    insight_type="RULE_DISCIPLINE",
                    title="Rule discipline needs attention",
                    description=f"{rule_breaks} journaled trades were marked as rule violations. Review the repeated setup breakdowns before scaling live deployment.",
                    related_trades=related_ids,
                )
            )

        low_execution = entries.filter(execution_quality__lte=2).count()
        TradingInsight.objects.filter(user=user, insight_type="EXECUTION_QUALITY").delete()
        if low_execution:
            insights.append(
                TradingInsight.objects.create(
                    user=user,
                    insight_type="EXECUTION_QUALITY",
                    title="Execution quality is slipping",
                    description=f"{low_execution} entries were rated 2/5 or below for execution quality. Focus on latency, hesitation, and order planning.",
                    related_trades=related_ids,
                )
            )

        common_tags = {}
        for entry in entries:
            for tag in entry.mistake_tags or []:
                common_tags[tag] = common_tags.get(tag, 0) + 1
        TradingInsight.objects.filter(user=user, insight_type="COMMON_MISTAKE").delete()
        if common_tags:
            top_tag = sorted(common_tags.items(), key=lambda item: item[1], reverse=True)[0]
            insights.append(
                TradingInsight.objects.create(
                    user=user,
                    insight_type="COMMON_MISTAKE",
                    title="Most repeated mistake cluster",
                    description=f"'{top_tag[0]}' appeared in {top_tag[1]} journal entries. This is your highest-frequency improvement area right now.",
                    related_trades=related_ids,
                )
            )

        return insights

    @staticmethod
    def journal_summary(user):
        entries = JournalEntry.objects.filter(user=user)
        total_entries = entries.count()
        rule_followed = entries.filter(rule_followed=True).count()
        avg_setup = sum((int(entry.setup_quality or 0) for entry in entries), 0) / total_entries if total_entries else 0
        avg_execution = sum((int(entry.execution_quality or 0) for entry in entries), 0) / total_entries if total_entries else 0
        return {
            "entries": total_entries,
            "rule_follow_rate": round((rule_followed / total_entries) * 100, 2) if total_entries else 0,
            "avg_setup_quality": round(avg_setup, 2),
            "avg_execution_quality": round(avg_execution, 2),
            "insights": TradingInsight.objects.filter(user=user).count(),
        }
