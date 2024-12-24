from django.db import models

from django.contrib.auth.models import AbstractUser


class MsUser(AbstractUser):
    TYPE_PERMISSION = [
        ('monitoring', 'Мониторинг'),
        ('control', 'Контроль'),
        ('service', 'Сервис'),
        ('all', 'Все'),
        ('admin', 'Админ'),
        ('technical', 'Техник'),
        ('none_type', 'Никакие'),

    ]
    permission = models.CharField(
        max_length=20,
        choices=TYPE_PERMISSION,
        default='none_type',
        verbose_name='Уровень доступа')
    telegram_id = models.CharField(max_length=10, blank=True, null=True,
                                   verbose_name='Айди телеграм')

    class Meta:
        db_table = 'user'
        verbose_name = 'Пользователя'
        verbose_name_plural = 'Пользователи'
        abstract = False

    def __str__(self):
        return self.username


class ConcreteMsUser(MsUser):
    pass
