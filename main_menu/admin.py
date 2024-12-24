from django.contrib import admin

from main_menu.models import *


class DisplayHistoryReportAdmin(admin.ModelAdmin):
    list_display = ('slot', 'description', 'comment', 'type_event', 'time',
                    'user')
    list_filter = ('display', 'type_event', 'time', 'user')
    search_fields = ('slot', 'type_event', 'time', 'user')
    ordering = ('type_event', 'time')
    fields = [
        ('slot', 'type_event', 'user'),
        'description',
        'comment',
        'time',
    ]


admin.site.register(DisplayHistoryReport, DisplayHistoryReportAdmin)


class PanelHistoryReportAdmin(admin.ModelAdmin):
    list_display = ('panel', 'description', 'comment', 'time', 'user')
    list_filter = ('time', 'user')
    search_fields = ('panel', 'time', 'user')
    ordering = ('time',)
    fields = [
        ('panel', 'user'),
        'description',
        'comment',
        'time',
    ]


admin.site.register(PanelHistoryReport, PanelHistoryReportAdmin)


class DailyTaskHistoryReportAdmin(admin.ModelAdmin):
    list_display = ('task', 'time', 'result', 'user')
    list_filter = ('task', 'user', 'result', 'time')
    search_fields = ('task', 'user', 'result', 'time')
    ordering = ('time', 'user')
    fields = [
        ('task', 'result'),
        ('user', 'time'),
    ]


admin.site.register(DailyTaskHistoryReport, DailyTaskHistoryReportAdmin)
