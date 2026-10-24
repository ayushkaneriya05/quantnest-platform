from django.contrib import admin

from .models import BrokerAPILog, BrokerChargeProfile, BrokerCredential, BrokerFundsSnapshot, BrokerSession


@admin.register(BrokerCredential)
class BrokerCredentialAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "broker_name", "client_id", "is_active", "is_verified", "updated_at"]
    list_filter = ["broker_name", "is_active", "is_verified"]
    search_fields = ["user__username", "client_id", "label"]
    fields = ["user", "broker_name", "label", "client_id", "is_active", "is_verified", "last_verified_at"]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BrokerSession)
class BrokerSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "credential", "is_valid", "token_expiry", "last_used_at"]
    list_filter = ["is_valid"]




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
    readonly_fields = ('is_default', 'created_at', 'updated_at')
    actions = ['set_default']

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (('user',) if obj else ())

    def get_deleted_objects(self, objs, request):
        deleted, counts, permissions, protected = super().get_deleted_objects(objs, request)
        protected.extend(str(profile) for profile in objs if profile.is_default)
        return deleted, counts, permissions, protected

    @admin.action(description='Set selected charge profile as default', permissions=['change'])
    def set_default(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Select exactly one charge profile.', level='error')
            return
        queryset.get().set_default()
        self.message_user(request, 'Default charge profile updated.')
