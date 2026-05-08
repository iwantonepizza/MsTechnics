from django.apps import AppConfig


class DailyTasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workflow.daily_tasks"
    label = "workflow_daily_tasks"
    verbose_name = "Ежедневные задания"
