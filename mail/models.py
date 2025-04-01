from django.db import models


class GmailMessage(models.Model):
    message_id = models.CharField(max_length=100, unique=True, verbose_name='Айди сообщения')
    received_at = models.DateTimeField(verbose_name='Обработано в', blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено в')
    full_text = models.TextField(blank=True, null=True, verbose_name='Полный текст сообщения')

    def __str__(self):
        return f"Сообщение с id {self.message_id}"

    class Meta:
        verbose_name = 'письмо'
        verbose_name_plural = 'Письма'
        ordering = ['-id']


class Alarm(models.Model):
    message = models.ForeignKey(GmailMessage, on_delete=models.CASCADE, related_name='alarms',
                                verbose_name='Связанное сообщение')
    display = models.ForeignKey(
        "zip.Display", to_field='name', on_delete=models.PROTECT, verbose_name='Экран', related_name='alarms',
        blank=True, null=True)
    alarm_time = models.CharField(max_length=50, verbose_name='Время сигнала')  # Время из таблицы
    slot_number = models.CharField(max_length=10, blank=True, null=True, verbose_name='Слот')
    description = models.CharField(max_length=200, blank=True, null=True, verbose_name='Описание')
    status = models.CharField(max_length=50, blank=True, null=True, verbose_name='Статус')

    class Meta:
        verbose_name = 'сигнал'
        verbose_name_plural = 'Сигналы'
        ordering = ['-alarm_time']

    def __str__(self):
        return f"Сигнал  слот : {self.slot_number or 'Нет слота'}"
