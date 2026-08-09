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
    def record_trade_result(user_id, strategy_id, pnl):
        key = RiskCache._key(user_id, strategy_id)
        current = RiskCache.get_stats(user_id, strategy_id)
        if pnl < 0:
            current["consecutive_losses"] = current.get("consecutive_losses", 0) + 1
        else:
            current["consecutive_losses"] = 0
        cache.set(key, current, timeout=60 * 60 * 24)

    @staticmethod
    def sync_on_fill(user_id, portfolio_value):
        """
        Perform an immediate recalculation/sync of the risk cache for the given user.
        """
        from live_trading.models import LiveStrategyAllocation
        from strategies.models import Strategy
        allocations = LiveStrategyAllocation.objects.filter(user_id=user_id, is_active=True).select_related('strategy')
        for alloc in allocations:
            RiskCache.sync_from_db(alloc.user, alloc.strategy)

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

        # 5. Consecutive losses are now tracked via record_trade_result on trade close.
        # We retain the existing cached value to avoid expensive DB queries.
        current_stats = RiskCache.get_stats(user.id, strategy.id)
        consecutive_losses = current_stats.get("consecutive_losses", 0)

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
