# backend/trading/apps.py
from django.apps import AppConfig

class TradingConfig(AppConfig):
    name = "trading"

    def ready(self):
        # import signals to register them
        import trading.signals  # noqa: F401
