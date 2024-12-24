from django.db import models
from datetime import datetime, timedelta

from core_mechanic.telegram_connect import send_tg_notification
from user.models import ConcreteMsUser

from django.db.models import UniqueConstraint
from django.core.exceptions import ValidationError


class Display(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='экран')
    city = models.ForeignKey(
        "main.Cities", to_field='name',
        on_delete=models.PROTECT, verbose_name='город')
    description = models.TextField(blank=True, null=True, verbose_name='описание')
    rows = models.PositiveIntegerField(verbose_name='кол-во рядов', default=0)
    cols = models.PositiveIntegerField(verbose_name='кол-во столбцов', default=0)
    condition = models.ForeignKey(
        "main.Condition", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='состояние',
    )
    slug = models.SlugField(unique=True, blank=True, null=True, verbose_name='URL', editable=False)
    camera_link = models.URLField(max_length=150, null=True, verbose_name='ссылка"')
    file = models.FileField(upload_to='files/', blank=True, null=True, default='probka.jpg',
                            verbose_name='Файл (PDF или JPEG)')

    class Meta:
        db_table = 'display'
        verbose_name = 'Экран'
        verbose_name_plural = 'Экраны'
        ordering = ['id']

    def __str__(self):
        return self.name

    @property
    def cells(self):
        return self.cell_set.all()


class Cell(models.Model):
    display = models.ForeignKey(
        "Display",
        on_delete=models.PROTECT,
        related_name="cell_set",
        verbose_name="экран", to_field='name', editable=False
    )
    row = models.PositiveIntegerField(verbose_name='ряд', editable=False)
    col = models.PositiveIntegerField(verbose_name='столбец', editable=False)
    panel = models.ForeignKey(
        "Panels",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cells",
        verbose_name="панель", to_field='name'
    )

    class Meta:
        db_table = 'cell'
        constraints = [
            UniqueConstraint(fields=['panel'], name='unique_panel'),
            UniqueConstraint(fields=['display', 'row', 'col'], name='unique_display_row_col')
        ]
        verbose_name = 'Ячейка'
        verbose_name_plural = 'Ячейки'
        ordering = ['display', 'row', 'col']

    def __str__(self):
        return f"Ячейка {self.position()} на {self.display.name}"

    def position(self):
        """
        Метод возвращает порядковый номер панели, начиная с 01.
        Нумерация происходит по рядам (слева направо, сверху вниз).
        """
        if not self.display:
            return None  # Если панель не привязана к экрану

        # Всего столбцов на экране
        cols_count = self.display.cols

        position_number = (self.row - 1) * cols_count + self.col

        return str(position_number).zfill(2)


class Panels(models.Model):
    name = models.CharField(max_length=15, unique=True, verbose_name='айдишник')
    display = models.ForeignKey(
        "Display", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='установлен на',
    )
    comment = models.TextField(blank=True, null=True, verbose_name='описание')
    condition = models.ForeignKey(
        "main.Condition", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='состояние', default='work'
    )
    department = models.ForeignKey(
        "main.Department", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='нахождение',
    )
    application_status = models.ForeignKey(
        "application.ApplicationStatus", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='статус заявки', default='default'
    )

    class Meta:
        db_table = 'panel'
        verbose_name = 'Панель'
        verbose_name_plural = 'Панели'
        ordering = ['id']

    def __str__(self):
        return self.name


class DailyTask(models.Model):
    TYPE_STATUS = [
        ('not_ready', 'Не готово'),
        ('ready', 'Доступно'),
        ('deadline', 'Дедлайн'),
        ('done', 'Выполнено'),
        ('undone', 'Не выполнено'),

    ]

    name = models.CharField(max_length=20, unique=True, verbose_name='название"')
    description = models.TextField(blank=True, verbose_name='описание')
    city = models.ForeignKey(
        "main.Cities", to_field='name',
        on_delete=models.PROTECT, verbose_name='город')
    status = models.CharField(
        max_length=20,
        choices=TYPE_STATUS,
        default='undone',
        verbose_name='Статус',
        db_column='Статус')
    start_time = models.TimeField(blank=True, null=True, verbose_name='начало')
    end_time = models.TimeField(blank=True, null=True, verbose_name='конец')
    link = models.URLField(max_length=150, blank=False, verbose_name='ссылка')
    last_completed_date = models.DateField(null=True, blank=True, verbose_name='уведомление выполнение')
    alert_notification_sent = models.BooleanField(default=False, verbose_name='уведомление скорое начало')
    deadline_notification_sent = models.BooleanField(default=False, verbose_name='уведомление дедлайн')
    lost_notification_sent = models.BooleanField(default=False, verbose_name='уведомление пропуск')
    start_notification_sent = models.BooleanField(default=False, verbose_name='уведомление начало')
    completed_notification_sent = models.BooleanField(default=False, verbose_name='уведомление выполнение')

    def complete_task(self, current_datetime):
        if self.status not in ('undone', 'done'):  # подумать на проверкой получше, чтобы изежать повторное выполнение
            self.status = 'done'
            self.last_completed_date = current_datetime
            self.completed_notification_sent = True
            self.save()
            return True
        else:
            return False

    def reset_task(self):
        self.alert_notification_sent = self.deadline_notification_sent = self.lost_notification_sent = self.start_notification_sent = self.completed_notification_sent = False
        self.status = 'not_ready'
        self.save()
        return send_tg_notification(text=f'Задание {self.name} обновлено',
                                    type_msg='server_checker'
                                    ) == 200

    def check_status(self, current_datetime: datetime) -> dict:
        # присылает уведомление, если осталось менее 5 минут до начала
        if self.alert_notification_sent is False and self.status == 'not_ready' and (
                datetime.combine(current_datetime.date(), self.start_time) - datetime.combine(current_datetime.date(),
                                                                                              current_datetime.time())) <= timedelta(
            minutes=5):
            self.alert_notification_sent = True
            return send_tg_notification(text=f'👁 {self.name} откроется через 5 минут 👁',
                                        type_msg='daily'
                                        )
        # проверка на просрок
        elif self.status != 'done' and self.lost_notification_sent is False and current_datetime.time() > self.end_time:
            self.status = 'undone'
            self.lost_notification_sent = True
            self.save()
            return send_tg_notification(text=f'❌ {self.name} просрочен ❌',
                                        type_msg='daily'
                                        )

        # проверка на дедлайн
        elif self.deadline_notification_sent is False and (
                datetime.combine(current_datetime.date(), self.end_time) - datetime.combine(current_datetime.date(),
                                                                                            current_datetime.time())) < timedelta(
            hours=1):
            self.status = 'deadline'
            self.deadline_notification_sent = True
            self.save()
            return send_tg_notification(text=f'🔥 {self.name} остался час на выполнение 🔥',
                                        type_msg='daily'
                                        )
        elif current_datetime.time() > self.start_time and self.start_notification_sent is False:
            self.start_notification_sent = True
            self.status = 'ready'
            self.save()
            return send_tg_notification(text=f'{self.name} доступен!',
                                        type_msg='daily'
                                        )

    def check_available_status(self):
        return self.status in ('ready', 'deadline')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def check_iteration(self, current_datetime: datetime) -> dict:
        if self.last_completed_date != current_datetime.date():
            message_delivered = self.check_status(current_datetime)
            self.save()
            return message_delivered

    class Meta:
        db_table = 'daily_task'
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'

    def __str__(self):
        return str(self.name or "Без названия")





def validate_positive(value):
    if value < 0:
        raise ValidationError('Количество не может быть меньше нуля.')


class Wires(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='Имя')
    description = models.CharField(max_length=100, blank=True, null=True, verbose_name='Описание')
    count = models.PositiveIntegerField(default=0, verbose_name='Количество', validators=[validate_positive])
    photo = models.ImageField(upload_to='photos/', blank=True, null=True, verbose_name='Фото')

    class Meta:
        db_table = 'wires_zip'
        verbose_name = 'Провод'
        verbose_name_plural = 'Провода'
        ordering = ['id']

    def __str__(self):
        return self.name

    def increase_count(self, value: int = 1):
        if value < 0:
            raise ValueError('Значение для увеличения должно быть положительным')
        self.count += value
        self.save()

    # Метод уменьшения количества
    def decrease_count(self, value: int = 1):
        if value < 0:
            raise ValueError('Значение для уменьшения должно быть положительным')
        if self.count - value < 0:
            raise ValidationError('Количество не может быть меньше нуля.')
        self.count -= value
        self.save()


class Hubs(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='Имя')
    description = models.CharField(max_length=100, blank=True, null=True, verbose_name='Описание')
    count = models.PositiveIntegerField(default=0, verbose_name='Количество', validators=[validate_positive])
    photo = models.ImageField(upload_to='photos/', blank=True, null=True, verbose_name='Фото')

    class Meta:
        db_table = 'hubs_zip'
        verbose_name = 'Хаб'
        verbose_name_plural = 'Хабы'
        ordering = ['id']

    def __str__(self):
        return self.name

    def increase_count(self, value: int = 1):
        if value < 0:
            raise ValueError('Значение для увеличения должно быть положительным')
        self.count += value
        self.save()

    # Метод уменьшения количества
    def decrease_count(self, value: int = 1):
        if value < 0:
            raise ValueError('Значение для уменьшения должно быть положительным')
        if self.count - value < 0:
            raise ValidationError('Количество не может быть меньше нуля.')
        self.count -= value
        self.save()


class Lamels(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='Имя')
    description = models.CharField(max_length=100, blank=True, null=True, verbose_name='Описание')
    count = models.PositiveIntegerField(default=0, verbose_name='Количество', validators=[validate_positive])
    photo = models.ImageField(upload_to='photos/', blank=True, null=True, verbose_name='Фото')

    class Meta:
        db_table = 'lamels_storage'
        verbose_name = 'Ламель'
        verbose_name_plural = 'Ламели'
        ordering = ['id']

    def __str__(self):
        return self.name

    def increase_count(self, value: int = 1):
        if value < 0:
            raise ValueError('Значение для увеличения должно быть положительным')
        self.count += value
        self.save()

    # Метод уменьшения количества
    def decrease_count(self, value: int = 1):
        if value < 0:
            raise ValueError('Значение для уменьшения должно быть положительным')
        if self.count - value < 0:
            raise ValidationError('Количество не может быть меньше нуля.')
        self.count -= value
        self.save()


class Contactlist(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='имя')
    description = models.TextField(blank=True, null=True, verbose_name='описание')
    display = models.ForeignKey(
        "Display", to_field='name',
        on_delete=models.PROTECT, verbose_name='экран', related_name='display'
    )

    class Meta:
        db_table = 'contactlist'
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'
        ordering = ['id']

    def __str__(self):
        return self.name
