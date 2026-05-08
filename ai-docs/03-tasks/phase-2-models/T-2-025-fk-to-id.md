# T-2-025. FK `to_field='name'` → `to_field='id'`

> **Тип:** migration
> **Приоритет:** P1
> **Оценка:** 4 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

В старом коде сплошь и рядом FK делают через `to_field='name'`. Это значит, что вместо integer-FK используется string-join по уникальному полю. Проблемы:
- Медленнее (индекс по строке > индекс по int)
- Неустойчиво к переименованиям (если поменять `name` — FK ломается)
- Python-аномалии: `model.field_name` даёт строку вместо объекта

Переход на `to_field='id'` (дефолт) — быстрее и устойчивее.

---

## Зависимости

- **Блокируется:** T-2-013, T-2-014 (модели в новых местах)
- **Блокирует:** API Фазы 3 (там id используется в URL)

---

## Охват

Найти все места:
```bash
grep -rn "to_field=" --include="*.py" . | grep -v migrations | sort -u
```

Типичные случаи (из прочтения кода проекта):

| FK в модели | Целевое поле | Новое целевое |
|---|---|---|
| `Application.display → Display.name` | name | id |
| `Application.panel → Panel.name` | name | id |
| `Application.status → ApplicationStatus.name` | name | id |
| `Cell.display → Display.name` | name | id |
| `Cell.panel → Panel.name` | name | id |
| `Display.city → Cities.name` | name | id |
| `ApplicationStatus.color → Color.name` | name | id |
| `ApplicationStatus.icon → Smile.smile_icon` | smile_icon | id |
| `Condition.color → Color.name` | name | id |
| `Panel.display → Display.name` | name | id |
| `Panel.department → Department.name` | name | id |
| `Panel.condition → Condition.name` | name | id |

---

## Подход

**Нельзя** просто убрать `to_field='name'` — это изменит тип колонки в БД. Нужна data-миграция:

1. Добавить новое поле `<fk>_new_id: int` (nullable)
2. Backfill: для каждой записи установить `<fk>_new_id = <current_fk>.id` 
3. Сделать NOT NULL, добавить индекс, добавить FK constraint
4. Удалить старое поле
5. Переименовать `<fk>_new_id` → `<fk>_id`

По одной модели за раз. Не делать всё сразу.

Для каждой модели — отдельный PR. Это тянется на ~12 PR, но каждый безопасен.

---

## Пример: Application.display (to_field='name' → id)

### Миграция 1: add new_id field

```python
# apps/workflow/applications/migrations/00XX_add_display_new_id.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('workflow_applications', 'XXXX_previous')]
    operations = [
        migrations.AddField(
            model_name='application',
            name='display_new_id',  # временное имя
            field=models.IntegerField(null=True, blank=True, db_index=True),
        ),
    ]
```

### Миграция 2: backfill data

```python
# 00XX_backfill_application_display_id.py
from django.db import migrations

def forwards(apps, schema_editor):
    Application = apps.get_model('workflow_applications', 'Application')
    Display = apps.get_model('directory_displays', 'Display')
    
    name_to_id = dict(Display.objects.values_list('name', 'id'))
    
    for app in Application.objects.filter(display_new_id__isnull=True).iterator(chunk_size=500):
        # app.display_id сейчас содержит NAME (because to_field='name')
        name = app.display_id
        new_id = name_to_id.get(name)
        if new_id is None:
            # broken FK? — skip with warning
            print(f'WARN: application {app.id} has display_id={name} not in Display')
            continue
        app.display_new_id = new_id
        app.save(update_fields=['display_new_id'])


class Migration(migrations.Migration):
    dependencies = [('workflow_applications', '00XX_add_display_new_id')]
    atomic = False
    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
```

### Миграция 3: replace old fk

```python
# 00XX_replace_application_display_fk.py
class Migration(migrations.Migration):
    dependencies = [('workflow_applications', '00XX_backfill_application_display_id')]
    operations = [
        migrations.RemoveField(model_name='application', name='display'),
        migrations.RenameField(model_name='application', old_name='display_new_id', new_name='display_id'),
        migrations.AddField(
            model_name='application',
            name='display',
            field=models.ForeignKey(
                'directory_displays.Display',
                on_delete=models.PROTECT,
                null=True,
                related_name='applications',
                # to_field не указан — дефолт id
            ),
        ),
    ]
```

**Важно:** `AddField` после `RenameField` на существующую колонку `display_id` будет работать, т.к. Django именует FK-колонку как `<fieldname>_id`. Но в некоторых случаях Django сгенерирует миграцию иначе — проверить сгенерированный SQL:
```bash
python manage.py sqlmigrate workflow_applications 00XX_replace_application_display_fk
```

### Обновить Python-модель

```python
# apps/workflow/applications/models.py
class Application(models.Model):
    display = models.ForeignKey(
        'directory_displays.Display',
        on_delete=models.PROTECT,
        null=True,
        related_name='applications',
        # to_field='name' УДАЛИТЬ
    )
```

---

## Критерии приёмки

- [ ] Для каждой FK из списка — 3 миграции (add, backfill, replace)
- [ ] После всех миграций: `python manage.py makemigrations --dry-run` — пусто
- [ ] `python manage.py check` — чисто
- [ ] Тест на dev-копии прода: все FK резолвятся, `app.display.name` возвращает правильное имя
- [ ] Regression-тесты проходят
- [ ] Performance: выборка `Application.objects.select_related('display').all()` стала быстрее (бенчмарк до/после)
- [ ] В коде больше нет `to_field=` (кроме возможно `email` у User — там обосновано)

---

## Что НЕ делать

- **НЕ делай** всё одним PR — по одной FK за раз
- **НЕ меняй** одновременно модель Python и миграции — применяй миграции ПЕРЕД обновлением модели
- **НЕ используй** `bulk_update` в backfill — он не вызывает `save()` и может не обновить индексы; либо через `update()`, либо `save()`
- **НЕ удаляй** старое поле пока не создан новый — данные потеряются

---

## Риски

- **`related_name` конфликты.** После change FK Django может требовать уникальный `related_name` если старый `'application'` занят где-то ещё. Переименовать аккуратно.
- **Broken FK в данных.** В проде могут быть записи, где `display_id` ссылается на name, которого уже нет в Display (orphan record). Backfill warning — проверить и вручную исправить.
- **Масштаб PR.** 12 моделей × 3 миграции = 36 миграций. Это много. Группировать по связанным (все FK на `Color`, все на `Condition`) — 5-6 PR вместо 12.

---

## Оценка по частям

- Application × 4 FK = 1 ч
- Cell × 2 FK = 0.5 ч
- Panel × 3 FK = 1 ч
- ApplicationStatus × 3 FK = 0.5 ч
- Condition × 3 FK = 0.5 ч
- Display × 1 FK = 0.5 ч

Итого 4 часа. Можно распределить на 2-3 дня по 1-2 ч.
