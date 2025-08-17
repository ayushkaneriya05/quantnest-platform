# backend/trading/admin.py
from django.contrib import admin
from .models import PaperAccount, PaperOrder, PaperTrade, PaperPosition, AuditLog

# Register your models here to make them accessible in the Django admin interface.
admin.site.register(PaperAccount)
admin.site.register(PaperOrder)
admin.site.register(PaperTrade)
admin.site.register(PaperPosition)
admin.site.register(AuditLog)