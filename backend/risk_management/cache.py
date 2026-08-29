import time
import uuid
import logging
from django.core.cache import cache
from common.cache_keys import CacheKeys

from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum
logger = logging.getLogger(__name__)

class RiskCache:
    """
    Manages real-time risk metrics in Redis.
    Used by LiveExecutionService to avoid DB hits in the tick loop.
    """
    
    TTL_SECONDS = 60 * 60 * 24

    @staticmethod
    def _key(scope, user_id, session_id=None):
        if session_id:
            return CacheKeys.RISK_SESSION.format(scope=scope, user_id=user_id, session_id=session_id)
        return None
        
    @staticmethod
    def _lock_key(scope, user_id, session_id):
        return CacheKeys.RISK_LOCK.format(scope=scope, user_id=user_id, session_id=session_id)

    @staticmethod
    def get_stats(scope, user_id, session_id=None):
        data = cache.get(RiskCache._key(scope, user_id, session_id))
        if data:
            data = RiskCache._reset_expired_periods(data)
            return data
        return {
            "daily_trades": 0,
            "daily_pnl": 0.0,
            "drawdown": 0.0,
            "consecutive_losses": 0,
            "consecutive_wins": 0,
            "win_rate": 0.0,
            "total_closed_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "open_positions": 0,
            "weekly_pnl": 0.0,
            "monthly_pnl": 0.0,
            "closed_trades": 0,
            "period_day": None,
            "period_week": None,
            "period_month": None,
            "last_entry_time": None,
            "last_exit_time": None,
        }

    @staticmethod
    def get_or_rebuild(scope, user_id, session_id):
        """Return cached stats and rebuild only when this session has no cache."""
        key = RiskCache._key(scope, user_id, session_id)
        if cache.get(key):
            return RiskCache.get_stats(scope, user_id, session_id)
        return RiskCache.sync_from_db(scope, session_id)

    @staticmethod
    def _period_keys():
        from django.utils import timezone

        today = timezone.localdate()
        iso_calendar = today.isocalendar()
        return str(today), f"{iso_calendar.year}-W{iso_calendar.week}", f"{today.year}-{today.month:02d}"

    @staticmethod
    def _reset_expired_periods(stats):
        day, week, month = RiskCache._period_keys()
        if stats.get("period_day") != day:
            stats["daily_trades"] = 0
            stats["daily_pnl"] = 0.0
            stats["period_day"] = day
        if stats.get("period_week") != week:
            stats["weekly_pnl"] = 0.0
            stats["period_week"] = week
        if stats.get("period_month") != month:
            stats["monthly_pnl"] = 0.0
            stats["period_month"] = month
        return stats

    @staticmethod
    def update_stats(scope, user_id, session_id, updates):
        key = RiskCache._key(scope, user_id, session_id)
        current = RiskCache.get_stats(scope, user_id, session_id)
        current.update(updates)
        cache.set(key, current, timeout=RiskCache.TTL_SECONDS)

    @staticmethod
    def _run_with_lock(scope, user_id, session_id, func, retries=5, delay=0.05):
        lock_key = RiskCache._lock_key(scope, user_id, session_id)
        lock_token = str(uuid.uuid4())
        
        for _ in range(retries):
            if cache.add(lock_key, lock_token, timeout=5):
                try:
                    return func()
                finally:
                    if cache.get(lock_key) == lock_token:
                        cache.delete(lock_key)
            time.sleep(delay)
            
        # Fallback if lock fails: log warning and execute anyway to prevent completely missing updates
        logger.warning(f"Could not acquire lock for {lock_key}, proceeding without lock to prevent missed updates.")
        return func()


    @staticmethod
    def record_trade_result(scope, user_id, session_id, pnl):
        def _record():
            from django.utils import timezone

            key = RiskCache._key(scope, user_id, session_id)
            current = RiskCache._reset_expired_periods(RiskCache.get_stats(scope, user_id, session_id))
            pnl = float(pnl or 0.0)
            current["daily_trades"] = int(current.get("daily_trades", 0) or 0) + 1
            current["daily_pnl"] = float(current.get("daily_pnl", 0.0) or 0.0) + pnl
            current["weekly_pnl"] = float(current.get("weekly_pnl", 0.0) or 0.0) + pnl
            current["monthly_pnl"] = float(current.get("monthly_pnl", 0.0) or 0.0) + pnl
            current["total_closed_trades"] = int(current.get("total_closed_trades", 0) or 0) + 1
            current["closed_trades"] = current["total_closed_trades"]

            if pnl < 0:
                current["consecutive_losses"] = current.get("consecutive_losses", 0) + 1
                current["consecutive_wins"] = 0
                current["losing_trades"] = int(current.get("losing_trades", 0) or 0) + 1
            elif pnl > 0:
                current["consecutive_wins"] = current.get("consecutive_wins", 0) + 1
                current["consecutive_losses"] = 0
                current["winning_trades"] = int(current.get("winning_trades", 0) or 0) + 1

            total_closed = int(current.get("total_closed_trades", 0) or 0)
            wins = int(current.get("winning_trades", 0) or 0)
            current["win_rate"] = (wins / total_closed) * 100 if total_closed else 0.0
            current["last_exit_time"] = timezone.now().isoformat()
            day, week, month = RiskCache._period_keys()
            current["period_day"] = day
            current["period_week"] = week
            current["period_month"] = month
            cache.set(key, current, timeout=RiskCache.TTL_SECONDS)
            
        RiskCache._run_with_lock(scope, user_id, session_id, _record)

    @staticmethod
    def sync_on_fill(scope, session_id):
        """Perform an immediate recalculation/sync of the risk cache for the given session."""
        RiskCache.sync_from_db(scope, session_id)

    @staticmethod
    def sync_from_db(scope, session_id):
        """Populate the cache from the database using scope-specific models."""
        from django.utils import timezone
        today = timezone.localdate()

        if scope.upper() == "LIVE":
            stats = RiskCache._sync_live_session(session_id, today)
        else:
            stats = RiskCache._sync_paper_session(session_id, today)
            
        if not stats:
            return {}
               
        RiskCache.update_stats(scope, stats.get("user_id"), session_id, stats)
        return stats

    @staticmethod
    def _sync_live_session(session_id, today):
        from live_trading.models import TradingSession as Session, LivePosition as Position, LiveTrade as Trade

        session = Session.objects.filter(id=session_id).select_related('user', 'strategy', 'allocation').first()
        if not session:
            return None
            
        user = session.user
        strategy = session.strategy
        positions = Position.objects.filter(allocation=session.allocation, quantity__gt=0)
        allocation = session.allocation
        trades = Trade.objects.filter(allocation=allocation, strategy=strategy)
        daily_trades = trades.filter(exit_time__date=today)
        weekly_trades = trades.filter(exit_time__date__gte=today - timedelta(days=7))
        monthly_trades = trades.filter(exit_time__date__gte=today - timedelta(days=30))
        total_closed = trades.count()
        winning_trades = trades.filter(realized_pnl__gt=0).count()
        losing_trades = trades.filter(realized_pnl__lt=0).count()
        ordered_results = list(trades.order_by("-exit_time").values_list("realized_pnl", flat=True))
        consecutive_losses = 0
        consecutive_wins = 0
        for result in ordered_results:
            if result < 0:
                if consecutive_wins:
                    break
                consecutive_losses += 1
            elif result > 0:
                if consecutive_losses:
                    break
                consecutive_wins += 1
            else:
                break
        allocated_capital = float(allocation.allocated_capital or 0) if allocation else 0.0
        realized_pnl = float(trades.aggregate(value=Sum("realized_pnl"))["value"] or 0) if allocation else 0.0
        unrealized_pnl = float(sum((position.unrealized_pnl for position in positions), Decimal("0")))
        equity = allocated_capital + realized_pnl + unrealized_pnl
        drawdown = max(0.0, -realized_pnl - unrealized_pnl)

        return {
            "user_id": user.id,
            "daily_trades": daily_trades.count(),
            "daily_pnl": float(daily_trades.aggregate(value=Sum("realized_pnl"))["value"] or 0) + unrealized_pnl,
            "drawdown": (drawdown / allocated_capital) * 100 if equity > 0 and allocated_capital > 0 else 0.0,
            "open_positions": positions.count(),
            "weekly_pnl": float(weekly_trades.aggregate(value=Sum("realized_pnl"))["value"] or 0),
            "monthly_pnl": float(monthly_trades.aggregate(value=Sum("realized_pnl"))["value"] or 0),
            "total_closed_trades": total_closed,
            "closed_trades": total_closed,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": (winning_trades / total_closed) * 100 if total_closed else 0.0,
            "consecutive_losses": consecutive_losses,
            "consecutive_wins": consecutive_wins,
            "last_entry_time": None,
            "last_exit_time": trades.order_by("-exit_time").values_list("exit_time", flat=True).first().isoformat() if total_closed else None,
        }

    @staticmethod
    def _sync_paper_session(session_id, today):
        from paper_trading.models import PaperTradingSession as Session, PaperPosition as Position, PaperTrade
        from django.db.models import Sum
        from datetime import timedelta

        session = Session.objects.filter(id=session_id).select_related('user', 'strategy', 'account').first()
        if not session:
            return None
            
        user = session.user
        strategy = session.strategy
        account = session.account
        
        positions = Position.objects.filter(account=account)
        closed_trades = PaperTrade.objects.filter(account=account, strategy=strategy).exclude(exit_time__isnull=True)
        realized_pnl = closed_trades.aggregate(v=Sum("net_pnl"))["v"] or Decimal("0")
        unrealized_pnl = sum((position.unrealized_pnl for position in positions), Decimal("0"))
        account_equity = account.initial_balance + realized_pnl + unrealized_pnl
        drawdown = max(Decimal("0"), account.initial_balance - account_equity)
        total_closed = closed_trades.count()
        winning_trades = closed_trades.filter(net_pnl__gt=0).count()
        losing_trades = closed_trades.filter(net_pnl__lt=0).count()
        ordered_results = list(closed_trades.order_by("-exit_time").values_list("net_pnl", flat=True))
        consecutive_losses = 0
        consecutive_wins = 0
        for result in ordered_results:
            if result < 0:
                if consecutive_wins:
                    break
                consecutive_losses += 1
            elif result > 0:
                if consecutive_losses:
                    break
                consecutive_wins += 1
            else:
                break

        return {
            "user_id": user.id,
            "daily_trades": closed_trades.filter(exit_time__date=today).count(),
            "daily_pnl": float(closed_trades.filter(exit_time__date=today).aggregate(v=Sum("net_pnl"))["v"] or 0) + float(unrealized_pnl),
            "drawdown": float((drawdown / account.initial_balance) * 100) if account.initial_balance > 0 else 0.0,
            "open_positions": positions.filter(quantity__gt=0).count(),
            "weekly_pnl": float(closed_trades.filter(exit_time__date__gte=today - timedelta(days=7)).aggregate(v=Sum("net_pnl"))["v"] or 0),
            "monthly_pnl": float(closed_trades.filter(exit_time__date__gte=today - timedelta(days=30)).aggregate(v=Sum("net_pnl"))["v"] or 0),
            "last_entry_time": None,
            "last_exit_time": closed_trades.order_by("-exit_time").values_list("exit_time", flat=True).first().isoformat() if closed_trades.exists() else None,
            "total_closed_trades": total_closed,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": (winning_trades / total_closed) * 100 if total_closed else 0.0,
            "closed_trades": total_closed,
            "consecutive_losses": consecutive_losses,
            "consecutive_wins": consecutive_wins,
        }
