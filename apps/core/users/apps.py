from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core.users"
    label = "user"
    verbose_name = "Пользователи"
