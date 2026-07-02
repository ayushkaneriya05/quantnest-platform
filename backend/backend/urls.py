"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def health_check(request):
    """Health check endpoint for monitoring."""
    return JsonResponse({"status": "healthy", "message": "QuantNest API is running"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/users/", include("users.urls")),
    path("health/", health_check, name="health_check"),
    path("api/v1/market/", include("marketdata.urls")), 
    path("api/v1/trading/", include("trading.urls")),
    # Common APIs (enums, etc.)
    path("api/v1/common/", include("common.urls")),
    # Algo Trading APIs (Phase 1)
    path("api/v1/strategies/", include("strategies.urls")),
    path("api/v1/instruments/", include("instruments.urls")),
    path("api/v1/rules/", include("rules_engine.urls")),
    # Algo Trading APIs (Phase 2)
    path("api/v1/risk/", include("risk_management.urls")),
    path("api/v1/portfolio/", include("paper_trading.urls")),
    # Algo Trading APIs (Phase 3)
    path("api/v1/backtest/", include("backtesting.urls")),
    # Algo Trading APIs (Phase 4)
    path("api/v1/paper/", include("paper_trading.urls")),
    # Algo Trading APIs (Phase 5-10)
    path("api/v1/brokers/", include("brokers.urls")),
    path("api/v1/live/", include("live_trading.urls")),
    path("api/v1/analytics/", include("analytics.urls")),
    path("api/v1/journal/", include("trade_journal.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/ai/", include("ai_engine.urls")),
    path("api/v1/marketplace/", include("marketplace.urls")),
    path("api/v1/audit/", include("audit.urls")),
    path("api/v1/events/", include("platform_events.events_urls")),
    path("api/v1/activity/", include("platform_events.activity_urls")),
    path("api/v1/community/", include("community.urls")),
    path("api/v1/gamification/", include("gamification.urls")),
    path("api/v1/challenges/", include("gamification.challenges_urls")),
    path("api/v1/learning/", include("learning.urls")),
    path("api/v1/reputation/", include("reputation.urls")),
    path("api/v1/proofs/", include("reputation.proofs_urls")),
    path("api/v1/replays/", include("reputation.replays_urls")),
    path("api/v1/moderation/", include("reputation.moderation_urls")),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
