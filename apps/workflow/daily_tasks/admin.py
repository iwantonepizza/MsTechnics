"""T-8-072: admin для ежедневных задач."""
from django.contrib import admin

from apps.workflow.daily_tasks.models import DailyTask


@admin.register(DailyTask)
class DailyTaskAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "status", "start_time", "end_time", "link")
    list_filter = ("status", "city")
    search_fields = ("name", "description")
    ordering = ("city", "start_time")
