from django.urls import path
from .views import (
    InstrumentSearchView, WatchlistView, AccountView, PositionView, 
    OrderView, OrderDetailView, TradeHistoryView, close_position,
    portfolio_summary, execute_market_order
)

urlpatterns = [
    # Instrument and Watchlist endpoints
    path('instruments/search/', InstrumentSearchView.as_view(), name='instrument-search'),
    path('watchlist/', WatchlistView.as_view(), name='watchlist'),
    
    # Account and Portfolio endpoints
    path('account/', AccountView.as_view(), name='account-details'),
    path('positions/', PositionView.as_view(), name='positions-list'),
    path('positions/<int:position_id>/close/', close_position, name='close-position'),
    path('portfolio/summary/', portfolio_summary, name='portfolio-summary'),
    
    # Order management endpoints
    path('orders/', OrderView.as_view(), name='order-list-create'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:order_id>/execute/', execute_market_order, name='execute-order'),
    
    # Trade history endpoint
    path('trades/', TradeHistoryView.as_view(), name='trade-history'),
]
