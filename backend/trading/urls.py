from django.urls import path
from . import views

urlpatterns = [
    # Instrument and Watchlist URLs
    path('instruments/search/', views.InstrumentSearchView.as_view(), name='instrument-search'),
    path('watchlist/', views.WatchlistView.as_view(), name='watchlist'),

    # Account, Position, and Order URLs
    path('account/', views.AccountView.as_view(), name='account-details'),
    path('positions/', views.PositionView.as_view(), name='position-list'),
    path('orders/', views.OrderView.as_view(), name='order-list-create'),
    # FIX: Changed <int:pk> to <int:id> to match the lookup_field in OrderDetailView
    path('orders/<int:id>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('history/', views.TradeHistoryView.as_view(), name='trade-history'),
]
