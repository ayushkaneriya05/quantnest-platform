from decimal import Decimal

from django.db.models import Avg, Sum
from django.utils import timezone

from backtesting.models import BacktestMetrics
from live_trading.models import LiveOrder, LivePosition, LiveTrade
from notifications.services import NotificationService
from paper_trading.models import PaperTrade
from strategies.models import Strategy
from trade_journal.models import TradingInsight
from trade_journal.services import TradeJournalService

from .models import DailyReport, PerformanceSnapshot, StrategyComparison


class AnalyticsService:
    @staticmethod
    def _strategy_trade_queryset(user, strategy, target_date):
        return PaperTrade.objects.filter(
            account__user=user,
            strategy=strategy,
            exit_time__date=target_date,
        )

    @staticmethod
    def refresh_strategy_snapshot(user, strategy, target_date=None):
        target_date = target_date or timezone.localdate()
        trades = AnalyticsService._strategy_trade_queryset(user, strategy, target_date)
        all_trades = PaperTrade.objects.filter(account__user=user, strategy=strategy, exit_time__date__lte=target_date)
        live_orders = LiveOrder.objects.filter(
            user=user,
            strategy=strategy,
            status__in=["PARTIAL_FILL", "FILLED"],
            executed_at__date=target_date,
        )
        live_positions = LivePosition.objects.filter(user=user, strategy=strategy)
        total_count = trades.count()
        wins = trades.filter(net_pnl__gt=0).count()
        live_trade_count = live_orders.count()
        daily_pnl = (trades.aggregate(v=Sum("net_pnl"))["v"] or Decimal("0")) + sum(
            (Decimal(str(position.unrealized_pnl or 0)) for position in live_positions),
            Decimal("0"),
        )
        cumulative_pnl = (all_trades.aggregate(v=Sum("net_pnl"))["v"] or Decimal("0")) + sum(
            (Decimal(str(value or 0)) for value in LiveTrade.objects.filter(
                user=user,
                strategy=strategy,
                exit_time__date=target_date,
            ).values_list("realized_pnl", flat=True)),
            Decimal("0"),
        )
        avg_trade_pnl = trades.aggregate(v=Avg("net_pnl"))["v"] or Decimal("0")
        metrics = BacktestMetrics.objects.filter(run__strategy=strategy, run__user=user).order_by("-run__completed_at", "-run__created_at").first()
        snapshot, _ = PerformanceSnapshot.objects.update_or_create(
            user=user,
            strategy=strategy,
            date=target_date,
            defaults={
                "daily_pnl": daily_pnl,
                "cumulative_pnl": cumulative_pnl,
                "trades_count": total_count + live_trade_count,
                "winning_trades": wins,
                "win_rate": (Decimal(str(wins)) / Decimal(str(total_count)) * Decimal("100")) if total_count else Decimal("0"),
                "avg_trade_pnl": avg_trade_pnl,
                "max_drawdown_pct": metrics.max_drawdown_pct if metrics else 0,
                "sharpe_ratio_30d": metrics.sharpe_ratio if metrics else 0,
            },
        )
        return snapshot

    @staticmethod
    def refresh_user_daily_report(user, target_date=None):
        target_date = target_date or timezone.localdate()
        for strategy in Strategy.objects.filter(user=user):
            AnalyticsService.refresh_strategy_snapshot(user, strategy, target_date)

        snapshots = PerformanceSnapshot.objects.filter(user=user, date=target_date).select_related("strategy")
        live_day_pnl = sum((Decimal(str(pos.unrealized_pnl or 0)) for pos in LivePosition.objects.filter(user=user)), Decimal("0"))
        paper_trades = PaperTrade.objects.filter(account__user=user, exit_time__date=target_date).select_related("strategy", "instrument")
        best_trade = paper_trades.order_by("-net_pnl").first()
        worst_trade = paper_trades.order_by("net_pnl").first()
        report, _ = DailyReport.objects.update_or_create(
            user=user,
            date=target_date,
            defaults={
                "total_pnl": (snapshots.aggregate(v=Sum("daily_pnl"))["v"] or Decimal("0")) + live_day_pnl,
                "realized_pnl": snapshots.aggregate(v=Sum("daily_pnl"))["v"] or Decimal("0"),
                "unrealized_pnl": sum((Decimal(str(pos.unrealized_pnl or 0)) for pos in LivePosition.objects.filter(user=user)), Decimal("0")),
                "total_trades": (snapshots.aggregate(v=Sum("trades_count"))["v"] or 0)
                + LiveOrder.objects.filter(user=user, executed_at__date=target_date).count(),
                "winning_trades": snapshots.aggregate(v=Sum("winning_trades"))["v"] or 0,
                "losing_trades": sum(max((snap.trades_count or 0) - (snap.winning_trades or 0), 0) for snap in snapshots),
                "best_trade": {
                    "symbol": best_trade.instrument.sym_ticker,
                    "strategy": getattr(best_trade.strategy, "name", ""),
                    "pnl": str(best_trade.net_pnl),
                } if best_trade else {},
                "worst_trade": {
                    "symbol": worst_trade.instrument.sym_ticker,
                    "strategy": getattr(worst_trade.strategy, "name", ""),
                    "pnl": str(worst_trade.net_pnl),
                } if worst_trade else {},
                "best_strategy": snapshots.order_by("-daily_pnl").first().strategy if snapshots.exists() else None,
                "worst_strategy": snapshots.order_by("daily_pnl").first().strategy if snapshots.exists() else None,
            },
        )
        return report

    @staticmethod
    def compare_strategies(user, strategies, start_date, end_date):
        comparison = StrategyComparison.objects.create(user=user, start_date=start_date, end_date=end_date)
        comparison.strategies.set(strategies)
        payload = []
        for strategy in strategies:
            snapshots = PerformanceSnapshot.objects.filter(
                user=user,
                strategy=strategy,
                date__range=(start_date, end_date),
            )
            payload.append(
                {
                    "strategy_id": strategy.id,
                    "strategy_name": strategy.name,
                    "total_pnl": float(snapshots.aggregate(v=Sum("daily_pnl"))["v"] or 0),
                    "avg_win_rate": float(snapshots.aggregate(v=Avg("win_rate"))["v"] or 0),
                    "trades_count": int(snapshots.aggregate(v=Sum("trades_count"))["v"] or 0),
                    "best_day": float(snapshots.order_by("-daily_pnl").first().daily_pnl) if snapshots.exists() else 0,
                    "worst_day": float(snapshots.order_by("daily_pnl").first().daily_pnl) if snapshots.exists() else 0,
                }
            )
        comparison.comparison_data = {"items": payload}
        comparison.save(update_fields=["comparison_data", "updated_at"])
        return comparison

    @staticmethod
    def refresh_phase7_suite(user, target_date=None):
        report = AnalyticsService.refresh_user_daily_report(user, target_date=target_date)
        TradeJournalService.bootstrap_recent_entries(user)
        insights = TradeJournalService.generate_insights(user)
        NotificationService.notify(
            user,
            title="Analytics refreshed",
            message=f"Daily report for {report.date} and {len(insights)} journal insights are ready.",
            data={"report_id": report.id, "insights": len(insights)},
        )
        return report

    @staticmethod
    def dashboard_payload(user):
        latest_report = DailyReport.objects.filter(user=user).select_related("best_strategy", "worst_strategy").first()
        snapshots = list(
            PerformanceSnapshot.objects.filter(user=user).select_related("strategy")[:8]
        )
        comparisons = list(StrategyComparison.objects.filter(user=user).prefetch_related("strategies")[:5])
        insights = list(TradingInsight.objects.filter(user=user)[:5])
        return {
            "latest_report": latest_report,
            "snapshots": snapshots,
            "comparisons": comparisons,
            "insights": insights,
            "notification_summary": NotificationService.summary(user),
            "journal_summary": TradeJournalService.journal_summary(user),
        }
