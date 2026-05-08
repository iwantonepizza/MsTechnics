"""T-3-005: admin для пользователей."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.core.users.models import MsUser


@admin.register(MsUser)
class MsUserAdmin(UserAdmin):
    list_display = ("username", "permission", "email", "is_active")
    list_filter = ("permission", "is_active")
    search_fields = ("username", "email")
    fieldsets = UserAdmin.fieldsets + (
        ("MS Technics", {"fields": ("permission", "allowed_city", "telegram_id", "max_id")}),
    )
