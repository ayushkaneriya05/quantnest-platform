from django.contrib import admin
from .models import Watchlist,TradeHistory,Account,Position,Order,ClosedPositionLog

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ('account', 'instrument', 'oco_linked_order', 'position_link')
    list_display = ('id', 'account', 'transaction_type', 'quantity', 'instrument', 'order_type', 'status', 'price')
    list_filter = ('status', 'order_type', 'transaction_type')

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    raw_id_fields = ('account', 'instrument')
    list_display = ('id', 'account', 'instrument', 'quantity', 'average_price')

@admin.register(TradeHistory)
class TradeHistoryAdmin(admin.ModelAdmin):
    raw_id_fields = ('order',)
    list_display = ('id', 'order', 'executed_price', 'quantity', 'timestamp')

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('id', 'user', 'balance', 'realized_pnl', 'unrealized_pnl')

@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)

@admin.register(ClosedPositionLog)
class ClosedPositionLogAdmin(admin.ModelAdmin):
    raw_id_fields = ('account', 'instrument')
    list_select_related = ('account', 'instrument')
    list_display = ('id', 'account', 'instrument', 'side', 'quantity', 'realized_pnl', 'entry_time', 'exit_time')
    list_filter = ('side',)
    search_fields = ('instrument__sym_ticker', 'account__user__username')
