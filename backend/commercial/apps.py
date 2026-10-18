from django.apps import AppConfig


class CommercialConfig(AppConfig):
    name = "commercial"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import usage  # noqa: F401 - register final task outcomes
