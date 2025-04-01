from django.contrib import admin

from departure.models import *


class DepartureAdmin(admin.ModelAdmin):
    list_display = ('description', 'user_create', 'time_created', 'time_start', 'time_end', 'result',
                    'executor', 'notification')  # Поля, отображаемые в списке
    list_filter = ('user_create', 'executor', 'time_start')  # Фильтры для боковой панели
    search_fields = ('user_create', 'executor', 'time_start')  # По каким полям осуществляется поиск
    ordering = ('-time_start',)  # Порядок сортировки (убывание по времени выполнения)
    list_editable = (
        'result', 'notification', 'executor')  # Поля, которые можно редактировать прямо в списке
    fields = [
        'description',
        'user_create',
        ('time_created', 'time_start', 'time_end'),
        'result',
        'executor',
        'notification',
    ]


admin.site.register(Departure, DepartureAdmin)


@admin.register(DepartureHistoryReport)
class DepartureHistoryReportAdmin(admin.ModelAdmin):
    pass


@admin.register(Executor)
class ExecutorAdmin(admin.ModelAdmin):
    pass


@admin.register(Contact)
class ContactlistAdmin(admin.ModelAdmin):
    pass
