from django.db import models
from zip.models import Display


class Departure(models.Model):
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    user_create = models.CharField(max_length=20, unique=False, verbose_name='Создатель')
    time_updated = models.DateTimeField(blank=True, null=True, verbose_name='Время последнего взаимодействия')
    time_created = models.DateTimeField(blank=True, null=True, verbose_name='Время создания')
    time_start = models.DateTimeField(blank=True, null=True, verbose_name='Время начала выезда')
    time_end = models.DateTimeField(blank=True, null=True, verbose_name='Время окончания выезда')
    result = models.TextField(blank=True, null=True, verbose_name='Результат выезда')
    executor = models.ForeignKey(
        "departure.Executor",
        on_delete=models.PROTECT, blank=True, null=True, verbose_name='Исполнитель',
    )
    notification = models.JSONField(blank=True, null=True, verbose_name='Уведомления')
    status = models.CharField(blank=True, default='Создан')

    class Meta:
        db_table = 'departure'
        verbose_name = 'Выезд'
        verbose_name_plural = 'Выезды'
        ordering = ['id']

    def __str__(self):
        return self.description


class DepartureHistoryReport(models.Model):
    departure = models.ForeignKey(
        "departure.Departure",
        on_delete=models.SET_NULL, null=True, verbose_name='Выезд',
    )
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    comment = models.TextField(verbose_name='Коммент')
    time = models.DateTimeField(null=False, blank=False, verbose_name='Время')
    user = models.ForeignKey(
        "user.MsUser",
        on_delete=models.PROTECT, null=True, verbose_name='Работник',
    )

    class Meta:
        db_table = 'departure_history_report'
        verbose_name = 'История репортов выездов'
        verbose_name_plural = 'Истории репортов выездов'
        ordering = ['id']

    def __str__(self):
        return f'{self.description}'

class Executor(models.Model):
    first_name = models.CharField(max_length=150, blank=True,
                                  verbose_name='Имя')
    last_name = models.CharField(max_length=150, blank=True,
                                 verbose_name='Фамилия')
    executor_role = models.CharField(
        max_length=20,
        default='должности нет',
        verbose_name='Должность')
    phone_number = models.CharField(max_length=15, blank=True, null=True,
                                    verbose_name='Номер телефона')
    telegram_id = models.CharField(max_length=15, blank=True, null=True,
                                   verbose_name='Айди телеграм')

    class Meta:
        db_table = 'executor'
        verbose_name = 'Исполнитель'
        verbose_name_plural = 'Исполнители'
        ordering = ['id']

    def __str__(self):
        return f'{self.first_name} {self.last_name} {self.phone_number}'


class Contact(models.Model):
    first_name = models.CharField(max_length=150, blank=True,
                                  verbose_name='Имя')
    last_name = models.CharField(max_length=150, blank=True,
                                 verbose_name='Фамилия')
    description = models.CharField(max_length=150, blank=True,
                                   verbose_name='Описание')
    displays = models.ManyToManyField(
        Display,
        related_name="contacts",
        verbose_name="Список экранов"
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True,
                                    verbose_name='Номер телефона')
    telegram_id = models.CharField(max_length=15, blank=True, null=True,
                                   verbose_name='Айди телеграм')

    class Meta:
        db_table = 'contact'
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'
        ordering = ['id']

    def __str__(self):
        return f'{self.first_name} {self.last_name} {self.phone_number}'
