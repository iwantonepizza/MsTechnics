"""T-3-005: admin для заявок."""
from django.contrib import admin
from apps.workflow.applications.models import Application, ApplicationStatus, ApplicationEvent


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "display", "panel", "status", "last_update_date_time")
    list_filter = ("status",)
    search_fields = ("panel__name", "id")
    ordering = ("-last_update_date_time",)


@admin.register(ApplicationStatus)
class ApplicationStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(ApplicationEvent)
class ApplicationEventAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "stage", "actor_name", "occurred_at")
    list_filter = ("stage",)
    date_hierarchy = "occurred_at"
    readonly_fields = [f.name for f in ApplicationEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
