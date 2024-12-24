from django.contrib import admin

from application.models import *


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'display__description', 'panel', 'status__description', 'comment_monitoring', 'time_monitoring', 'comment_control',
                    'time_control', 'comment_service', 'time_service')  # Поля, отображаемые в списке
    list_filter = ('display__description', 'status__description')  # Фильтры для боковой панели
    search_fields = ('description', 'panel', 'id')  # По каким полям осуществляется поиск
    ordering = ('status',)  # Порядок сортировки (убывание по времени выполнения)

    fields = [
        ('display', 'panel', 'status'),
        ('comment_monitoring', 'time_monitoring'),
        ('comment_control', 'time_control'),
        ('comment_service', 'time_service'),
    ]


admin.site.register(Application, ApplicationAdmin)


class ApplicationStatusAdmin(admin.ModelAdmin):
    list_display = ('description', 'color', 'color_text', 'icon')  # Поля, отображаемые в списке
    search_fields = ('description',)  # По каким полям осуществляется поиск
    ordering = ('id',)  # Порядок сортировки (убывание по времени выполнения)
    list_editable = ('color', 'color_text', 'icon')  # Поля, которые можно редактировать прямо в списке
    fields = [
        'name',
        'description',
        ('color', 'color_text', 'icon'),
    ]


admin.site.register(ApplicationStatus, ApplicationStatusAdmin)


class ApplicationHistoryReportAdmin(admin.ModelAdmin):
    list_display = ('display', 'panel', 'description', 'comment', 'time', 'user')  # Поля, отображаемые в списке
    list_filter = ('display__description', 'description', 'comment', 'time', 'user')  # Фильтры для боковой панели
    search_fields = ('display', 'panel', 'description', 'comment', 'time', 'user')  # По каким полям осуществляется поиск
    ordering = ('display',)  # Порядок сортировки (убывание по времени выполнения)
    list_editable = ('panel', 'description', 'comment', 'time', 'user')
    list_display_links = ['display']  # Ссылка на первое поле
    # Поля, которые можно редактировать прямо в списке
    fields = [
        ('display', 'panel', 'time'),
        ('user', 'comment'),
        'description',
    ]


admin.site.register(ApplicationHistoryReport, ApplicationHistoryReportAdmin)
