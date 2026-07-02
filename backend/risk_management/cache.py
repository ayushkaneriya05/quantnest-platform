import json
from decimal import Decimal
from django.core.cache import cache

class RiskCache:
    """
    Manages real-time risk metrics in Redis.
    Used by LiveExecutionService to avoid DB hits in the tick loop.
    """
    
    @staticmethod
    def _key(user_id, strategy_id=None):
        if strategy_id:
            return f"risk_state:user_{user_id}:strat_{strategy_id}"
        return f"risk_state:user_{user_id}:portfolio"

    @staticmethod
    def get_stats(user_id, strategy_id=None):
        data = cache.get(RiskCache._key(user_id, strategy_id))
        if data:
            return data
        return {
            "daily_trades": 0,
            "daily_pnl": 0.0,
            "total_exposure": 0.0,
            "drawdown": 0.0,
            "consecutive_losses": 0,
            "strategy_allocation_pct": 0.0,
            "instrument_exposure_pct": 0.0,
        }

    @staticmethod
    def update_stats(user_id, strategy_id, updates):
        key = RiskCache._key(user_id, strategy_id)
        current = RiskCache.get_stats(user_id, strategy_id)
        current.update(updates)
        cache.set(key, current, timeout=60 * 60 * 24) # 24 hours

    @staticmethod
    def increment_trade_count(user_id, strategy_id):
        key = RiskCache._key(user_id, strategy_id)
        current = RiskCache.get_stats(user_id, strategy_id)
        current["daily_trades"] = current.get("daily_trades", 0) + 1
        cache.set(key, current, timeout=60 * 60 * 24)

    @staticmethod
    def sync_from_db(user, strategy):
        """
        Populate the cache from the database.
        Called on session startup and after fills.
        """
        from live_trading.models import LivePosition, LiveOrder
        from paper_trading.models import Portfolio
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Sum
        from common.enums import OrderStatus, Side

        today = timezone.localdate()

        # 1. Fetch current positions for strategy
        positions = LivePosition.objects.filter(user=user, strategy=strategy)
        total_exposure = sum((float(pos.avg_price) * pos.quantity for pos in positions), 0.0)

        entry_config = getattr(strategy, "entry_order_config", None)
        entry_side = getattr(entry_config, "entry_side", Side.BUY) if entry_config else Side.BUY
        exit_side = Side.SELL if entry_side == Side.BUY else Side.BUY
        filled_statuses = {OrderStatus.PARTIAL_FILL, OrderStatus.FILLED}

        # 2. Fetch completed trade count. A completed strategy trade is counted
        # on the exit fill, matching paper trades and backtest closed trades.
        completed_trade_query = LiveOrder.objects.filter(
            user=user,
            strategy=strategy,
            side=exit_side,
            status__in=filled_statuses,
        ).exclude(executed_at__isnull=True)
        daily_trades = completed_trade_query.filter(executed_at__date=today).count()

        # 3. Fetch Portfolio PnL
        portfolio = Portfolio.objects.filter(user=user).first()
        daily_pnl = float(portfolio.today_pnl or 0) if portfolio else 0.0
        drawdown = float(portfolio.current_drawdown or 0) if portfolio else 0.0

        # 4. Fetch last exit time for re-entry check
        last_exit = completed_trade_query.order_by("-executed_at").first()

        # 5. Compute consecutive losses by pairing recent exit fills with the
        # preceding entry fills for the same instrument.
        consecutive_losses = 0
        for exit_order in completed_trade_query.order_by("-executed_at")[:50]:
            entry_order = (
                LiveOrder.objects.filter(
                    user=user,
                    strategy=strategy,
                    instrument=exit_order.instrument,
                    side=entry_side,
                    status__in=filled_statuses,
                    executed_at__lt=exit_order.executed_at,
                )
                .exclude(executed_at__isnull=True)
                .order_by("-executed_at")
                .first()
            )
            if not entry_order or not entry_order.avg_fill_price or not exit_order.avg_fill_price:
                break
            closed_qty = min(int(entry_order.filled_quantity or entry_order.quantity or 0), int(exit_order.filled_quantity or exit_order.quantity or 0))
            if closed_qty <= 0:
                break
            pnl = (
                (exit_order.avg_fill_price - entry_order.avg_fill_price) * closed_qty
                if entry_side == Side.BUY
                else (entry_order.avg_fill_price - exit_order.avg_fill_price) * closed_qty
            )
            if pnl < 0:
                consecutive_losses += 1
            else:
                break

        # 6. Weekly and monthly PnL for auto-disable rules
        from paper_trading.models import DailyPerformance
        weekly_pnl = float(
            DailyPerformance.objects.filter(
                portfolio=portfolio,
                date__gte=today - timedelta(days=7),
            ).aggregate(v=Sum("total_pnl"))["v"] or 0
        ) if portfolio else 0.0
        monthly_pnl = float(
            DailyPerformance.objects.filter(
                portfolio=portfolio,
                date__gte=today - timedelta(days=30),
            ).aggregate(v=Sum("total_pnl"))["v"] or 0
        ) if portfolio else 0.0

        stats = {
            "daily_trades": daily_trades,
            "daily_pnl": daily_pnl,
            "total_exposure": total_exposure,
            "drawdown": drawdown,
            "consecutive_losses": consecutive_losses,
            "weekly_pnl": weekly_pnl,
            "monthly_pnl": monthly_pnl,
            "last_exit_time": last_exit.executed_at.isoformat() if last_exit and last_exit.executed_at else None,
        }

        RiskCache.update_stats(user.id, strategy.id, stats)
        return stats
