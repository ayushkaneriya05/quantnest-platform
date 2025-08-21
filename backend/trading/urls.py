from django.urls import path
from .views import (
    InstrumentSearchView, WatchlistView, AccountView, PositionView,
    OrderView, OrderDetailView, OrderCancelView, PositionCloseView,
    PortfolioSummaryView
)

urlpatterns = [
    # Instrument and watchlist endpoints
    path('instruments/search/', InstrumentSearchView.as_view(), name='instrument-search'),
    path('watchlist/', WatchlistView.as_view(), name='watchlist'),

    # Account and portfolio endpoints
    path('account/', AccountView.as_view(), name='account-details'),
    path('portfolio/summary/', PortfolioSummaryView.as_view(), name='portfolio-summary'),

    # Position endpoints
    path('positions/', PositionView.as_view(), name='positions-list'),
    path('positions/<int:pk>/close/', PositionCloseView.as_view(), name='position-close'),

    # Order endpoints
    path('orders/', OrderView.as_view(), name='order-list-create'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
]
