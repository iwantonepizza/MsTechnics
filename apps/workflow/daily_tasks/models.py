"""Daily tasks moved out of `zip` while keeping the original `daily_task` table."""

from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from django.db import models

from sorting_message import presend_filters


class DailyTask(models.Model):
    _NOTIFICATION_FLAGS = {
        "alert": "alert_notification_sent",
        "deadline": "deadline_notification_sent",
        "lost": "lost_notification_sent",
        "start": "start_notification_sent",
        "completed": "completed_notification_sent",
    }

    TYPE_STATUS = [
        ("not_ready", "Не готово"),
        ("ready", "Доступно"),
        ("deadline", "Дедлайн"),
        ("done", "Выполнено"),
        ("undone", "Не выполнено"),
    ]

    name = models.CharField(max_length=20, unique=True, verbose_name='название"')
    description = models.TextField(blank=True, verbose_name="описание")
    city = models.ForeignKey(
        "core_references.Cities",
        on_delete=models.PROTECT,
        verbose_name="Город",
    )
    status = models.CharField(
        max_length=20,
        choices=TYPE_STATUS,
        default="undone",
        verbose_name="Статус",
        db_column="Статус",
    )
    start_time = models.TimeField(blank=True, null=True, verbose_name="начало")
    end_time = models.TimeField(blank=True, null=True, verbose_name="конец")
    link = models.URLField(max_length=150, verbose_name="ссылка")
    last_completed_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="уведомление выполнение",
    )
    notified_stages = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Отправленные уведомления",
    )
    alert_notification_sent = models.BooleanField(default=False, verbose_name="уведомление скорое начало")
    deadline_notification_sent = models.BooleanField(default=False, verbose_name="уведомление дедлайн")
    lost_notification_sent = models.BooleanField(default=False, verbose_name="уведомление пропуск")
    start_notification_sent = models.BooleanField(default=False, verbose_name="уведомление начало")
    completed_notification_sent = models.BooleanField(default=False, verbose_name="уведомление выполнение")

    class Meta:
        app_label = "workflow_daily_tasks"
        db_table = "daily_task"
        verbose_name = "Задание"
        verbose_name_plural = "Задания"

    def __str__(self) -> str:
        return str(self.name or "Без названия")

    def has_notified(self, stage: str) -> bool:
        stages = self.notified_stages or []
        if stage in stages:
            return True
        flag_name = self._NOTIFICATION_FLAGS.get(stage)
        return bool(flag_name and getattr(self, flag_name, False))

    def mark_notified(self, stage: str) -> None:
        self.save(update_fields=self._mark_notification_stage(stage))

    def reset_notifications(self) -> None:
        self.save(update_fields=self._reset_notification_flags())

    def _mark_notification_stage(self, stage: str) -> list[str]:
        if stage not in self._NOTIFICATION_FLAGS:
            raise ValueError(f"Неизвестная стадия уведомления: {stage}")

        update_fields = ["notified_stages"]
        stages = list(self.notified_stages or [])
        if stage not in stages:
            stages.append(stage)
            self.notified_stages = stages

        flag_name = self._NOTIFICATION_FLAGS[stage]
        if not getattr(self, flag_name, False):
            setattr(self, flag_name, True)
            update_fields.append(flag_name)

        return update_fields

    def _reset_notification_flags(self) -> list[str]:
        self.notified_stages = []
        update_fields = ["notified_stages"]
        for flag_name in self._NOTIFICATION_FLAGS.values():
            if getattr(self, flag_name, False):
                setattr(self, flag_name, False)
                update_fields.append(flag_name)
        return update_fields

    def complete_task(self, current_datetime):
        if self.status not in ("undone", "done"):
            self.status = "done"
            self.last_completed_date = current_datetime
            update_fields = ["status", "last_completed_date", *self._mark_notification_stage("completed")]
            self.save(update_fields=list(dict.fromkeys(update_fields)))
            return True
        return False

    def reset_task(self):
        self.status = "not_ready"
        update_fields = ["status", *self._reset_notification_flags()]
        self.save(update_fields=list(dict.fromkeys(update_fields)))
        async_to_sync(presend_filters)(text=f"🔄 Задание {self.name} обновлено", type_msg="server_checker")

    def check_status(self, current_datetime: datetime) -> None:
        if (
            not self.has_notified("alert")
            and self.status == "not_ready"
            and self.start_time
            and (
                datetime.combine(current_datetime.date(), self.start_time)
                - datetime.combine(current_datetime.date(), current_datetime.time())
            )
            <= timedelta(minutes=5)
        ):
            self.save(update_fields=self._mark_notification_stage("alert"))
            async_to_sync(presend_filters)(
                text=f"👁 {self.name} откроется через 5 минут 👁",
                type_msg="daily",
            )
        elif (
            self.status != "done"
            and not self.has_notified("lost")
            and self.end_time
            and current_datetime.time() > self.end_time
        ):
            self.status = "undone"
            update_fields = ["status", *self._mark_notification_stage("lost")]
            self.save(update_fields=list(dict.fromkeys(update_fields)))
            async_to_sync(presend_filters)(text=f"❌ {self.name} просрочен ❌", type_msg="daily")
        elif (
            not self.has_notified("deadline")
            and self.end_time
            and (
                datetime.combine(current_datetime.date(), self.end_time)
                - datetime.combine(current_datetime.date(), current_datetime.time())
            )
            < timedelta(hours=1)
        ):
            self.status = "deadline"
            update_fields = ["status", *self._mark_notification_stage("deadline")]
            self.save(update_fields=list(dict.fromkeys(update_fields)))
            async_to_sync(presend_filters)(
                text=f"🔥 {self.name} остался час на выполнение 🔥",
                type_msg="daily",
            )
        elif self.start_time and current_datetime.time() > self.start_time and not self.has_notified("start"):
            self.status = "ready"
            update_fields = ["status", *self._mark_notification_stage("start")]
            self.save(update_fields=list(dict.fromkeys(update_fields)))
            async_to_sync(presend_filters)(text=f"{self.name} доступен!", type_msg="daily")

    def check_available_status(self):
        return self.status in ("ready", "deadline")

    def check_iteration(self, current_datetime: datetime) -> None:
        if self.last_completed_date != current_datetime.date():
            self.check_status(current_datetime)
            self.save()
