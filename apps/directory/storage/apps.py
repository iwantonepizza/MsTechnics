from django.apps import AppConfig


class StorageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.directory.storage"
    label = "directory_storage"
    verbose_name = "ЗИП-расходники"
