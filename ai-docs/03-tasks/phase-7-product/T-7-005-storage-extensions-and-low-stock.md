# T-7-005. Storage: PowerBlocks + Connectors + low_stock_threshold

> **Тип задачи:** backend (модели + миграции) + frontend (low-stock highlight)
> **Приоритет:** P2 (открывает Z3, Z4 от владельца)
> **Оценка:** 2-3 часа backend + 1.5 frontend
> **Фаза:** 7
> **Статус:** review (раньше blocked был на ответе про threshold — закрыт в раунде 2026-05-17)
> **Исполнитель:** GPT-5 Codex

---

## Цель

Закрыть Z3 + Z4 владельца:
- **Z3:** «в колонке расходников показывать ламели, провода, **блоки питания, коннекторы**».
- **Z4:** «когда расходник заканчивается (count < N) — **подсвечивать красным**».

Сейчас в `apps/directory/storage/` есть модели `Wires`, `Hubs`, `Lamels`. Нужно добавить `PowerBlocks` (блоки питания) и `Connectors` (коннекторы) + всем 5 моделям добавить `low_stock_threshold` (default 3, владелец 2026-05-17).

---

## Контекст

Из owner-answers-2026-05-13 + раунд 2026-05-17:

| Поле | Значение |
|---|---|
| Z3 расходники | Ламели, провода, **блоки питания, коннекторы** + всё из текущей версии |
| Z4 порог | **3** (default) |
| Z5 кто меняет | Админ; админ может выдать `extra_permission='can_edit_zip_counts'` (T-7-003) |

Текущие модели — `apps/directory/storage/models.py`:

```python
class Wires(models.Model):
    name = CharField(20, unique=True)
    description = CharField(100, blank=True, null=True)
    count = PositiveIntegerField(default=0, validators=[validate_positive])
    photo = ImageField('photos/', blank=True, null=True)

class Hubs(...): ...   # такая же
class Lamels(...): ...  # такая же
```

Видно, что **3 модели почти идентичны** — это классический антипаттерн дублирования. Идеально было бы свернуть в одну `StorageItem(category=...)`. Но это **BC-breaking** (изменит endpoints `/api/v1/storage/{wires,hubs,lamels}/`, фронт, фикстуры). **Не делаем сейчас**, оставляем как 5 отдельных моделей, follow-up задача `T-7-005-followup-consolidate-storage` после prod stable.

---

## Зависимости

- **Блокируется:** ничем.
- **Блокирует:** T-7-033 (DnD ZIP колонок), T-7-034 (low-stock highlight UI), T-7-035 (создать панель через ZIP — может ссылаться на новые типы).

---

## Что нужно сделать

### Backend

**1. Добавить модели `PowerBlocks` и `Connectors`** в `apps/directory/storage/models.py`:

```python
class PowerBlocks(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='Имя')
    description = models.CharField(max_length=100, blank=True, null=True)
    count = models.PositiveIntegerField(default=0, validators=[validate_positive])
    low_stock_threshold = models.PositiveIntegerField(default=3, verbose_name='Порог низкого остатка')
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)

    class Meta:
        db_table = 'power_blocks_zip'
        verbose_name = 'Блок питания'
        verbose_name_plural = 'Блоки питания'
        ordering = ['id']

    def __str__(self):
        return self.name

class Connectors(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name='Имя')
    description = models.CharField(max_length=100, blank=True, null=True)
    count = models.PositiveIntegerField(default=0, validators=[validate_positive])
    low_stock_threshold = models.PositiveIntegerField(default=3, verbose_name='Порог низкого остатка')
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)

    class Meta:
        db_table = 'connectors_zip'
        verbose_name = 'Коннектор'
        verbose_name_plural = 'Коннекторы'
        ordering = ['id']

    def __str__(self):
        return self.name
```

**2. Добавить `low_stock_threshold` на существующие модели** (`Wires`, `Hubs`, `Lamels`):

```python
low_stock_threshold = models.PositiveIntegerField(default=3, verbose_name='Порог низкого остатка')
```

**3. Миграции:**

```python
# apps/directory/storage/migrations/000N_add_powerblocks_connectors_threshold.py
operations = [
    migrations.AddField('Wires', 'low_stock_threshold', models.PositiveIntegerField(default=3)),
    migrations.AddField('Hubs', 'low_stock_threshold', models.PositiveIntegerField(default=3)),
    migrations.AddField('Lamels', 'low_stock_threshold', models.PositiveIntegerField(default=3)),
    migrations.CreateModel('PowerBlocks', ...),
    migrations.CreateModel('Connectors', ...),
]
```

**4. API endpoints** в `apps/interface/api/v1/storage/`:

Добавить ViewSet для `PowerBlocks` и `Connectors` по образцу существующих `WiresViewSet`/`HubsViewSet`. Подключить в `urls.py`:

```
GET    /api/v1/storage/power-blocks/
POST   /api/v1/storage/power-blocks/         (только админ или с `can_edit_zip_counts`)
PATCH  /api/v1/storage/power-blocks/{id}/    (тот же scope)
DELETE /api/v1/storage/power-blocks/{id}/    (только админ)

GET    /api/v1/storage/connectors/
... аналогично
```

**Serializer** включает `is_low_stock` computed-поле:

```python
class WiresSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = Wires
        fields = ['id', 'name', 'description', 'count', 'low_stock_threshold', 'is_low_stock', 'photo']

    def get_is_low_stock(self, obj):
        return obj.count < obj.low_stock_threshold
```

Аналогично для остальных 4 моделей.

**5. Admin:**

Зарегистрировать `PowerBlocks`, `Connectors` в `apps/directory/storage/admin.py` с list_display, list_editable для `count` и `low_stock_threshold`. Добавить **list_filter `is_low_stock` через annotate** (опционально).

**6. Тесты:**

- `Wires`/`Hubs`/`Lamels` после миграции имеют `low_stock_threshold=3` для существующих записей.
- `PowerBlocks`/`Connectors` создаются.
- API возвращает `is_low_stock=true` когда `count < threshold`.
- Permission: юзер без admin/без `can_edit_zip_counts` получает 403 на PATCH `count`.

**7. OpenAPI schema** обновить (`make api-schema && make fe-types`).

### Frontend

**1. TypeScript types** регенерируются автоматически после `fe-types`.

**2. ZipPage** в `frontend/src/pages/zip/`:
- Добавить колонки «Блоки питания» и «Коннекторы» (или подкатегории в существующей секции «Расходники» — на усмотрение T-7-033).
- Низкий остаток — **красный border + красный текст count** на карточке расходника:

```tsx
<div
  className={cn(
    "rounded border p-3",
    item.is_low_stock ? "border-danger text-danger" : "border-border-1"
  )}
>
  <div className="font-display">{item.name}</div>
  <div className="text-3xl font-bold">{item.count}</div>
  {item.is_low_stock && (
    <div className="text-xs mt-1">Меньше {item.low_stock_threshold}</div>
  )}
</div>
```

`danger` — это `--danger` CSS-var из T-7-002 tokens. Не подгоняем хардкодом hex.

**3. Tests:**
- Snapshot: low-stock карточка → border-danger.
- Mock API возвращает `is_low_stock=true` → UI меняет class.

---

## Критерии приёмки

- [ ] Модели `PowerBlocks` и `Connectors` созданы, миграции применяются на чистой БД и на копии прод-БД.
- [ ] `low_stock_threshold` (default=3) добавлено на все 5 моделей.
- [ ] API endpoints `/storage/power-blocks/`, `/storage/connectors/` работают.
- [ ] `is_low_stock` computed корректно в serializer.
- [ ] Permission: GET доступен всем authenticated; PATCH/POST — admin или `can_edit_zip_counts`.
- [ ] Admin отображает + позволяет редактировать count/threshold.
- [ ] Frontend ZIP page показывает новые типы.
- [ ] Карточка с `is_low_stock` подсвечена красным.
- [ ] OpenAPI schema + TS types сгенерированы.
- [ ] pytest и vitest зелёные.
- [ ] Schema diff на копии прод-БД — только новые таблицы + новое поле в существующих.
- [ ] Отчёт `08-reports/T-7-005.md`.

---

## Что НЕ делать

- **Не консолидировать** 5 моделей в одну `StorageItem(category=...)`. BC-breaking, отдельная задача после prod stable.
- Не делать `low_stock_threshold` глобальной настройкой через `SiteConfig` — оно на каждой модели per-item, владелец явно сказал «можно настраивать».
- Не делать auto-notification при low-stock в этой задаче. Это отдельная feature (T-7-005-followup-notify-low-stock), требует решения «кому слать» и «как часто».
- Не делать историю изменений count'ов через ActivityLog здесь. Если потребуется — follow-up.

---

## Вопросы для архитектора

- [ ] Photo upload для PowerBlocks/Connectors — обязательно или опционально? — **Ответ:** опционально (как у Wires/Hubs/Lamels).
- [ ] Низкий остаток — нужен ли badge с числом «осталось N единиц до порога»? — **Ответ:** нет, достаточно цвета + подписи «Меньше {threshold}» под count'ом.

---

## Отчёт по выполнению

- Код, миграция, API, frontend и целевые тесты выполнены.
- Отчёт: `ai-docs/08-reports/T-7-005.md`
- Ограничения проверки:
  - не было локальной копии prod-БД для schema diff / migrate smoke;
  - глобальный `frontend/tsc --noEmit` падает на существующих ошибках `react-hook-form` вне скоупа `T-7-005`.
