from django.apps import AppConfig


class ApplicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'application'
    verbose_name = 'Заявки'

    def ready(self):
        import application.signals  # Подключаем файл signals.py
