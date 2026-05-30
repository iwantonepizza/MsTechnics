"""T-3-005: admin для пользователей."""
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.users.models import MsUser, Role
from apps.core.users.permissions import EXTRA_PERMISSION_CHOICES


class MsUserAdminForm(forms.ModelForm):
    extra_permissions = forms.MultipleChoiceField(
        required=False,
        choices=EXTRA_PERMISSION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Дополнительные права",
    )

    class Meta:
        model = MsUser
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["extra_permissions"].initial = list(self.instance.extra_permissions or [])

    def clean_extra_permissions(self):
        return list(self.cleaned_data["extra_permissions"])


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")


@admin.register(MsUser)
class MsUserAdmin(UserAdmin):
    form = MsUserAdminForm
    list_display = ("username", "first_name", "last_name", "permission", "email", "show_activity_feed", "is_active")
    list_filter = ("permission", "is_active", "roles", "show_activity_feed", "allowed_city")
    search_fields = ("username", "email", "first_name", "last_name")
    filter_horizontal = ("roles", "allowed_city", "groups", "user_permissions")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Доступ",
            {
                "fields": (
                    "permission",
                    "roles",
                    "extra_permissions",
                    "allowed_city",
                    "telegram_id",
                    "max_id",
                    "show_activity_feed",
                )
            },
        ),
    )
