"""T-3-005 / T-8-072: admin для экранов."""
from django.contrib import admin

from apps.directory.displays.models import Cell, Display, DisplayNote, PhotoDisplay


@admin.register(Display)
class DisplayAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "rows", "cols", "camera_link")
    list_filter = ("city",)
    search_fields = ("name", "description", "slug")


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    list_display = ("id", "display", "row", "col", "panel")
    list_filter = ("display",)
    search_fields = ("display__name", "panel__name")


@admin.register(DisplayNote)
class DisplayNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "display", "author_name", "department", "created_at")
    list_filter = ("department", "created_at")
    search_fields = ("display__name", "author_name", "text")
    date_hierarchy = "created_at"


@admin.register(PhotoDisplay)
class PhotoDisplayAdmin(admin.ModelAdmin):
    list_display = ("id", "display", "uploaded_at")
    list_filter = ("display",)
    search_fields = ("display__name",)
