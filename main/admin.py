from django.contrib import admin
from main.models import *


class CitiesAdmin(admin.ModelAdmin):
    list_display = ('name', 'description',)
    ordering = ('name',)
    fields = ['name',
              'description',
              'displays',
              'slug'
              ]


admin.site.register(Cities, CitiesAdmin)




class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_color',)  # Поля, отображаемые в списке
    search_fields = ('name', 'hex_color')  # По каким полям осуществляется поиск
    fields = [
        'name',
        'hex_color',

    ]


admin.site.register(Color, ColorAdmin)


class SmileAdmin(admin.ModelAdmin):
    list_display = ('smile_icon',)  # Поля, отображаемые в списке
    ordering = ('smile_icon',)  # Порядок сортировки (убывание по времени выполнения)


admin.site.register(Smile, SmileAdmin)


class ConditionAdmin(admin.ModelAdmin):
    list_display = ('description', 'color', 'color_text', 'icon')  # Поля, отображаемые в списке
    list_filter = ('name', 'color', 'icon')  # Фильтры для боковой панели
    search_fields = ('name', 'icon')  # По каким полям осуществляется поиск
    ordering = ('name',)  # Порядок сортировки (убывание по времени выполнения)
    list_editable = ('color', 'color_text', 'icon')  # Поля, которые можно редактировать прямо в списке
    fields = [
        'name',
        ('color', 'color_text', 'icon'),
        'description',

    ]


admin.site.register(Condition, ConditionAdmin)


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('description', 'color', 'color_text', 'icon')  # Поля, отображаемые в списке
    search_fields = ('description', 'icon')  # По каким полям осуществляется поиск
    ordering = ('name',)  # Порядок сортировки (убывание по времени выполнения)
    list_editable = ('color', 'color_text', 'icon')  # Поля, которые можно редактировать прямо в списке
    fields = [
        'name',
        ('color', 'color_text', 'icon'),
        'description',

    ]


admin.site.register(Department, DepartmentAdmin)
