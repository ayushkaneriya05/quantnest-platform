from django.apps import AppConfig
from django.core.management import call_command
import threading
import logging

logger = logging.getLogger(__name__)

class TradingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trading"

    def ready(self):
        """
        Run commands only once when the server starts.
        Using a thread so it doesn't block Daphne startup.
        """
        import trading.receivers
        def run_startup_commands():
            try:
                call_command("order_executor")
                logger.info("✅ order_executor executed successfully at startup.")
            except Exception as e:
                logger.error(f"❌ Error running startup commands: {e}")

        # Prevent duplicate runs (e.g., autoreload in dev mode)
        if not hasattr(self, "already_ran"):
            self.already_ran = True
            threading.Thread(target=run_startup_commands).start()
