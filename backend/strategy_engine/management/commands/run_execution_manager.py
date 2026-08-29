import json
import logging
import time

from django.core.management.base import BaseCommand
from django.core.cache import cache
from strategy_engine.manager import SessionExecutionManager
from live_trading.models import TradingSession
from paper_trading.models import PaperTradingSession
from instruments.services import InstrumentResolver

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Runs the Redis Pub/Sub Session Execution Manager to orchestrate strategy workers."

    def handle(self, *args, **options):
        manager = SessionExecutionManager()
        
        # 1. Sync any existing RUNNING sessions on boot (catch-up mechanism)
        self.stdout.write("Syncing active sessions on boot...")
        
        # Sync Live
        for session in TradingSession.objects.filter(status="RUNNING").select_related("strategy").prefetch_related(
            "strategy__watchlist_instruments__execution_routes__target_underlying_instrument",
        ):
            inst_ids = InstrumentResolver.execution_instrument_ids(session.strategy)
            manager.start_worker(str(session.id), str(session.strategy_id), "live", inst_ids)
            
        # Sync Paper
        for session in PaperTradingSession.objects.filter(status="RUNNING").select_related("strategy").prefetch_related(
            "strategy__watchlist_instruments__execution_routes",
        ):
            inst_ids = InstrumentResolver.execution_instrument_ids(session.strategy)
            manager.start_worker(str(session.id), str(session.strategy_id), "paper", inst_ids)

        self.stdout.write("Boot sync complete. Listening for execution events on Redis...")

        # 2. Connect to Redis Pub/Sub
        # Handle both raw redis clients and django-redis backends
        if hasattr(cache, 'client'):
            redis_client = cache.client.get_client()
        else:
            # Fallback if using a non-redis cache but redis is available
            import redis
            from django.conf import settings
            redis_url = getattr(settings, 'CHANNEL_REDIS_URL', 'redis://localhost:6379/0')
            redis_client = redis.from_url(redis_url)

        pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe("execution_control")

        # 3. Main event loop
        try:
            for message in pubsub.listen():
                try:
                    data = json.loads(message['data'])
                    action = data.get("action")
                    session_id = str(data.get("session_id"))
                    scope = data.get("scope")
                    
                    if action == "SESSION_START":
                        strategy_id = str(data.get("strategy_id"))
                        inst_ids = data.get("instrument_ids", [])
                        logger.info(f"Received SESSION_START for {scope} session {session_id}")
                        manager.start_worker(session_id, strategy_id, scope, inst_ids)
                        
                    elif action == "SESSION_STOP":
                        logger.info(f"Received SESSION_STOP for {scope} session {session_id}")
                        manager.stop_worker(session_id, scope)

                    elif action == "SESSION_PAUSE":
                        logger.info(f"Received SESSION_PAUSE for {scope} session {session_id}")
                        manager.pause_worker(session_id, scope)

                    elif action == "VERSION_CHANGE":
                        strategy_id = str(data.get("strategy_id"))
                        inst_ids = data.get("instrument_ids", [])
                        logger.info(f"Received VERSION_CHANGE for {scope} session {session_id}")
                        manager.stop_worker(session_id, scope)
                        manager.start_worker(session_id, strategy_id, scope, inst_ids)
                        
                    elif action == "HEALTH_CHECK":
                        manager.check_health()
                        
                except json.JSONDecodeError:
                    logger.error("Failed to decode message from execution_control channel")
                except Exception as e:
                    logger.error(f"Error processing pubsub message: {e}")
                    
        except KeyboardInterrupt:
            self.stdout.write("Shutting down execution manager...")
        finally:
            manager.cleanup()
            pubsub.close()
            self.stdout.write("Execution manager terminated cleanly.")
