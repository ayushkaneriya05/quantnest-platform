from django.urls import path
from .views import InstrumentSearchView, WatchlistView

urlpatterns = [
    path('instruments/search/', InstrumentSearchView.as_view(), name='instrument-search'),
    path('watchlist/', WatchlistView.as_view(), name='watchlist'),
]
# ... existing urls
from .views import AccountView, PositionView, OrderView, OrderDetailView

urlpatterns += [
    path('account/', AccountView.as_view(), name='account-details'),
    path('positions/', PositionView.as_view(), name='positions-list'),
    path('orders/', OrderView.as_view(), name='order-list-create'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
]