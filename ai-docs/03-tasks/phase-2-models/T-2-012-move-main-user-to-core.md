# T-2-012. Перенос `main` + `user` → `apps/core`

> **Тип:** refactor / migration
> **Приоритет:** P1
> **Оценка:** 3 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Физически переместить код (`main/` → `apps/core/references/`, `user/` → `apps/core/users/`), сохранив миграции и `db_table`. Функциональность остаётся той же. Код работает через `apps.core.*`, но старые импорты `from main.models import ...` **временно продолжают работать** через compat-shim.

Риск высокий — это модели юзеров и справочников, они связаны почти со всем. Делаем аккуратно.

---

## Зависимости

- **Блокируется:** T-2-011
- **Блокирует:** T-2-025 (FK to_field), T-2-026 (ConcreteMsUser)

---

## Подход

**Django проблема:** когда ты переносишь модель в другое приложение — по дефолту генерируется миграция `RemoveModel` + `CreateModel`, и данные теряются. Чтобы этого избежать — используем `Meta.db_table` + `RunPython(code=lambda: None, reverse_code=lambda: None)` для отметки в `django_migrations`.

**Стратегия:**
1. В новом пакете создаём модель с той же `db_table`, что и в старом.
2. Генерируем миграцию через `makemigrations` — в ней будет `CreateModel`.
3. Вручную редактируем миграцию: заменяем `CreateModel` на `SeparateDatabaseAndState`, где database-операции пустые (RunSQL no-op), а state-операции — полный CreateModel. Таблица уже существует в БД — ничего физически не создаётся.
4. В старом пакете создаём миграцию `RunPython` пустую + `state_operations=[migrations.DeleteModel(...)]` — снимаем модель из state.
5. Синхронно обновляем все `from main.models import X` → `from apps.core.references.models import X`.
6. Оставляем compat-shim в `main/models.py`:
   ```python
   from apps.core.references.models import Color, Cities, Smile, Condition  # noqa: F401
   ```
   Это дает время постепенно обновлять импорты.

---

## Что нужно сделать — по шагам

### Шаг 1. Переносим `main/` → `apps/core/references/`

Содержимое `main/models.py` — Color, Cities, Smile, Condition, и т.д. Перечитай перед работой.

1. Создать файлы в `apps/core/references/`:
   - `__init__.py`
   - `apps.py` с `ReferencesConfig(name="apps.core.references", label="core_references")`
   - `models.py` — копия `main/models.py` с правкой:
     ```python
     class Color(models.Model):
         # ... поля как раньше ...
         
         class Meta:
             db_table = 'color'  # тот же что был в main — ОБЯЗАТЕЛЬНО
             # label: app_label явно не нужен если apps.py корректный
     ```
   - `admin.py`, `managers.py`, etc. — тоже перенести

2. Зарегистрировать в `INSTALLED_APPS`:
   ```python
   "apps.core.references",
   ```

### Шаг 2. Миграции — `SeparateDatabaseAndState`

1. Сгенерировать:
   ```bash
   python manage.py makemigrations core_references --name=initial_state_import
   ```
   Увидишь миграцию с `CreateModel` для всех моделей.

2. Отредактировать её вручную:
   ```python
   from django.db import migrations, models

   class Migration(migrations.Migration):
       initial = True
       dependencies = []
       
       operations = [
           migrations.SeparateDatabaseAndState(
               database_operations=[],  # таблицы уже есть
               state_operations=[
                   migrations.CreateModel(
                       name='Color',
                       fields=[...],  # как было в автогенерации
                       options={'db_table': 'color', 'verbose_name': 'Цвет', ...},
                   ),
                   # остальные модели
               ],
           ),
       ]
   ```

3. В старом `main/migrations/` создать новую:
   ```bash
   python manage.py makemigrations main --empty --name=remove_models_moved_to_core_references
   ```
   
   Отредактировать:
   ```python
   from django.db import migrations
   
   class Migration(migrations.Migration):
       dependencies = [
           ('main', 'XXXX_previous_migration'),
           ('core_references', '0001_initial_state_import'),
       ]
       
       operations = [
           migrations.SeparateDatabaseAndState(
               database_operations=[],  # таблицы не трогаем
               state_operations=[
                   migrations.DeleteModel(name='Color'),
                   migrations.DeleteModel(name='Cities'),
                   migrations.DeleteModel(name='Smile'),
                   migrations.DeleteModel(name='Condition'),
                   # ... все модели из main
               ],
           ),
       ]
   ```

4. Прогнать на dev-копии прод-БД (см. T-2-001):
   ```bash
   python manage.py migrate
   # Ожидание: миграции применены, данные не тронуты
   ```

5. **Верификация:**
   ```bash
   python manage.py shell -c "
   from apps.core.references.models import Color
   print(Color.objects.count())  # должно быть >0 с прод-данными
   "
   ```

### Шаг 3. Compat-shim в `main/`

`main/models.py` становится:
```python
"""Compat shim — модели переехали в apps.core.references.

Этот модуль будет удалён в Фазе 3 после того, как все импорты
обновлены. Не добавляй сюда новый код!
"""
from apps.core.references.models import (  # noqa: F401
    Color, Cities, Smile, Condition,
)
```

Аналогично `main/admin.py` (тоже shim), `main/managers.py` и т.д.

### Шаг 4. Перенос `user/` → `apps/core/users/`

Полностью аналогично шагам 1-3. Отличия:
- `user.MsUser` и `user.ConcreteMsUser` — последний удалится в T-2-026, пока переносим как есть
- `AUTH_USER_MODEL` в settings: `"core_users.MsUser"` (по новому label)
- **Тестирование смены AUTH_USER_MODEL требует особой осторожности** — Django запоминает его в миграциях. Миграция на смену `AUTH_USER_MODEL` должна быть пустой с явной `app_label` привязкой.

**Альтернативный вариант для user:** оставь label=`user` (`UserConfig(label="user")`). Тогда `AUTH_USER_MODEL` остаётся `"user.MsUser"`, не нужно менять. Рекомендую этот путь — безопаснее.

### Шаг 5. Обновить импорты по всему коду

```bash
# Главные импорты
grep -rln "from main.models import" --include="*.py" | xargs sed -i \
  's|from main.models import|from apps.core.references.models import|g'

grep -rln "from user.models import" --include="*.py" | xargs sed -i \
  's|from user.models import|from apps.core.users.models import|g'

# Тщательно проверить:
# - admin.py файлы
# - templatetags — часто импортируют Cities, Color и т.п.
# - migrations других apps — НЕ ТРОГАТЬ, там должны остаться старые пути
#   (если тронешь — миграции сломаются)
```

**КРИТИЧНО:** не меняй импорты в `*/migrations/*.py`. Там пути должны остаться как были (иначе история миграций сломается).

### Шаг 6. Тестируй

```bash
python manage.py check
python manage.py makemigrations --dry-run  # не должно предлагать новых миграций
pytest
# Ручное: поднять dev, открыть /admin, проверить что Cities/Colors/Users работают
```

---

## Критерии приёмки

- [ ] `apps/core/references/` и `apps/core/users/` содержат модели
- [ ] Миграции `SeparateDatabaseAndState` применены, данные на dev-копии прода НЕ потеряны
- [ ] `main/models.py`, `user/models.py` — compat-shim с re-export
- [ ] Все `from main.models` / `from user.models` в **не-migrations** файлах — обновлены
- [ ] В migrations старые импорты — НЕ тронуты
- [ ] `python manage.py makemigrations --dry-run` — ничего не предлагает
- [ ] `python manage.py check` — чисто
- [ ] `pytest` — проходит
- [ ] Ручной smoke-test: админка /admin — работает

---

## Что НЕ делать

- **НЕ меняй** `db_table` в моделях — это сохранение прод-данных
- **НЕ удаляй** `main/` или `user/` папки — compat-shim там живёт
- **НЕ трогай** миграции legacy-apps (кроме созданной на шаге 2)
- **НЕ меняй** `AUTH_USER_MODEL`, если не уверен — держи legacy label `user`
- **НЕ переноси** сразу всё одним коммитом — сначала references, убедись что работает, потом users

---

## Риски и митигация

| Риск | Митигация |
|---|---|
| Миграции `SeparateDatabaseAndState` применились некорректно, Django думает что таблицы нет | `python manage.py sqlmigrate core_references 0001` покажет SQL. Должен быть пустой (кроме INSERT в django_migrations). Если нет — ошибка в database_operations=[] |
| Другие apps ссылаются `"main.Color"` в FK | Django-доки: `db_table` сохраняется → FK работает. Но если где-то string-ссылка `"main.Color"` — после переноса станет `"core_references.Color"`. Надо обновить. Тест: `python manage.py check` ловит сломанные FK |
| Админка сломалась | Часто `admin.site.register(Color)` был в `main/admin.py`. Перенести в `apps/core/references/admin.py` |
| `user` переименовать рискованно | Оставь label=`user` как есть, только физическая папка в `apps/core/users/`. `AUTH_USER_MODEL=user.MsUser` остаётся |

---

## Вопросы

- [ ] Нужно ли объединять `main` и `user` в один шаг или делить на два PR? **Архитектор рекомендует два PR** — проще откатывать.
