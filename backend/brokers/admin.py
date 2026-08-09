from django.contrib import admin

from .models import BrokerAPILog, BrokerChargeProfile, BrokerCredential, BrokerFundsSnapshot, BrokerSession, OrderReconciliation, OrderSettings


@admin.register(BrokerCredential)
class BrokerCredentialAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "broker_name", "client_id", "is_active", "is_verified", "updated_at"]
    list_filter = ["broker_name", "is_active", "is_verified"]
    search_fields = ["user__username", "client_id", "label"]


@admin.register(BrokerSession)
class BrokerSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "credential", "is_valid", "token_expiry", "last_used_at"]
    list_filter = ["is_valid"]


@admin.register(OrderSettings)
class OrderSettingsAdmin(admin.ModelAdmin):
    list_display = ["id", "broker_credential", "default_slippage_pct", "max_retries"]


@admin.register(OrderReconciliation)
class OrderReconciliationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "broker_order_id", "internal_order_id", "broker_status", "internal_status", "resolved"]
    list_filter = ["resolved", "broker_status", "internal_status"]


@admin.register(BrokerAPILog)
class BrokerAPILogAdmin(admin.ModelAdmin):
    list_display = ["id", "credential", "endpoint", "status_code", "latency_ms", "created_at"]
    list_filter = ["status_code"]


@admin.register(BrokerFundsSnapshot)
class BrokerFundsSnapshotAdmin(admin.ModelAdmin):
    list_display = ["id", "credential", "available_margin", "used_margin", "net_equity", "snapshot_time"]
    list_filter = ["credential__broker_name"]


@admin.register(BrokerChargeProfile)
class BrokerChargeProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'brokerage_per_order', 'brokerage_cap', 'is_default', 'created_at')
    list_filter = ('is_default', 'user')
    search_fields = ('name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
