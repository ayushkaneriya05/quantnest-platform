from celery import shared_task

from strategies.models import Strategy

from .services import AIEngineService


@shared_task(name="ai_engine.generate_strategy_recommendations")
def generate_strategy_recommendations():
    count = 0
    for strategy in Strategy.objects.filter(status="ACTIVE"):
        AIEngineService.refresh_strategy_suite(strategy)
        count += 1
    return {"generated": count}
