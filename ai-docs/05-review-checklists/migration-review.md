# Migration Review Checklist

Особый чеклист для любого PR, в котором есть файлы под `*/migrations/`. Работаем на проде — ошибка дорогая.

---

## Перед ревью

- [ ] Автор прогнал миграцию на **копии прод-БД**, а не на чистой
- [ ] В PR-описании указан размер затронутых таблиц (`SELECT count(*) FROM ...`)
- [ ] Оценено время выполнения на прод-размерах
- [ ] План отката (хотя бы ручной SQL) приложен

## Имя и стиль

- [ ] Имя миграции осмысленное: `0012_add_application_event_model.py`, не `0012_auto_20240422_1234.py`
- [ ] Имя отражает суть: `add_`, `remove_`, `backfill_`, `rename_`
- [ ] Нет одной огромной миграции на 500 строк — лучше несколько

## Structure vs Data

- [ ] Структурные изменения (add column, drop column, create index) и data-миграции — **в разных файлах**
- [ ] Если это data-migration — имя начинается с `backfill_`, `migrate_`, `normalize_`

## Безопасность

- [ ] Никаких `DROP COLUMN` в первой миграции изменения — сначала перестаём использовать колонку, потом отдельной миграцией удаляем
- [ ] `DROP TABLE` — только после того, как все читатели перешли на новое
- [ ] `RENAME COLUMN` в Postgres атомарен, ОК
- [ ] `RENAME TABLE` — осторожно, только если есть уверенность что никто не ходит по старому имени

## Производительность

- [ ] `CREATE INDEX` на больших таблицах — **`CONCURRENTLY`** через `RunSQL`, не через `AddIndex` (блокирует таблицу):
  ```python
  migrations.RunSQL(
      "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_foo ON app_foo(bar);",
      "DROP INDEX IF EXISTS idx_foo;"
  )
  ```
  И `atomic = False` в миграции.

- [ ] `ALTER TABLE ADD COLUMN` с `default` на большой таблице — опасно (блокирует, переписывает всю таблицу в старых Postgres). Разбить: сначала `ADD COLUMN NULL`, потом backfill, потом `SET NOT NULL`.

- [ ] Data-миграция с миллионом строк — batch-processing:
  ```python
  def forwards(apps, schema_editor):
      Model = apps.get_model("app", "Model")
      batch = []
      for obj in Model.objects.all().iterator(chunk_size=1000):
          batch.append(...)
          if len(batch) >= 1000:
              Model.objects.bulk_update(batch, fields=['x'])
              batch = []
      if batch:
          Model.objects.bulk_update(batch, fields=['x'])
  ```

## Data-migrations

- [ ] Используется `apps.get_model("app", "Model")`, **не** прямой импорт из `app.models` (иначе break в будущем)
- [ ] Миграция идемпотентна (повторный запуск не ломает)
- [ ] Миграция обрабатывает edge cases: пустая таблица, NULL-ы, странные данные
- [ ] Есть `reverse_code` либо явное `RunPython.noop` с комментарием «необратимая миграция, почему: ...»

## Обратимость

- [ ] Структурные миграции — всегда обратимы
- [ ] Data-migrations по возможности обратимы (если не сохраняем старые значения — явно помечаем)
- [ ] `python manage.py migrate app ZZZZ_previous` работает локально

## Foreign Keys

- [ ] `on_delete` задан явно
- [ ] По дефолту — `PROTECT` для важных связей
- [ ] `CASCADE` только когда семантически оправдано (удалить заявку → удалить её события — ОК)

## Переименования (особая осторожность)

- [ ] `RenameModel` / `RenameField` — **только** если ни один код больше не ссылается на старое имя
- [ ] Стратегия: в одном PR делаем alias через `db_column` / `db_table`, в следующем PR уже физический rename

## Zero-downtime

- [ ] Приложение не падает между стадией «миграция применена» и «код задеплоен»
- [ ] Это проверяется через:
  1. Миграция применена (БД имеет новое поле)
  2. Старый код работает (он не знает о новом поле — это ОК, если NOT NULL, то с default)
  3. Новый код работает

## Примеры хороших миграций

### Добавление поля безопасно
```python
# Миграция 1
migrations.AddField(
    model_name="msuser",
    name="max_chat_id",
    field=models.CharField(max_length=64, blank=True, null=True, unique=True, db_index=True),
)
```
NULL-поле, backfill не нужен, deploy без downtime.

### Удаление поля безопасно
```python
# Шаг 1: в коде перестали писать в поле, только читаем → deploy
# Шаг 2: в коде перестали читать → deploy
# Шаг 3: миграция:
migrations.RemoveField(
    model_name="...", name="...",
)
```

### Нормализация (пример для ApplicationEvent)
```python
# Миграция 1: создание ApplicationEvent
# Миграция 2: backfill из старых денормализованных полей
# Миграция 3 (в следующем релизе, после проверки): удаление старых полей
```

---

## Вопросы ревьюера к автору PR

- Какой размер затронутых таблиц?
- Сколько займёт миграция на проде? (оценка)
- Есть ли блокировка пользовательского трафика во время?
- Как откатимся если что-то пошло не так?
- Протестирована ли миграция на копии прода?
