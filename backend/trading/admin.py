from django.contrib import admin
from .models import Instrument, Watchlist,TradeHistory,Account,Position,Order

admin.site.register(Instrument)
admin.site.register(Watchlist)
admin.site.register(TradeHistory)
admin.site.register(Account)
admin.site.register(Position)
admin.site.register(Order)