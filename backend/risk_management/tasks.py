import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from risk_management.models import StrategyAutoDisable

logger = logging.getLogger(__name__)

@shared_task(name="risk_management.check_and_reenable_strategies")
def check_and_reenable_strategies():
    """
    Check for PAUSED sessions that were disabled by risk rules 
    and re-enable them after the cooldown period.
    """
    from paper_trading.models import PaperTradingSession
    from live_trading.models import TradingSession
    
    now = timezone.now()
    reenabled_count = 0
    
    # We look for active auto-disable rules that allow auto-reenabling
    auto_reenable_rules = StrategyAutoDisable.objects.filter(
        is_active=True,
        auto_reenable=True,
    )
    
    strategy_to_rule = {rule.strategy_id: rule for rule in auto_reenable_rules}
    if not strategy_to_rule:
        return {"reenabled": 0}
        
    strategy_ids = list(strategy_to_rule.keys())
    
    # Check paper sessions
    paper_sessions = PaperTradingSession.objects.filter(
        status="PAUSED", 
        strategy_id__in=strategy_ids
    )
    for session in paper_sessions:
        rule = strategy_to_rule[session.strategy_id]
        if session.updated_at + timedelta(hours=rule.cooldown_hours) <= now:
            session.status = "RUNNING"
            session.error_message = f"Auto-reenabled after {rule.cooldown_hours}h cooldown"
            session.save(update_fields=["status", "error_message", "updated_at"])
            reenabled_count += 1
            # Publish event for paper session auto-reenable
            from paper_trading.services import PaperExecutionService
            PaperExecutionService._publish_execution_event("SESSION_START", session, "paper")
            
    # Check live sessions
    live_sessions = TradingSession.objects.filter(
        status="PAUSED",
        strategy_id__in=strategy_ids
    )
    for session in live_sessions:
        rule = strategy_to_rule[session.strategy_id]
        if session.updated_at + timedelta(hours=rule.cooldown_hours) <= now:
            session.status = "RUNNING"
            session.error_message = f"Auto-reenabled after {rule.cooldown_hours}h cooldown"
            session.save(update_fields=["status", "error_message", "updated_at"])
            reenabled_count += 1
            # Publish event for live session auto-reenable
            from live_trading.services import LiveExecutionService
            LiveExecutionService._publish_execution_event("SESSION_START", session, "live")

    return {"reenabled": reenabled_count}
