from celery import shared_task

from .models import TradingSession
from .services import LiveExecutionService


@shared_task(name="live_trading.run_active_sessions")
def run_active_sessions(symbol=None):
    processed = 0
    for session in TradingSession.objects.filter(status="RUNNING").select_related("strategy", "broker_credential"):
        if LiveExecutionService.execute_session_once(session, symbol=symbol):
            processed += 1
    return {"processed_sessions": processed}


@shared_task(name="live_trading.process_live_tick", queue="tick")
def process_live_tick(symbol, quote=None, quote_already_cached=False, candle_state=None):
    LiveExecutionService.execute_tick(
        symbol,
        quote=quote,
        quote_already_cached=quote_already_cached,
        candle_state=candle_state,
    )
    return {"status": "processed", "symbol": symbol}


@shared_task(name="live_trading.reconcile_all_active_accounts")
def reconcile_all_active_accounts():
    """
    Periodic task to ensure system state matches broker state for all active users.
    """
    from users.models import User
    # Only sync for users who have a RUNNING session or open positions
    active_user_ids = set(TradingSession.objects.filter(status="RUNNING").values_list("user_id", flat=True))
    
    synced_users = 0
    for user_id in active_user_ids:
        try:
            user = User.objects.get(id=user_id)
            LiveExecutionService.sync_account_state(user, force=True)
            synced_users += 1
        except Exception:
            continue
            
    return {"synced_users": synced_users}


@shared_task(name="live_trading.process_session_tick", queue="strategy_tick")
def process_session_tick(session_id, symbol, candle_state=None):
    from common.enums import StrategyStatus
    try:
        session = TradingSession.objects.select_related("strategy", "broker_credential").get(id=session_id)
        if session.status == "RUNNING" and session.strategy.status == StrategyStatus.ACTIVE:
            LiveExecutionService.execute_session_once(session, symbol, candle_state=candle_state)
    except TradingSession.DoesNotExist:
        pass
    except Exception as exc:
        if 'session' in locals():
            session.status = "ERROR"
            session.error_message = str(exc)
            session.save(update_fields=["status", "error_message", "updated_at"])
