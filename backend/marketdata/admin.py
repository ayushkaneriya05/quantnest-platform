# backend/marketdata/admin.py
from django.contrib import admin
from .models import MarketDataToken

# Register your models here.
admin.site.register(MarketDataToken)