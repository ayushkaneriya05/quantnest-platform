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
    paused_strategies = Strategy.objects.filter(
        status=StrategyStatus.PAUSED,
        auto_disable_rules__is_active=True,
        auto_disable_rules__auto_reenable=True,
        auto_disable_rules__require_manual_review=False
    ).distinct()
    
    reenabled = 0
    for strategy in paused_strategies:
        # Check if cooldown has passed since last status change
        # (Assuming updated_at was the time it was paused)
        # We take the maximum cooldown among all matching rules
        rules = strategy.auto_disable_rules.filter(
            is_active=True, 
            auto_reenable=True, 
            require_manual_review=False
        )
        cooldown_hours = max((r.cooldown_hours for r in rules), default=24)
        
        if timezone.now() >= strategy.updated_at + timedelta(hours=cooldown_hours):
            strategy.status = StrategyStatus.ACTIVE
            strategy.save(update_fields=["status", "updated_at"])
            
            # Log violation resolution
            from risk_management.models import RiskViolation
            from common.enums import ViolationAction
            RiskViolation.objects.create(
                user=strategy.user,
                strategy=strategy,
                violation_type="RE_ENABLED",
                message=f"Strategy auto-reenabled after {cooldown_hours}h cooldown",
                action_taken=ViolationAction.LOGGED,
            )
            reenabled += 1

    return {"reenabled": reenabled}
