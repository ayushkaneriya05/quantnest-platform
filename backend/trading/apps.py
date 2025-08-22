from django.apps import AppConfig

class TradingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trading'

    def ready(self):
        # This line is crucial. It imports and connects the signal receivers
        # as soon as the Django application is ready.
        import trading.receivers
