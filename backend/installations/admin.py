from django.contrib import admin
from django.db import transaction
from common.admin import ImmutableAdmin
from .models import PrivateContract, Installation, LicenseIssuance, SupportAuthorization


@admin.register(PrivateContract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ["reference", "customer", "rights", "approved", "paid_through", "revision"]
    readonly_fields = ["revision"]

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if change:
                obj.revision = PrivateContract.objects.select_for_update().get(pk=obj.pk).revision + 1
            super().save_model(request, obj, form, change)


@admin.register(Installation)
class InstallationAdmin(admin.ModelAdmin):
    list_display = ["id", "contract", "enabled", "last_refresh"]
    readonly_fields = ["id", "contract", "created_at", "last_refresh"]
    exclude = ["activation_hash"]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
admin.site.register(LicenseIssuance, ImmutableAdmin)
admin.site.register(SupportAuthorization, ImmutableAdmin)
