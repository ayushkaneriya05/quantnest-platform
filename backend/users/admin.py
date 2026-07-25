from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import APIKey, BackupCode, User, UserSession


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "username", "is_staff", "is_active", "is_2fa_enabled", "date_joined")
    list_filter = ("is_staff", "is_active", "is_2fa_enabled", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username", "first_name", "last_name", "bio", "avatar")}),
        ("Security", {"fields": ("is_2fa_enabled",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("prefix", "user", "name", "created_at", "last_used")
    list_filter = ("created_at",)
    search_fields = ("prefix", "user__email", "name")
    readonly_fields = ("key_hash", "prefix", "created_at")


@admin.register(BackupCode)
class BackupCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "is_used", "created_at", "used_at")
    list_filter = ("is_used", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("code_hash", "created_at", "used_at")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "session_id",
        "ip_address",
        "browser",
        "os",
        "device_type",
        "last_activity",
        "expires_at",
    )
    list_filter = ("browser", "os", "device_type", "created_at", "last_activity")
    search_fields = ("user__email", "user__username", "ip_address", "session_id")
    readonly_fields = ("session_id", "created_at", "last_activity", "expires_at")
    ordering = ("-last_activity",)

