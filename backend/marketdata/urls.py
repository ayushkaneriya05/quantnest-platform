from django.urls import path
from .views import historical_data, live_quote, market_status, symbols_list

urlpatterns = [
    path('historical/', historical_data, name='historical-data'),
    path('quote/', live_quote, name='live-quote'),
    path('status/', market_status, name='market-status'),
    path('symbols/', symbols_list, name='symbols-list'),
]
