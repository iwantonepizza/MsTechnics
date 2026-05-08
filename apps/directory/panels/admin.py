"""T-3-005: admin для панелей."""
from django.contrib import admin

from apps.core.references.models import Department
from apps.directory.panels.models import Panel


@admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    list_display = ("name", "display", "condition", "department")
    list_filter = ("condition", "department")
    search_fields = ("name",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
