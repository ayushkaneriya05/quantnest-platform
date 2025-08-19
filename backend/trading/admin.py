from django.contrib import admin
from .models import Instrument, Watchlist

admin.site.register(Instrument)
admin.site.register(Watchlist)