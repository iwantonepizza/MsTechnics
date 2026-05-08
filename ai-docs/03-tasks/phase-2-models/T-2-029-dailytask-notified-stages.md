# T-2-029. `DailyTask.*_notification_sent` → `notified_stages: JSONField`

> **Тип:** migration / refactor
> **Приоритет:** P2
> **Оценка:** 1.5 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

В `DailyTask` есть несколько булевых полей вроде:
```python
morning_notification_sent = BooleanField(default=False)
afternoon_notification_sent = BooleanField(default=False)
evening_notification_sent = BooleanField(default=False)
```

Это антипаттерн: каждое новое время уведомления = новое поле + миграция. Заменяем на `notified_stages: JSONField` со списком идентификаторов уже отправленных стадий.

---

## Зависимости

- **Блокируется:** нет (независимая)

---

## Целевая модель

```python
class DailyTask(models.Model):
    # ... существующие поля ...
    
    notified_stages = models.JSONField(
        default=list,  # будет list-of-str, напр. ['morning', 'afternoon']
        blank=True,
        verbose_name='Отправленные напоминания'
    )
    
    # Старые поля пока оставляем! Удаляем в отдельной миграции после паузы.
    morning_notification_sent = ...  # legacy
    afternoon_notification_sent = ...  # legacy
    evening_notification_sent = ...  # legacy
```

И методы:
```python
def has_notified(self, stage: str) -> bool:
    return stage in (self.notified_stages or [])

def mark_notified(self, stage: str) -> None:
    stages = list(self.notified_stages or [])
    if stage not in stages:
        stages.append(stage)
    self.notified_stages = stages
    self.save(update_fields=['notified_stages'])

def reset_notifications(self) -> None:
    """Вызывается при старте нового дня."""
    self.notified_stages = []
    self.save(update_fields=['notified_stages'])
```

---

## Что нужно сделать

### Шаг 1. Добавить поле

```python
# 00XX_add_notified_stages_to_dailytask.py
migrations.AddField(
    model_name='dailytask',
    name='notified_stages',
    field=models.JSONField(default=list, blank=True),
)
```

### Шаг 2. Backfill

```python
# 00XX_backfill_notified_stages.py
def forwards(apps, schema_editor):
    DailyTask = apps.get_model('<app_label>', 'DailyTask')
    for task in DailyTask.objects.all().iterator(chunk_size=500):
        stages = []
        if task.morning_notification_sent:
            stages.append('morning')
        if task.afternoon_notification_sent:
            stages.append('afternoon')
        if task.evening_notification_sent:
            stages.append('evening')
        task.notified_stages = stages
        task.save(update_fields=['notified_stages'])

class Migration(migrations.Migration):
    dependencies = [('...', '00XX_add_notified_stages_to_dailytask')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
```

### Шаг 3. Обновить worker `daily_checker.py`

Где было:
```python
if current_hour == 9 and not task.morning_notification_sent:
    send_notification(task)
    task.morning_notification_sent = True
    task.save()
```

Стало:
```python
stage = determine_stage(current_hour)  # 'morning' | 'afternoon' | 'evening'
if stage and not task.has_notified(stage):
    send_notification(task)
    task.mark_notified(stage)
```

Функция `determine_stage(hour)`:
```python
def determine_stage(hour: int) -> str | None:
    if 9 <= hour < 12:  return 'morning'
    if 12 <= hour < 17: return 'afternoon'
    if 17 <= hour < 20: return 'evening'
    return None
```

### Шаг 4. Сброс в начале дня

В `daily_checker.py` должен быть cron-like блок, который сбрасывает `notified_stages = []` в начале нового дня (00:00 local time). Проверить что так и есть, адаптировать.

### Шаг 5. После паузы — удалить старые поля

В **отдельной задаче** (запланировать через 2 недели как T-2-029-followup):
```python
migrations.RemoveField(model_name='dailytask', name='morning_notification_sent'),
migrations.RemoveField(model_name='dailytask', name='afternoon_notification_sent'),
migrations.RemoveField(model_name='dailytask', name='evening_notification_sent'),
```

---

## Критерии приёмки

- [ ] Поле `notified_stages: JSONField` добавлено
- [ ] Backfill данных из трёх boolean-полей применён
- [ ] `DailyTask.has_notified(stage)`, `.mark_notified(stage)`, `.reset_notifications()` методы реализованы
- [ ] `daily_checker.py` обновлён на новые методы
- [ ] Старые boolean-поля временно остались (для отката)
- [ ] Unit-тесты:
  - has_notified возвращает True после mark_notified
  - mark_notified идемпотентен (дубли не создаются)
  - reset_notifications очищает список
- [ ] Worker `daily_checker` тестово прогнан на dev

---

## Что НЕ делать

- **НЕ удаляй** старые поля в этой задаче — следующая
- **НЕ меняй** расписание (часы стадий) — только структуру хранения
- **НЕ используй** `models.ArrayField` (Postgres-specific) — JSONField переносимее
