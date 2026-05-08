from django.apps import AppConfig


class DeparturesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workflow.departures"
    label = "workflow_departures"
    verbose_name = "Выезды"
