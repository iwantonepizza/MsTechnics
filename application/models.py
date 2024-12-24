from django.db import models


class Application(models.Model):
    display = models.ForeignKey(
        "zip.Display", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='экран',
    )
    panel = models.ForeignKey(
        "zip.Panels", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='панель',
    )
    status = models.ForeignKey(
        "ApplicationStatus", to_field='name',
        on_delete=models.PROTECT, null=False, verbose_name='Статус',
    )
    comment_monitoring = models.TextField(max_length=300, null=True, verbose_name='Коммент мониторинга')
    time_monitoring = models.DateTimeField(verbose_name='Время мониторинга', null=True, blank=True)
    # file_monitoring = models.FileField(upload_to='files/', blank=True, null=True, default='probka.jpg',
    #                         verbose_name='Фото мониторинга')


    comment_control = models.TextField(max_length=300, null=True, verbose_name='Коммент контроля')
    time_control = models.DateTimeField(verbose_name='Время мониторинга', null=True, blank=True)
    # file_control_apply = models.FileField(upload_to='files/', blank=True, null=True, default='probka.jpg',
    #                         verbose_name='Фото мониторинга')
    #


    comment_service = models.TextField(max_length=300, null=True, verbose_name='Комменты мониторинга')
    time_service = models.DateTimeField(verbose_name='Время мониторинга', null=True, blank=True)

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
    display = models.ForeignKey(
        "zip.Display", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='дисплей',
    )
    panel = models.ForeignKey(
        "zip.Panels", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='панель',
    )
    description = models.TextField(blank=True, null=True, verbose_name='описание')
    comment = models.TextField(verbose_name='коммент')
    time = models.DateTimeField(null=False, blank=False, verbose_name='время')
    user = models.CharField(max_length=20, unique=False, verbose_name='пользователь')

    class Meta:
        db_table = 'history_application'
        verbose_name = 'История репортов заявок'
        verbose_name_plural = 'Истории репортов заявок'
        ordering = ['id']

    def __str__(self):
        return self.description
