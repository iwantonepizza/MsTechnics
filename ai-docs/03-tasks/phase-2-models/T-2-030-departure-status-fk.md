# T-2-030. `Departure.status: CharField` → `FK(DepartureStatus)`

> **Тип:** migration / refactor
> **Приоритет:** P2
> **Оценка:** 1.5 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Сейчас `Departure.status` — это `CharField` со свободными русскими значениями: `'Создан'`, `'Выполнен'`, `'В архиве'`, `'Удален'`. Проблемы:
- Опечатки ломают фильтрацию (`'Создан'` vs `'созданный'`)
- Русские константы в коде: `if departure.status == 'Создан': ...`
- Нельзя менять наименование (сломает старые данные)
- Нет порядка / иконок / цветов

Заменяем на FK(DepartureStatus) — по аналогии с `ApplicationStatus`.

---

## Зависимости

- **Блокируется:** T-2-014 (departure в новом месте)

---

## Целевая модель

```python
# apps/workflow/departures/models.py

class DepartureStatus(models.Model):
    name = models.CharField(max_length=40, unique=True)       # 'created', 'completed', 'archived', 'deleted'
    description = models.CharField(max_length=80)             # 'Создан', 'Выполнен', ...
    color = models.ForeignKey('core_references.Color', on_delete=models.PROTECT, null=True)
    icon = models.ForeignKey('core_references.Smile', on_delete=models.PROTECT, null=True)
    order = models.PositiveSmallIntegerField(default=0)       # порядок в UI
    is_terminal = models.BooleanField(default=False)          # archived / deleted
    
    class Meta:
        db_table = 'departure_status'
        ordering = ['order', 'id']
    
    def __str__(self):
        return self.description


class Departure(models.Model):
    # ...
    status = models.ForeignKey(
        DepartureStatus,
        on_delete=models.PROTECT,
        related_name='departures',
    )
    # ...
```

---

## Что нужно сделать

### Шаг 1. Миграция модели DepartureStatus

```python
# 00XX_create_departurestatus.py
migrations.CreateModel(
    name='DepartureStatus',
    fields=[...],  # как модель выше
    options={'db_table': 'departure_status', 'ordering': ['order', 'id']},
)
```

### Шаг 2. Data-миграция — заполнение справочника

```python
# 00XX_seed_departurestatus.py
def forwards(apps, schema_editor):
    DepartureStatus = apps.get_model('workflow_departures', 'DepartureStatus')
    
    rows = [
        ('created',   'Создан',      0, False),
        ('completed', 'Выполнен',    1, False),
        ('archived',  'В архиве',    2, True),
        ('deleted',   'Удалён',      3, True),
    ]
    for name, desc, order, terminal in rows:
        DepartureStatus.objects.get_or_create(
            name=name,
            defaults={'description': desc, 'order': order, 'is_terminal': terminal},
        )
```

### Шаг 3. Добавить `status_new_id` в Departure

```python
# 00XX_add_departure_status_new_id.py
migrations.AddField(
    model_name='departure',
    name='status_new_id',
    field=models.IntegerField(null=True, blank=True, db_index=True),
)
```

### Шаг 4. Backfill по старому CharField

```python
# 00XX_backfill_departure_status_new_id.py
def forwards(apps, schema_editor):
    Departure = apps.get_model('workflow_departures', 'Departure')
    DepartureStatus = apps.get_model('workflow_departures', 'DepartureStatus')
    
    mapping = {
        'Создан':    'created',
        'Выполнен':  'completed',
        'В архиве':  'archived',
        'Удалён':    'deleted',
        'Удален':    'deleted',  # возможные опечатки
    }
    
    name_to_id = dict(DepartureStatus.objects.values_list('name', 'id'))
    
    unmapped = []
    for d in Departure.objects.filter(status_new_id__isnull=True).iterator(chunk_size=500):
        target_name = mapping.get(d.status)
        if not target_name:
            unmapped.append(d.id)
            continue
        d.status_new_id = name_to_id[target_name]
        d.save(update_fields=['status_new_id'])
    
    if unmapped:
        # Не падаем, но логируем, пусть DBA разберётся
        import structlog
        structlog.get_logger(__name__).warning('departure_status_unmapped', ids=unmapped[:20])
```

### Шаг 5. Замена поля

```python
# 00XX_replace_departure_status.py
class Migration(migrations.Migration):
    dependencies = [('...', '00XX_backfill_departure_status_new_id')]
    operations = [
        migrations.RemoveField(model_name='departure', name='status'),
        migrations.RenameField(model_name='departure', old_name='status_new_id', new_name='status_id'),
        migrations.AddField(
            model_name='departure',
            name='status',
            field=models.ForeignKey(
                'workflow_departures.DepartureStatus',
                on_delete=models.PROTECT,
                related_name='departures',
                null=True,  # потом SET NOT NULL в отдельной миграции, когда будем уверены
            ),
        ),
    ]
```

### Шаг 6. Обновить код

Грепнуть по русским константам:
```bash
grep -rn "'Создан'\|'Выполнен'\|'В архиве'\|'Удален'" --include="*.py" --include="*.html" .
```

В шаблонах и коде:
```python
# было:
if departure.status == 'Создан':
    show_edit_buttons()

# стало:
if departure.status.name == 'created':
    show_edit_buttons()
```

Или ещё лучше — свойство:
```python
class Departure(models.Model):
    @property
    def is_created(self):
        return self.status and self.status.name == 'created'
    
    @property
    def is_archived(self):
        return self.status and self.status.name == 'archived'
```

### Шаг 7. Тесты

```python
def test_departure_status_fk_resolves(departure_factory):
    d = departure_factory(status__name='created')
    assert d.status.description == 'Создан'
    assert d.is_created is True

def test_departure_status_legacy_values_migrated(...):
    # после применения миграций все Departure имеют status_id != NULL
    from apps.workflow.departures.models import Departure
    assert not Departure.objects.filter(status__isnull=True).exists()
```

### Шаг 8. Сделать NOT NULL (финальный шаг)

Когда на проде данных нет с NULL — дополнительная миграция:
```python
migrations.AlterField(
    model_name='departure',
    name='status',
    field=models.ForeignKey('workflow_departures.DepartureStatus', on_delete=models.PROTECT, related_name='departures', null=False),
),
```

---

## Критерии приёмки

- [ ] Модель `DepartureStatus` создана с 4 записями справочника
- [ ] `Departure.status` — FK(DepartureStatus), NOT NULL
- [ ] Все записи `Departure` на проде имеют непустой `status_id`
- [ ] `grep -rn "'Создан'\|'В архиве'" --include="*.py"` — пусто в бизнес-коде
- [ ] `grep -rn "'Создан'\|'В архиве'" --include="*.html"` — только в шаблонах, через фильтры/свойства
- [ ] Шаблоны адаптированы: `{% if departure.is_archived %}` вместо `{% if departure.status == 'В архиве' %}`
- [ ] Тесты покрывают миграцию и свойства

---

## Что НЕ делать

- **НЕ сохраняй** старое поле параллельно — это смешение подходов
- **НЕ используй** английские имена в русских description (description нужен для отображения юзеру)
- **НЕ переводи** «Создан» → «Created» в UI — пользователи русскоязычные

---

## Риски

- **Unmapped статусы.** Если в проде у кого-то есть `status = 'какая-то строка'` (не в списке) — backfill не проставит ID. Проверить перед миграцией: `SELECT DISTINCT status FROM departure;`
- **Null-FK.** Если FK `null=True` — в запросах `Departure.objects.filter(status__name='created')` NULL-записи не попадают. Убедиться что backfill прошёл полностью до финальной миграции NOT NULL.
