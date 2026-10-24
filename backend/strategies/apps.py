from django.apps import AppConfig


class StrategiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'strategies'
    verbose_name = 'Trading Strategies'

    def ready(self):
        import strategies.signals  # noqa: F401 - register model signal handlers
        return super().ready()