from django.db import models
from datetime import datetime, timedelta
from django.db import transaction
from django.apps import apps
from get_time import get_time_setting_tz

from main.models import Condition
from sorting_message import presend_filters
from user.models import ConcreteMsUser

from django.db.models import UniqueConstraint
from django.core.exceptions import ValidationError

from main_menu.models import PanelHistoryReport, DisplayHistoryReport

class ExampleQueryset(models.QuerySet):
    def test_fuction(self):
        return [obj.slug for obj in self]


class Display(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='экран')
    city = models.ForeignKey(
        "main.Cities", to_field='name',
        on_delete=models.PROTECT, verbose_name='город', related_name='display')
    description = models.TextField(blank=True, null=True, verbose_name='описание')
    rows = models.PositiveIntegerField(verbose_name='кол-во рядов', default=0)
    cols = models.PositiveIntegerField(verbose_name='кол-во столбцов', default=0)
    camera_link = models.URLField(max_length=150, null=True, verbose_name='ссылка на камеру')
    file = models.FileField(upload_to='files/', blank=True, null=True, default='file_not_found.jpg',
                            verbose_name='Электросхема')
    project_photo = models.FileField(upload_to='files/', blank=True, null=True, default='file_not_found.jpg',
                                     verbose_name='Проект')
    slug = models.SlugField(unique=True, blank=True, null=True, verbose_name='URL')
    objects = ExampleQueryset().as_manager()

    class Meta:
        db_table = 'display'
        verbose_name = 'Экран'
        verbose_name_plural = 'Экраны'
        ordering = ['id']

    def __str__(self):
        return self.name

    @property
    def cells(self):
        """
        Вызов всех слотов дисплея
        """
        return self.cell_set.all()

    @property
    def current_condition(self):
        """
        Ленивый поиск текущего состояния по худшему состоянию панелей во всех ячейках >id == хуже состояние
        """
        worst_condition_id = self.cell_set.aggregate(
            worst_condition=models.Max('panel__condition__id')
        )['worst_condition']

        if worst_condition_id:
            Condition = apps.get_model('main', 'Condition')
            return Condition.objects.filter(id=worst_condition_id).first()

        return None

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        extra_panels = getattr(self, "_extra_panels", 10)

        with transaction.atomic():
            super().save(*args, **kwargs)

            if is_new:
                # 1. Создаем ячейки
                cells = [
                    Cell(display=self, row=row, col=col)
                    for row in range(1, self.rows + 1)
                    for col in range(1, self.cols + 1)
                ]
                Cell.objects.bulk_create(cells)

                # 2. Создаем панели
                PanelModel = Panels
                total = len(cells) + extra_panels  # гарантируем достаточно панелей

                panels = [
                    PanelModel(
                        name=f"{self.name}-{i + 1}",
                        display=self,
                        comment="Создан автоматически с экраном",
                    )
                    for i in range(total)
                ]
                PanelModel.objects.bulk_create(panels)

                # 3. Назначаем панель каждой ячейке
                # Повторно получаем объекты, т.к. bulk_create не возвращает PK
                created_cells = list(Cell.objects.filter(display=self).order_by("id"))
                created_panels = list(PanelModel.objects.filter(display=self).order_by("id"))

                for cell, panel in zip(created_cells, created_panels):
                    cell.panel = panel
                    current_time = get_time_setting_tz()

                    PanelHistoryReport.objects.create(panel=cell.panel,
                                                      description=f'⬇️ {cell.panel.display.description} {cell.position}',
                                                      type_report='moving', time=current_time,
                                                      comment='Установлена автоматически при создании экрана')
                    DisplayHistoryReport.objects.create(display=cell.panel.display, slot=cell,
                                                        description=f'⬇️ {cell.panel}',
                                                        type_event='moving', time=current_time,
                                                        comment='Установлена автоматически при создании экрана')
                    cell.save()

                Cell.objects.bulk_update(created_cells, ["panel"])


class Cell(models.Model):
    display = models.ForeignKey(
        "Display",
        on_delete=models.CASCADE,
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
        related_name="cell",
        verbose_name="панель", to_field='name'
    )

    def __str__(self):
        return f"Ячейка {self.position} на {self.display.name}"

    @property
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

    class Meta:
        db_table = 'cell'
        constraints = [
            UniqueConstraint(fields=['panel'], name='unique_panel'),
            UniqueConstraint(fields=['display', 'row', 'col'], name='unique_display_row_col')
        ]
        verbose_name = 'Ячейка'
        verbose_name_plural = 'Ячейки'
        ordering = ['display', 'row', 'col']


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
        on_delete=models.PROTECT, null=True, verbose_name='нахождение', default='zip'
    )
    application_status = models.ForeignKey(
        "application.ApplicationStatus", to_field='name',
        on_delete=models.PROTECT, null=True, verbose_name='статус заявки', default='default'
    )

    def get_full_title(self):
        dislpay = self.display.name if self.display else None
        comment = self.comment if self.comment else "Не передан"
        condition = self.condition.description
        department = self.department.description
        application_status = self.application_status.description if self.application_status and self.application_status != "default" else None
        result = ""
        result += f"ID - {self.name}\n"
        if dislpay:
            result += f"Экран - {dislpay}\n"
        result += f"Комментарий - {comment}\n"
        result += f"Состояние - {condition}\n"
        if application_status:
            result += f"Заявка - {application_status}\n"
        result += f"Нахождение - {department}\n"
        return result

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
        on_delete=models.PROTECT, verbose_name='Город')
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
        presend_filters(text=f'🔄 Задание {self.name} обновлено', type_msg='server_checker')

    def check_status(self, current_datetime: datetime) -> None:
        # присылает уведомление, если осталось менее 5 минут до начала
        if self.alert_notification_sent is False and self.status == 'not_ready' and (
                datetime.combine(current_datetime.date(), self.start_time) - datetime.combine(current_datetime.date(),
                                                                                              current_datetime.time())) <= timedelta(
            minutes=5):
            self.alert_notification_sent = True
            presend_filters(text=f'👁 {self.name} откроется через 5 минут 👁',
                            type_msg='daily'
                            )
        # проверка на просрок
        elif self.status != 'done' and self.lost_notification_sent is False and current_datetime.time() > self.end_time:
            self.status = 'undone'
            self.lost_notification_sent = True
            self.save()
            presend_filters(text=f'❌ {self.name} просрочен ❌',
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
            presend_filters(text=f'🔥 {self.name} остался час на выполнение 🔥',
                            type_msg='daily'
                            )
        elif current_datetime.time() > self.start_time and self.start_notification_sent is False:
            self.start_notification_sent = True
            self.status = 'ready'
            self.save()
            presend_filters(text=f'{self.name} доступен!',
                            type_msg='daily'
                            )

    def check_available_status(self):
        return self.status in ('ready', 'deadline')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def check_iteration(self, current_datetime: datetime) -> None:
        if self.last_completed_date != current_datetime.date():
            message_delivered = self.check_status(current_datetime)
            self.save()

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


class PhotoDisplay(models.Model):
    display = models.ForeignKey(
        Display,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="Экран"
    )
    image = models.ImageField(upload_to="photos/display_photos/", verbose_name="Фото")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")
    class Meta:
        db_table = 'photo_display'
        verbose_name = 'Фото экрана'
        verbose_name_plural = 'Фото экрана'
        ordering = ['id']
    def __str__(self):
        return f"Фото {self.display.name}"
