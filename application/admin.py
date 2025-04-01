from django.contrib import admin

from application.models import *


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'display', 'panel', 'status',
                    'last_update_date_time')  # Поля, отображаемые в списке
    list_filter = ('id', 'display__description', 'status__description', 'panel__name')  # Фильтры для боковой панели
    search_fields = ('display__description', 'panel__name', 'id')  # По каким полям осуществляется поиск
    ordering = ('id', 'status', 'display__description', 'panel__name',
                'status__description')  # Порядок сортировки (убывание по времени выполнения)

    fields = [
        ('display', 'panel', 'status'),
        ('comment_monitoring', 'time_monitoring', 'file_monitoring'),
        ('comment_control_apply', 'time_control_apply', 'file_control_apply'),
        ('comment_control_send', 'time_control_send', 'file_control_send'),
        ('comment_service_apply', 'time_service_apply', 'file_service_apply'),
        ('comment_control_at_work', 'time_control_at_work', 'file_control_at_work'),
        ('comment_control_unable', 'time_control_unable', 'file_control_unable'),
        ('comment_control_archive', 'time_control_archive', 'file_control_archive'),

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
    list_display = ('application_id', 'description', 'comment', 'time', 'user')  # Поля, отображаемые в списке
    list_filter = ('application_id', 'description', 'comment', 'time', 'user')  # Фильтры для боковой панели
    search_fields = ('application_id', 'description', 'comment', 'time', 'user')  # По каким полям осуществляется поиск
    ordering = ('application_id',)  # Порядок сортировки (убывание по времени выполнения)
    list_display_links = ['application_id']  # Ссылка на первое поле
    # Поля, которые можно редактировать прямо в списке
    fields = [
        ('application_id', 'time'),
        ('user', 'comment'),
        'description',
    ]


admin.site.register(ApplicationHistoryReport, ApplicationHistoryReportAdmin)
