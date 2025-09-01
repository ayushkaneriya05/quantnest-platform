from django.apps import AppConfig
from django.core.management import call_command
import threading
import logging

logger = logging.getLogger(__name__)

class MyAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "marketdata"

    def ready(self):
        """
        Run commands only once when the server starts.
        Using a thread so it doesn't block Daphne startup.
        """
        def run_startup_commands():
            try:
                call_command("fyers_ingest")
                logger.info("✅ fyers_ingest executed successfully at startup.")
            except Exception as e:
                logger.error(f"❌ Error running startup commands: {e}")
    
        def run_startup_commands_1():
            try:
                call_command("aggregate_candles")
                logger.info("✅ aggregate_candles executed successfully at startup.")                
            except Exception as e:
                logger.error(f"❌ Error running startup commands: {e}")
                
        def run_startup_commands_2():
            try:
                call_command("replay_broadcaster")
                logger.info("✅ replay_broadcaster executed successfully at startup.")
            except Exception as e:
                logger.error(f"❌ Error running startup commands: {e}")

        # Prevent duplicate runs (e.g., autoreload in dev mode)
        if not hasattr(self, "already_ran"):
            self.already_ran = True
            threading.Thread(target=run_startup_commands).start()
            threading.Thread(target=run_startup_commands_1).start()
            threading.Thread(target=run_startup_commands_2).start()
