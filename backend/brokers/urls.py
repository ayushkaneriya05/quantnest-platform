from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BrokerAPILogViewSet,
    BrokerCredentialViewSet,
    BrokerSessionViewSet,
    OrderReconciliationViewSet,
    OrderSettingsViewSet,
    fyers_broker_callback,
)

router = DefaultRouter()
router.register(r"credentials", BrokerCredentialViewSet, basename="broker-credential")
router.register(r"sessions", BrokerSessionViewSet, basename="broker-session")
router.register(r"settings", OrderSettingsViewSet, basename="broker-settings")
router.register(r"reconciliation", OrderReconciliationViewSet, basename="order-reconciliation")
router.register(r"logs", BrokerAPILogViewSet, basename="broker-api-log")

urlpatterns = [
    path("credentials/fyers/callback/", fyers_broker_callback, name="fyers_broker_callback"),
    path("", include(router.urls)),
]
