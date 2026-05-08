from django.apps import AppConfig


class GmailAlarmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations.gmail_alarms"
    label = "gmail_alarms"
    verbose_name = "VNNOX email alarms"
