from django.db import models


class DisplayHistoryReport(models.Model):
    TYPE_EVENT = [
        ('moving', 'Передвижение'),
        ('breakdown', 'Поломка'),
        ('status', 'Статус'),
        ('service', 'Ремонт'),
        ('none_type', 'Общий'),

    ]
    display = models.ForeignKey(
        "zip.Display",
        on_delete=models.PROTECT,
        related_name="display_history",
        verbose_name="экран", to_field='name', editable=False
    )
    slot = models.ForeignKey(
        "zip.Cell",
        on_delete=models.PROTECT, verbose_name='слот')
    description = models.TextField(blank=True, null=True, verbose_name='описание')
    comment = models.TextField(blank=True, null=True, verbose_name='коммент')
    type_event = models.CharField(
        max_length=20,
        choices=TYPE_EVENT,
        default='none_type',
    )
    time = models.DateTimeField()
    user = models.CharField(max_length=20, blank=True, null=True, unique=False, verbose_name='пользователь')

    class Meta:
        db_table = 'history_report'
        verbose_name = 'История репортов экрана'
        verbose_name_plural = 'Истории репортов экранов'
        ordering = ['id']

    def __str__(self):
        return self.description


class PanelHistoryReport(models.Model):
    TYPE_REPORT = [
        ('moving', 'Передвижение'),
        ('breakdown', 'Поломка'),
        ('condition', 'Состояние'),
        ('service', 'Ремонт'),
        ('none_type', 'Общий'),

    ]

    panel = models.ForeignKey(
        "zip.Panels", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='панель', related_name="history",
    )
    description = models.TextField(blank=True, null=True, verbose_name='описание')
    comment = models.TextField(blank=True, null=True, verbose_name='коммент')
    type_report = models.CharField(
        max_length=20,
        choices=TYPE_REPORT,
        default='none_type',
    )
    time = models.DateTimeField()
    user = models.CharField(max_length=20, blank=True, null=True, verbose_name='пользователь')

    class Meta:
        db_table = 'history_panel'
        verbose_name = 'История репортов панелей'
        verbose_name_plural = 'Истории репортов панелей'
        ordering = ['id']

    def __str__(self):
        return self.description


class DailyTaskHistoryReport(models.Model):
    task = models.ForeignKey(
        "zip.DailyTask", to_field='name', related_name='task_reports',
        on_delete=models.CASCADE, verbose_name='задание')
    user = models.CharField(max_length=20, unique=False, verbose_name='пользователь')
    result = models.CharField(max_length=20, unique=False, verbose_name='результат')
    time = models.DateTimeField()

    class Meta:
        db_table = 'history_daily'
        verbose_name = 'История репортов задания'
        verbose_name_plural = 'Истории репортов заданий'
        ordering = ['id']

    def __str__(self):
        return self.task.name
