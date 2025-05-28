from django.contrib import admin

from zip.models import *


class DisplayAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'description', 'rows', 'cols',
                    'camera_link', 'file', 'project_photo', 'slug')  # Поля, отображаемые в списке
    list_filter = ('name', 'city')  # Фильтры для боковой панели
    search_fields = ('name', 'city', 'description')  # По каким полям осуществляется поиск
    ordering = ('name',)  # Порядок сортировки (убывание по времени выполнения)
    list_editable = (
        'description', 'camera_link', 'file', 'project_photo',
        'slug')  # Поля, которые можно редактировать прямо в списке
    fields = [
        'name',
        ('city', 'cols', 'rows'),
        'description',
        'camera_link',
        'file',
        'project_photo',
        'slug'
    ]


admin.site.register(Display, DisplayAdmin)


@admin.register(Panels)
class PanelsAdmin(admin.ModelAdmin):
    pass


@admin.register(PhotoDisplay)
class PhotoDisplayAdmin(admin.ModelAdmin):
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


class CellAdmin(admin.ModelAdmin):
    list_display = ('display__name', 'row', 'col', 'panel')
    list_filter = ('display__name', 'row', 'col', 'panel')
    search_fields = ('display__name', 'row', 'col', 'panel')
    fields = [
        'display',
        ('row', 'col'),
        'panel'
    ]


