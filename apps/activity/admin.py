"""T-8-072: read-only admin для журнала активности."""
from django.contrib import admin

from apps.activity.models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "actor_name", "description", "occurred_at")
    list_filter = ("event_type", "occurred_at")
    search_fields = ("actor_name", "description", "comment")
    date_hierarchy = "occurred_at"
    readonly_fields = [field.name for field in ActivityLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
