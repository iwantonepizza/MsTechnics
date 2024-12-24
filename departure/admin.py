from django.contrib import admin

from departure.models import Departure


class DepartureAdmin(admin.ModelAdmin):
    list_display = ('description', 'user_create', 'time_created', 'time_start', 'time_end', 'result',
                    'contractor', 'notification')  # Поля, отображаемые в списке
    list_filter = ('user_create', 'contractor', 'time_start')  # Фильтры для боковой панели
    search_fields = ('user_create', 'contractor', 'time_start')  # По каким полям осуществляется поиск
    ordering = ('-time_start',)  # Порядок сортировки (убывание по времени выполнения)
    list_editable = (
         'result', 'notification', 'contractor')  # Поля, которые можно редактировать прямо в списке
    fields = [
        'description',
        'user_create',
        ('time_created', 'time_start', 'time_end'),
        'result',
        'contractor',
        'notification',
    ]


admin.site.register(Departure, DepartureAdmin)
