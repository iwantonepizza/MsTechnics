from django.contrib import admin
from django.db.models import F, QuerySet

from apps.directory.storage.models import Connectors, Hubs, Lamels, PowerBlocks, Wires


class LowStockFilter(admin.SimpleListFilter):
    title = "низкий остаток"
    parameter_name = "low_stock"

    def lookups(self, _request, _model_admin):
        return (
            ("yes", "Да"),
            ("no", "Нет"),
        )

    def queryset(self, _request, queryset: QuerySet):
        if self.value() == "yes":
            return queryset.filter(count__lt=F("low_stock_threshold"))
        if self.value() == "no":
            return queryset.filter(count__gte=F("low_stock_threshold"))
        return queryset


class StorageItemAdmin(admin.ModelAdmin):
    list_display = ("name", "count", "low_stock_threshold", "is_low_stock_display")
    list_editable = ("count", "low_stock_threshold")
    list_filter = (LowStockFilter,)
    search_fields = ("name", "description")
    ordering = ("id",)

    @admin.display(boolean=True, description="Низкий остаток")
    def is_low_stock_display(self, obj) -> bool:
        return obj.is_low_stock


admin.site.register(Wires, StorageItemAdmin)
admin.site.register(Hubs, StorageItemAdmin)
admin.site.register(Lamels, StorageItemAdmin)
admin.site.register(PowerBlocks, StorageItemAdmin)
admin.site.register(Connectors, StorageItemAdmin)
