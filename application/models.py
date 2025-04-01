from django.db import models


class Application(models.Model):
    display = models.ForeignKey(
        "zip.Display", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='экран', related_name='application'
    )
    panel = models.ForeignKey(
        "zip.Panels", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='панель', related_name='application'
    )
    status = models.ForeignKey(
        "ApplicationStatus", to_field='name',
        on_delete=models.PROTECT, null=False, verbose_name='Статус', related_name='application'
    )

    last_update_date_time = models.DateTimeField(verbose_name='Время последней активности', null=True, blank=True)

    cell = models.ForeignKey(
        "zip.Cell", to_field='id',
        on_delete=models.PROTECT, null=False, verbose_name='ячейка',
    )

    executor = models.ForeignKey(
        "departure.Executor",
        on_delete=models.PROTECT, blank=True, null=True, verbose_name='Исполнитель',
    )

    comment_monitoring = models.TextField(max_length=300, null=True, verbose_name='Коммент отправки заявки мониторинга')
    time_monitoring = models.DateTimeField(verbose_name='Время отправки заявки мониторинга', null=True, blank=True)
    file_monitoring = models.FileField(upload_to=f'application/', blank=True, null=True,
                                       verbose_name='Фото отправки заявки мониторинг')
    user_monitoring = models.CharField(max_length=40, blank=True, null=True, verbose_name='Работник')

    comment_control_apply = models.TextField(max_length=300, null=True, verbose_name='Коммент принятия заявки контроль')
    time_control_apply = models.DateTimeField(verbose_name='Время принятие заявки контроль', null=True, blank=True)
    file_control_apply = models.FileField(upload_to='files/', blank=True, null=True,
                                          verbose_name='Фото контроль принятие заявки')
    user_control_apply = models.CharField(max_length=40, blank=True, null=True, verbose_name='Работник')

    comment_control_send = models.TextField(max_length=300, null=True, verbose_name='Коммент отправки заявки контроль')
    time_control_send = models.DateTimeField(verbose_name='Время отправки заявки контроль', null=True, blank=True)
    file_control_send = models.FileField(upload_to='files/', blank=True, null=True,
                                         verbose_name='Фото контроль отправка заявки')
    user_control_send = models.CharField(max_length=40, blank=True, null=True, verbose_name='Работник')

    comment_service_apply = models.TextField(max_length=300, null=True,
                                             verbose_name='Коммент принятия заявки сервис')
    time_service_apply = models.DateTimeField(verbose_name='Время принятие заявки сервис', null=True, blank=True)
    file_service_apply = models.FileField(upload_to='files/', blank=True, null=True,
                                          verbose_name='Фото сервис принятие заявки')
    user_service_apply = models.CharField(max_length=40, blank=True, null=True, verbose_name='Работник')

    comment_control_at_work = models.TextField(max_length=300, null=True,
                                               verbose_name='Коммент проведенной работы по заявке в сервисе')
    time_control_at_work = models.DateTimeField(verbose_name='Время проведенной работы по заявке в сервисе', null=True,
                                                blank=True)
    file_control_at_work = models.FileField(upload_to='files/', blank=True, null=True,
                                            verbose_name='Фото проведенной работы по заявке в сервисе')
    user_control_at_work = models.CharField(max_length=40, blank=True, null=True, verbose_name='Работник')

    comment_control_unable = models.TextField(max_length=300, null=True,
                                              verbose_name='Коммент проведенной работы по заявке в сервисе')
    time_control_unable = models.DateTimeField(verbose_name='Время проведенной работы по заявке в сервисе', null=True,
                                               blank=True)
    file_control_unable = models.FileField(upload_to='files/', blank=True, null=True,
                                           verbose_name='Фото проведенной работы по заявке в сервисе')
    user_control_unable = models.CharField(max_length=40, blank=True, null=True, verbose_name='Работник')

    comment_control_archive = models.TextField(max_length=300, null=True,
                                               verbose_name='Коммент архивирования заявки в сервисе')
    time_control_archive = models.DateTimeField(verbose_name='Время архивирования заявки в сервисе', null=True,
                                                blank=True)
    file_control_archive = models.FileField(upload_to='files/', blank=True, null=True,
                                            verbose_name='Фото архивирования заявки в сервисе')
    user_control_archive = models.CharField(max_length=40, blank=True, null=True, verbose_name='Работник')

    class Meta:
        db_table = 'application'
        verbose_name = 'Заявки'
        verbose_name_plural = 'Заявка'
        ordering = ['id']


class ApplicationStatus(models.Model):
    name = models.TextField(max_length=40, unique=True, verbose_name='название"')
    description = models.TextField(blank=True, null=True, verbose_name='описание')
    color = models.ForeignKey(
        "main.Color", to_field='name',
        on_delete=models.PROTECT, verbose_name='цвет', related_name='application_status_color'
    )
    color_text = models.ForeignKey(
        "main.Color", to_field='name',
        on_delete=models.PROTECT, verbose_name='цвет текста', related_name='application_status_color_text'
    )
    icon = models.ForeignKey(
        "main.Smile", to_field='smile_icon',
        on_delete=models.PROTECT, null=True, verbose_name='иконка',
    )

    class Meta:
        db_table = 'application_status'
        verbose_name = 'Статус заявки'
        verbose_name_plural = 'Статусы заявок'
        ordering = ['id']

    def __str__(self):
        return self.name


class ApplicationHistoryReport(models.Model):
    application_id = models.CharField(max_length=5, unique=False, null=True, verbose_name='Айди заявки')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    comment = models.TextField(verbose_name='коммент')
    time = models.DateTimeField(null=False, blank=False, verbose_name='Время')
    user = models.CharField(max_length=40, unique=False, verbose_name='Пользователь')

    class Meta:
        db_table = 'history_application'
        verbose_name = 'История репортов заявок'
        verbose_name_plural = 'Истории репортов заявок'
        ordering = ['id']

    def __str__(self):
        return self.description
