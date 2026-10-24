"""QuantNest API, administrator and health routes."""
from django.contrib import admin
from django.urls import path, include
from .health import health_check
from commercial.views import get_public_catalog
from customer_support.views import EnquiryView


urlpatterns = [
    path("api/v1/public/catalog/", get_public_catalog),
    path("api/v1/public/enquiries/", EnquiryView.as_view()),
    path("api/v1/billing/", include("commercial.urls")),
    path("api/v1/support/", include("customer_support.urls")),
    path("admin/", admin.site.urls),
    path("api/v1/users/", include("users.urls")),
    path("health/", health_check, name="health_check"),
    path("api/v1/market/", include("marketdata.urls")), 
    path("api/v1/trading/", include("trading.urls")),
    path("api/v1/common/", include("common.urls")),
    path("api/v1/strategies/", include("strategies.urls")),
    path("api/v1/instruments/", include("instruments.urls")),
    path("api/v1/rules/", include("rules_engine.urls")),
    path("api/v1/backtest/", include("backtesting.urls")),
    path("api/v1/paper/", include("paper_trading.urls")),
    path("api/v1/brokers/", include("brokers.urls")),
    path("api/v1/live/", include("live_trading.urls")),
    path("api/v1/analytics/", include("analytics.urls")),
    path("api/v1/journal/", include("trade_journal.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/research/", include("research.urls")),
    path("api/v1/audit/", include("audit.urls")),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
