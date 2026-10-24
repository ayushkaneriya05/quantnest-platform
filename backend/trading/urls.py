from django.urls import path
from . import views

urlpatterns = [
    # Instrument and Watchlist URLs
    path('instruments/search/', views.InstrumentSearchView.as_view(), name='instrument-search'),
    path('watchlist/', views.WatchlistView.as_view(), name='watchlist'),
    path('watchlists/', views.WatchlistCollectionView.as_view(), name='terminal-watchlists'),
    path('watchlists/<int:pk>/', views.WatchlistDetailView.as_view(), name='terminal-watchlist-detail'),
    path('terminal/', views.TerminalSnapshotView.as_view(), name='terminal-snapshot'),
    path('status/', views.TerminalStatusView.as_view(), name='terminal-status'),

    # Account, Position, and Order URLs
    path('account/', views.AccountView.as_view(), name='account-details'),
    path('positions/', views.PositionView.as_view(), name='position-list'),
    path('positions/<int:id>/', views.PositionDetailView.as_view(), name='position-detail'),
    path('positions/<int:id>/action/', views.PositionActionView.as_view(), name='position-action'),
    path('orders/cancel/', views.CancelOrdersView.as_view(), name='cancel-terminal-orders'),
    path('orders/preview/', views.OrderPreviewView.as_view(), name='preview-terminal-order'),
    path('orders/', views.OrderView.as_view(), name='order-list-create'),
    path('orders/<int:id>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('trades/', views.TradeHistoryView.as_view(), name='trade-history'),
    path('pnl-report/', views.ClosedPositionLogView.as_view(), name='pnl-report'),
]
