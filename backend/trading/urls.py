# backend/trading/urls.py
from django.urls import path
from .views import (
    PlaceOrderView, CancelOrderView, ModifyOrderView, OrdersListView, TradesListView, AuditLogsListView,  PositionsView, AccountView, OrderbookSnapshotView, BracketOrderView, CoverOrderView
)

urlpatterns = [
    path("orders/", PlaceOrderView.as_view(), name="place-order"),
    path("orders/list/", OrdersListView.as_view(), name="orders-list"),
    path("orders/<int:order_id>/cancel/", CancelOrderView.as_view(), name="cancel-order"),
    path("orders/<int:order_id>/modify/", ModifyOrderView.as_view(), name="modify-order"),
    path("orders/trades/", TradesListView.as_view(), name="trades-list"),
    path("positions/", PositionsView.as_view(), name="positions"),
    path("account/", AccountView.as_view(), name="account"),
    path("orderbook/<str:symbol>/", OrderbookSnapshotView.as_view(), name="orderbook-snapshot"),
    path("bracket/", BracketOrderView.as_view(), name="bracket-order"),
    path("cover/", CoverOrderView.as_view(), name="cover-order"),
    path("orders/audit-logs/", AuditLogsListView.as_view(), name="audit-logs"),

]