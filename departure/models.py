from django.db import models


class Departure(models.Model):
    description = models.TextField(blank=True, null=True, verbose_name='описание')
    user_create = models.CharField(max_length=20, unique=False, verbose_name='создатель')
    time_created = models.DateTimeField(blank=True, null=True, verbose_name='время создания')
    time_start = models.DateTimeField(blank=True, null=True, verbose_name='время начала выезда')
    time_end = models.DateTimeField(blank=True, null=True, verbose_name='время окончания выезда')
    result = models.TextField(blank=True, null=True, verbose_name='результат выезда')
    contractor = models.TextField(blank=True, null=True, verbose_name='исполнитель')
    notification = models.JSONField(blank=True, null=True, verbose_name='уведомления')
    status = models.CharField(blank=True, default='created')

    class Meta:
        db_table = 'departure'
        verbose_name = 'Выезд'
        verbose_name_plural = 'Выезды'
        ordering = ['id']

    def __str__(self):
        return self.description
