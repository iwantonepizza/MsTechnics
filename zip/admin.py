from django.contrib import admin

from zip.models import *


class DisplayAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'description', 'rows', 'cols', 'condition',
                    'camera_link', 'file')  # Поля, отображаемые в списке
    list_filter = ('name', 'city', 'condition')  # Фильтры для боковой панели
    search_fields = ('name', 'city', 'description')  # По каким полям осуществляется поиск
    ordering = ('name',)  # Порядок сортировки (убывание по времени выполнения)
    list_editable = (
        'description', 'condition', 'camera_link', 'file')  # Поля, которые можно редактировать прямо в списке
    fields = [
        'name',
        ('city', 'cols', 'rows'),
        'description',
        'condition',
        'camera_link',
    ]


admin.site.register(Display, DisplayAdmin)



@admin.register(Panels)
class PanelsAdmin(admin.ModelAdmin):
    pass


@admin.register(DailyTask)
class DailyTaskAdmin(admin.ModelAdmin):
    pass


@admin.register(Wires)
class WiresAdmin(admin.ModelAdmin):
    pass


@admin.register(Hubs)
class HubsAdmin(admin.ModelAdmin):
    pass


@admin.register(Lamels)
class LamelsAdmin(admin.ModelAdmin):
    pass


@admin.register(Contactlist)
class ContactlistAdmin(admin.ModelAdmin):
    pass

@admin.register(Cell)
class DailyTaskAdmin(admin.ModelAdmin):
    pass