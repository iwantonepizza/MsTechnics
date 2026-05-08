"""T-3-005: admin для экранов."""
from django.contrib import admin
from apps.directory.displays.models import Display, Cell


@admin.register(Display)
class DisplayAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "rows", "cols")
    list_filter = ("city",)
    search_fields = ("name", "description")


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    list_display = ("id", "display", "row", "col", "panel")
    list_filter = ("display",)
