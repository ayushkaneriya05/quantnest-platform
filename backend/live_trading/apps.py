from django.apps import AppConfig


class LiveTradingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "live_trading"
    verbose_name = "Live Trading"

    def ready(self):
        from . import signals  # noqa: F401
        try:
            from .services import LiveExecutionService
            LiveExecutionService.rebuild_runtime_state_from_db()
        except Exception:
            pass
