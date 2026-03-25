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
    path("api/v1/portfolio/", include("portfolio.urls")),
    # Algo Trading APIs (Phase 3)
    path("api/v1/backtest/", include("backtesting.urls")),
    # Algo Trading APIs (Phase 4)
    path("api/v1/paper/", include("paper_trading.urls")),
]