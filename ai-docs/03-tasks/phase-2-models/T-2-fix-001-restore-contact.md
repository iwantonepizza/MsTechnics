# T-2-fix-001. Перенести `Contact` в `apps/workflow/departures/`

> **Тип:** hotfix / migration
> **Приоритет:** P0 (BLOCKER запуска)
> **Оценка:** 0.5 часа
> **Фаза:** 2 (доработка)
> **Статус:** done

---

## Цель

Закрыть блокер запуска: класс `Contact` ссылается из `departure/admin.py`, но в новых моделях `apps/workflow/departures/models.py` отсутствует. `python manage.py check` падает с `NameError: name 'Contact' is not defined`.

Архитектор подтвердил: модель **используется** — это контакт-лист с привязкой к экранам (отображается на странице отдела через `templates/main_menu/main_department_menu.html`).

---

## Зависимости

- **Блокируется:** T-2-014 (departure уже перенесён, Contact забыт)
- **Блокирует:** запуск Django, Фаза 3

---

## Структура модели Contact (из legacy migrations)

```python
class Contact(models.Model):
    first_name   = CharField(max_length=150, blank=True, verbose_name='Имя')
    last_name    = CharField(max_length=150, blank=True, verbose_name='Фамилия')
    description  = CharField(max_length=150, blank=True, verbose_name='Описание')
    phone_number = CharField(max_length=15, blank=True, null=True, verbose_name='Номер телефона')
    telegram_id  = CharField(max_length=15, blank=True, null=True, verbose_name='Айди телеграм')
    displays     = ManyToManyField('directory_displays.Display', related_name='contacts',
                                   verbose_name='Список экранов')
    
    class Meta:
        db_table = 'contact'
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'
        ordering = ['id']
```

Таблица существует в проде (создана `departure/migrations/0001_initial.py`).

---

## Что нужно сделать

### Шаг 1. Добавить модель в `apps/workflow/departures/models.py`

Добавить класс `Contact` рядом с существующими `Executor`, `Departure`, `DepartureHistoryReport`. Обрати внимание:

- `db_table = 'contact'` — оставить, не менять (прод-таблица)
- `displays = ManyToManyField('directory_displays.Display', ...)` — string-FK, чтобы избежать circular import

### Шаг 2. State-only миграция

Создать `apps/workflow/departures/migrations/0003_add_contact_state.py`:

```python
"""T-2-fix-001: импортируем существующую таблицу contact в state.

Таблица уже существует в проде через legacy departure/migrations/0001_initial.py.
Это миграция state-only — БД не трогаем.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('workflow_departures', '0002_departure_status_fk'),
        ('directory_displays', '0001_initial_state_import'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # таблица contact уже есть
            state_operations=[
                migrations.CreateModel(
                    name='Contact',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ('first_name', models.CharField(blank=True, max_length=150, verbose_name='Имя')),
                        ('last_name', models.CharField(blank=True, max_length=150, verbose_name='Фамилия')),
                        ('description', models.CharField(blank=True, max_length=150, verbose_name='Описание')),
                        ('phone_number', models.CharField(blank=True, max_length=15, null=True, verbose_name='Номер телефона')),
                        ('telegram_id', models.CharField(blank=True, max_length=15, null=True, verbose_name='Айди телеграм')),
                        ('displays', models.ManyToManyField(related_name='contacts',
                                                              to='directory_displays.display',
                                                              verbose_name='Список экранов')),
                    ],
                    options={
                        'verbose_name': 'Контакт',
                        'verbose_name_plural': 'Контакты',
                        'db_table': 'contact',
                        'ordering': ['id'],
                    },
                ),
            ],
        ),
    ]
```

### Шаг 3. State-only миграция в legacy `departure`

Снять модель из state legacy-app:

`departure/migrations/0003_remove_contact_from_state.py`:

```python
"""T-2-fix-001: снимаем Contact из state legacy app departure."""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('departure', '0002_initial'),
        ('workflow_departures', '0003_add_contact_state'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='Contact'),
            ],
        ),
    ]
```

### Шаг 4. Compat-shim

Обновить `departure/models.py`:

```python
"""
departure/models.py — compat shim.
Модели переехали в apps.workflow.departures (T-2-014, T-2-fix-001).
"""
from apps.workflow.departures.models import (  # noqa: F401
    Contact,
    Departure,
    DepartureHistoryReport,
    Executor,
)
```

### Шаг 5. Проверка

```bash
python manage.py check
# ожидание: System check identified no issues

python manage.py makemigrations --dry-run
# ожидание: No changes detected

# На копии прода:
./scripts/bootstrap_dev.sh dumps/prod-latest.sql.gz
python manage.py migrate
# ожидание: миграции применены без ошибок
```

### Шаг 6. M2M к Display через FK to_field='id'

В legacy проде у `Display` PK был `id` (поле в модели `Display.name` — unique но не PK). Поэтому M2M через `to='directory_displays.display'` ссылается на `Display.id` корректно.

**Но:** если кодер обнаружит, что в проде M2M-таблица `contact_displays` использует `display_id` где значения = `display.name` (строки), а не int — это станет проблемой. Маловероятно (Django M2M всегда через PK), но проверить:

```sql
\d contact_displays
SELECT display_id, count(*) FROM contact_displays GROUP BY display_id LIMIT 5;
-- если display_id это int — всё ок
-- если это varchar (строка) — копать глубже
```

---

## Критерии приёмки

- [ ] Класс `Contact` есть в `apps/workflow/departures/models.py`
- [ ] Миграция `0003_add_contact_state` применяется на чистой БД (state-only)
- [ ] Миграция `departure/migrations/0003_remove_contact_from_state` применяется
- [ ] `python manage.py check` — чисто
- [ ] `python manage.py makemigrations --dry-run` — пусто
- [ ] `departure/admin.py` импорт `Contact` через shim работает (admin загружается без ошибок)
- [ ] Смоук-тест: `from apps.workflow.departures.models import Contact; print(Contact.objects.count())` возвращает число (≥ 0)
- [ ] На копии прод-БД миграции применяются, данные `contact` на месте

---

## Что НЕ делать

- **НЕ копируй** legacy миграцию `departure/migrations/0001_initial.py` целиком — там есть `Departure` и др., которые уже перенесены
- **НЕ меняй** `db_table='contact'`
- **НЕ удаляй** `from departure.models import *` в `departure/admin.py` — оно подтянет всё через shim

---

## Отчёт

После закрытия — отчёт `ai-docs/08-reports/T-2-fix-001.md` по шаблону. Указать:
- Сколько строк в таблице `contact` на копии прода
- Какие admin-классы зависят от Contact (нашлось ли больше точек?)
