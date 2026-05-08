"""T-3-005: admin для справочников."""
from django.contrib import admin
from apps.core.references.models import Cities, Color, Smile, Condition, Department


@admin.register(Cities)
class CitiesAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("name", "hex_color")


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
