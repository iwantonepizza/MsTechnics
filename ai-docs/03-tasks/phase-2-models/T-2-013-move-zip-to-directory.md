# T-2-013. `zip/` → `apps/directory/` + переименование `Panels` → `Panel`

> **Тип:** refactor / migration
> **Приоритет:** P1
> **Оценка:** 3 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Перенести `zip/` в `apps/directory/` (три sub-app: `displays`, `panels`, `storage`). Одновременно **переименовать модель `Panels` в `Panel`** (в единственном числе — Django конвенция).

---

## Зависимости

- **Блокируется:** T-2-011, T-2-012 (references уже в apps.core)
- **Блокирует:** T-2-027 (Display.save), T-2-028 (application_status), T-2-041 (PanelMover)

---

## Структура target

```
apps/directory/
├── __init__.py
├── apps.py                     # DirectoryConfig(label='directory')
├── displays/
│   ├── __init__.py
│   ├── apps.py                 # DisplaysConfig(label='directory_displays')
│   ├── models.py               # Display, Cell
│   ├── admin.py
│   └── managers.py
├── panels/
│   ├── __init__.py
│   ├── apps.py                 # PanelsConfig(label='directory_panels')
│   ├── models.py               # Panel (ex-Panels), Department
│   ├── admin.py
│   └── managers.py
└── storage/
    ├── __init__.py
    ├── apps.py                 # StorageConfig(label='directory_storage')
    └── models.py               # Wires, Hubs, Lamels
```

---

## Что нужно сделать

### Шаг 1. Панель: `Panels` → `Panel`

Имена моделей Python регистр-зависимы, но Django хранит их в `django_migrations` и `ContentType`. Переименование — две операции:

1. Python-уровень: `class Panels` → `class Panel` + `__all__` re-export для compat:
   ```python
   # apps/directory/panels/models.py
   class Panel(models.Model):
       # поля как были в Panels
       class Meta:
           db_table = 'panels'  # таблица остаётся — SAVE прод-данные
           verbose_name = 'Панель'
           verbose_name_plural = 'Панели'
   
   # Совместимость:
   Panels = Panel  # старые импорты `from zip.models import Panels` работают
   ```

2. Миграция переименования в state:
   ```python
   # apps/directory/panels/migrations/0002_rename_panels_to_panel.py
   class Migration(migrations.Migration):
       dependencies = [('directory_panels', '0001_initial_state_import')]
       operations = [
           migrations.RenameModel(old_name='Panels', new_name='Panel'),
       ]
   ```

   **Важно:** `RenameModel` по дефолту переименовывает `db_table`. Чтобы этого избежать — после `RenameModel` добавить:
   ```python
   migrations.AlterModelTable(name='panel', table='panels'),  # оставить старое имя таблицы
   ```
   
   Или использовать `SeparateDatabaseAndState`:
   ```python
   migrations.SeparateDatabaseAndState(
       database_operations=[],
       state_operations=[migrations.RenameModel(old_name='Panels', new_name='Panel')],
   ),
   ```

3. `ContentType` запись может остаться старой. Для чистоты — `update_contenttypes` management-команда:
   ```bash
   python manage.py remove_stale_contenttypes --include-stale-apps
   ```

### Шаг 2. Перенос `zip/` → `apps/directory/`

Аналогично T-2-012, но разбитый на 3 sub-app'а:

**displays** (Display, Cell):
- `apps/directory/displays/models.py` — Display, Cell
- Миграция: `SeparateDatabaseAndState` с `CreateModel` для обеих
- `Display.save()` пока **остаётся как есть** (логика с side effects) — чиним в T-2-027
- `Meta.db_table = 'display'` / `'cell'` — не менять

**panels** (Panel, Department):
- `apps/directory/panels/models.py` — Panel (rename), Department
- Миграции: initial + rename
- FK из Cell → Panel — остаётся через `directory_panels.Panel` (Django автоматически обновит через label + model name)

**storage** (Wires, Hubs, Lamels — они есть в zip/models.py):
- Отдельный sub-app — логически это другая сущность (расходники, не панели)
- `db_table` остаются исходными

### Шаг 3. Обновление FK

Важно: в других приложениях могут быть FK с строковыми ссылками:
```python
# application/models.py (старое):
panel = models.ForeignKey("zip.Panels", ...)
```

После переноса:
```python
panel = models.ForeignKey("directory_panels.Panel", ...)
```

**Но!** Старые миграции (`application/migrations/*.py`) трогать **нельзя** — там есть исторические ссылки `"zip.Panels"`, которые нужны для применения на старых снимках БД.

Решение: Django имеет `Meta.app_label` + `db_table` — рельсы сохраняются. Но для string-FK в моделях — обновить:

```python
# apps/workflow/applications/models.py (когда сделаем T-2-014)
panel = models.ForeignKey("directory_panels.Panel", to_field='name', ...)
```

Когда ты **перед T-2-014** это трогаешь — применяется `swappable`-паттерн Django. Но проще: сначала сделай T-2-013 (directory), потом в T-2-014 перенеси application и перепиши FK-строки.

### Шаг 4. Compat-shim

`zip/models.py` становится:
```python
"""Compat shim — модели переехали в apps.directory."""
from apps.directory.displays.models import Display, Cell  # noqa: F401
from apps.directory.panels.models import Panel, Department  # noqa: F401
from apps.directory.storage.models import Wires, Hubs, Lamels  # noqa: F401

# Легаси-имя:
Panels = Panel  # noqa: F401
```

`zip/admin.py`, `zip/utils.py` — shim аналогично.

### Шаг 5. Тестируй миграции ТЩАТЕЛЬНО

Это самая рискованная задача Фазы 2. Panel — центральная модель, проверь:

```bash
# 1. Чистая БД
python manage.py migrate
# Все миграции применяются без ошибок

# 2. На копии прод-БД
./scripts/bootstrap_dev.sh dumps/prod-latest.sql.gz
python manage.py migrate
# Данные не потеряны, таблицы panels, display, cell — на месте, строки те же

# 3. Regression-тесты из T-2-003 — проходят

# 4. Вручную в admin:
# - /admin/directory/panel/ — список панелей работает
# - /admin/directory/display/ — экраны работают
# - /admin/application/application/ — заявки ссылаются на панели корректно
```

---

## Критерии приёмки

- [ ] `apps/directory/{displays,panels,storage}/` созданы с моделями
- [ ] Модель переименована: `Panels` → `Panel`, `db_table` остался `'panels'`
- [ ] `Panels = Panel` alias в compat-shim для старых импортов
- [ ] Миграции `SeparateDatabaseAndState` — state изменился, БД не тронута
- [ ] Ручной тест на копии прода: все данные на месте
- [ ] regression-тесты T-2-003 — проходят
- [ ] `admin.site` регистрирует модели из новых мест, а не из `zip/admin.py`
- [ ] `python manage.py check` — чисто
- [ ] `ContentType.objects.filter(app_label='zip').count()` — можно оставить или удалить, решение по месту

---

## Что НЕ делать

- **НЕ переименовывай `db_table`** — прод-данные потеряются
- **НЕ трогай** `Display.save()` (это T-2-027)
- **НЕ меняй** FK в других apps пока не переносишь их сами (T-2-014)
- **НЕ удаляй** `zip/` папку — shim-файлы внутри нужны
- **НЕ забудь** зарегистрировать 3 новых AppConfig в `INSTALLED_APPS`

---

## Риски

- **ContentType кэш.** Django кэширует ContentType, при rename может сбоить. Решение: `ContentType.objects.clear_cache()` в начале миграции или `python manage.py migrate --run-syncdb`.
- **Admin break.** `admin.autodiscover()` ищет `admin.py` в каждом INSTALLED_APP. Если регистрация дублируется (в `zip/admin.py` и `apps/directory/*/admin.py`) — `AlreadyRegistered`. Оставить регистрацию только в новом месте.
- **Generic FKs.** Если где-то используется `ContentType.objects.get_for_model(Panel)` — после rename: `ContentType(app_label='directory_panels', model='panel')`. Старый `('zip', 'panels')` останется в БД как stale. Логика GenericForeignKey может указывать на stale type — проверить руками.

---

## Вопросы

- [ ]
