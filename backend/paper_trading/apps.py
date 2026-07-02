from django.apps import AppConfig


class PaperTradingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'paper_trading'
    verbose_name = 'Paper Trading'

    def ready(self):
        import paper_trading.signals  # noqa: F401
