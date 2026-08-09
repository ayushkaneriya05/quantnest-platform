from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from strategies.models import Strategy
from common.enums import StrategyStatus

@shared_task(name="risk_management.check_and_reenable_strategies")
def check_and_reenable_strategies():
    """
    Check for PAUSED strategies that were disabled by risk rules 
    and re-enable them after the cooldown period.
    """
    # Find strategies that are PAUSED and have auto_reenable = True and require_manual_review = False
    # TODO: Rewrite this task to check PaperTradingSession and TradingSession statuses
    # instead of Strategy status, since execution control has moved to sessions.
    reenabled = 0

    return {"reenabled": reenabled}
