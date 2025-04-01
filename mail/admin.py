from django.contrib import admin

from mail.models import GmailMessage, Alarm


class AlarmTabular(admin.TabularInline):
    model = Alarm
    fields = ('slot_number', 'status', 'description', 'display','alarm_time')
    readonly_fields = ('slot_number', 'status', 'description', 'display','alarm_time')
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(GmailMessage)
class GmailAdmin(admin.ModelAdmin):
    list_display = ('message_id', 'received_at', 'added_at')
    list_filter = ('received_at', 'added_at')
    search_fields = ('message_id',)
    ordering = ('-received_at',)  # Порядок сортировки (убывание по времени выполнения)
    fieldsets = (
        ('Основная информация', {
            'fields': ('message_id', 'received_at')
        }),
        ('Детали', {
            'fields': ('full_text',)
        }),
    )

    # Поля только для чтения
    readonly_fields = ('message_id', 'received_at')
    inlines = [AlarmTabular, ]
    actions = ['mark_as_processed']

    def mark_as_processed(self, request, queryset):
        queryset.update(status='Processed')
        self.message_user(request, "Выбранные письма помечены как обработанные.")

    mark_as_processed.short_description = "Пометить как обработанные"


@admin.register(Alarm)
class AlarmAdmin(admin.ModelAdmin):
    list_display = ('message', 'slot_number', 'status', 'description', 'alarm_time', 'display')  # Исправлены поля
    list_filter = ('status', 'display')
    search_fields = ('description', 'slot_number')
    ordering = ('-alarm_time',)
    readonly_fields = ('message', 'slot_number', 'status', 'description', 'alarm_time', 'display')
