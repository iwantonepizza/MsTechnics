# T-2-021. Удалить 28 старых полей из `Application`

> **Тип:** migration
> **Приоритет:** P1
> **Оценка:** 1 час
> **Фаза:** 2
> **Статус:** blocked (ждёт 2-недельной паузы после T-2-020)

---

## Цель

После успешной миграции данных в `ApplicationEvent` (T-2-020) и 2-недельного наблюдения — физически удалить 28 denormalized-колонок из таблицы `application`.

---

## Зависимости

- **Блокируется:** T-2-020 (данные перенесены)
- **Блокируется:** переход всего кода, пишущего в старые поля, на `ApplicationEvent` (внутри T-2-040 FSM)

---

## Подготовка (перед миграцией)

1. **Убедиться что код больше не пишет** в старые поля:
   ```bash
   grep -rln "comment_monitoring\|time_monitoring\|user_monitoring\|file_monitoring" --include="*.py" . | grep -v migrations | grep -v compat
   grep -rln "comment_control_apply\|time_control_apply\|user_control_apply\|file_control_apply" --include="*.py" . | grep -v migrations
   # ... для каждого из 7 этапов × 4 типа поля = 28 комбинаций
   ```
   
   После T-2-040 всё должно читать/писать через `ApplicationEvent`. Если остались `app.comment_monitoring = ...` — это баг, фиксим до удаления колонок.

2. **Данные верифицированы:**
   ```bash
   python manage.py verify_application_events
   # 0 bad
   ```

3. **Прождать 2 недели** после T-2-020 в проде. Если за этот период кто-то заметит, что данные не сохранились — откатить T-2-020, разобраться.

---

## Что нужно сделать

### Шаг 1. Архив перед удалением

Сделать дамп таблицы `application` в отдельный файл — на случай восстановления:
```bash
pg_dump "$PROD_DATABASE_URL" -t application -f application_before_T-2-021.sql
gzip application_before_T-2-021.sql
# положить в защищённое хранилище, НЕ в git
```

### Шаг 2. Миграция

```bash
python manage.py makemigrations workflow_applications --name=drop_denormalized_application_fields
```

Содержимое (тщательно выверенный список из 28 полей):

```python
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('workflow_applications', 'XXXX_backfill_application_events'),
    ]
    
    operations = [
        # Monitoring stage (4 поля)
        migrations.RemoveField(model_name='application', name='comment_monitoring'),
        migrations.RemoveField(model_name='application', name='time_monitoring'),
        migrations.RemoveField(model_name='application', name='file_monitoring'),
        migrations.RemoveField(model_name='application', name='user_monitoring'),
        
        # Control apply (4)
        migrations.RemoveField(model_name='application', name='comment_control_apply'),
        migrations.RemoveField(model_name='application', name='time_control_apply'),
        migrations.RemoveField(model_name='application', name='file_control_apply'),
        migrations.RemoveField(model_name='application', name='user_control_apply'),
        
        # Control send (4)
        migrations.RemoveField(model_name='application', name='comment_control_send'),
        migrations.RemoveField(model_name='application', name='time_control_send'),
        migrations.RemoveField(model_name='application', name='file_control_send'),
        migrations.RemoveField(model_name='application', name='user_control_send'),
        
        # Service apply (4)
        migrations.RemoveField(model_name='application', name='comment_service_apply'),
        migrations.RemoveField(model_name='application', name='time_service_apply'),
        migrations.RemoveField(model_name='application', name='file_service_apply'),
        migrations.RemoveField(model_name='application', name='user_service_apply'),
        
        # Control at work (4)
        migrations.RemoveField(model_name='application', name='comment_control_at_work'),
        migrations.RemoveField(model_name='application', name='time_control_at_work'),
        migrations.RemoveField(model_name='application', name='file_control_at_work'),
        migrations.RemoveField(model_name='application', name='user_control_at_work'),
        
        # Control unable (4)
        migrations.RemoveField(model_name='application', name='comment_control_unable'),
        migrations.RemoveField(model_name='application', name='time_control_unable'),
        migrations.RemoveField(model_name='application', name='file_control_unable'),
        migrations.RemoveField(model_name='application', name='user_control_unable'),
        
        # Control archive (4)
        migrations.RemoveField(model_name='application', name='comment_control_archive'),
        migrations.RemoveField(model_name='application', name='time_control_archive'),
        migrations.RemoveField(model_name='application', name='file_control_archive'),
        migrations.RemoveField(model_name='application', name='user_control_archive'),
    ]
```

### Шаг 3. Удалить поля из модели Python

В `apps/workflow/applications/models.py` — удалить 28 полей из `class Application`.

### Шаг 4. Тест на dev-копии прода

Перед применением в проде:
```bash
./scripts/bootstrap_dev.sh dumps/prod-latest.sql.gz
python manage.py migrate
# 28 колонок удалены, данные из application_event на месте
psql -c "SELECT count(*) FROM application_event;"
```

### Шаг 5. Прод-миграция

`ALTER TABLE ... DROP COLUMN` на Postgres — атомарна, но блокирует таблицу на время. Для таблицы в 100K строк — ~1 секунда. Для 1M+ — до минуты.

Лучше применить **ночью** или в окно низкой нагрузки. Один `BEGIN; DROP ... DROP ... DROP; COMMIT;`.

---

## Критерии приёмки

- [ ] 28 колонок физически удалены из `application` таблицы на проде
- [ ] 28 атрибутов удалены из `Application` Python-модели
- [ ] `python manage.py check` — чисто
- [ ] `grep -rln "comment_monitoring\|time_monitoring" --include="*.py" .` — только в migrations
- [ ] Regression-тесты проходят
- [ ] В продакшене creating / transitioning / displaying заявок работает корректно
- [ ] Сохранён архив прод-таблицы `application` перед удалением (`application_before_T-2-021.sql.gz`, **вне репо**, в защищённом хранилище)

---

## Что НЕ делать

- **НЕ удаляй** ДО T-2-040 (FSM) и полного обновления views
- **НЕ удаляй** без 2-недельной паузы после T-2-020
- **НЕ удаляй** без архивного дампа
- **НЕ удаляй** в одной миграции с другими изменениями — это backward-incompatible

---

## Откат если что-то пошло не так

Если после применения обнаружится, что данные нужны:
1. `ALTER TABLE application ADD COLUMN ...` (пустые)
2. `INSERT ... FROM application_before_T-2-021.sql` — восстановить старые значения
3. Python-модель вернуть как была
4. `python manage.py migrate --fake workflow_applications XXXX_previous`

Это сложно и требует downtime. Лучше так не делать — отсюда важность пауз T-2-020 → T-2-021.
