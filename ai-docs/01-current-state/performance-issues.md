# Проблемы производительности

Прогноз: после рефакторинга модели и переезда на REST API большинство этих проблем уходит. Но пока они есть, и важно их фиксировать, чтобы:
1. Регрессии не появились;
2. При нагрузочном тесте мы знали baseline.

---

## Критические

### PERF-001. `application_report` без лимита при каждом рендере

**Файлы:** `control/views.py:55`, `monitoring/views.py:37`, `service/views.py:91`

```python
application_report = ApplicationHistoryReport.objects.order_by('-time')
```

Тащится вся история. При 10k записей:
- SQL: 150-300ms
- Serialize в Python: 500+ms
- Render в HTML: 1-2s

**Итог:** страница открывается 3-5 секунд.

**Временный фикс (фаза 1):** `[:50]`.
**Финальный фикс:** отдельный API-эндпоинт с пагинацией.

---

### PERF-002. Prefetch × 7 уровней

**Файл:** `service/views.py:40-53`

Django строит один большой SQL с JOIN'ами на все уровни:

```sql
SELECT * FROM display
LEFT JOIN cell ON ...
LEFT JOIN panel ON ...
LEFT JOIN application_status ON ...
LEFT JOIN color c1 ON ...
LEFT JOIN color c2 ON ...
LEFT JOIN condition ON ...
LEFT JOIN smile ON ...
LEFT JOIN department ON ...
WHERE display.name = ?
```

Для 30×30 экрана = 900 строк с полной декартовой массой. Трафик БД → Django = 5-10 МБ.

**Фикс:** разделить на 2-3 запроса через `prefetch_related`.

---

### PERF-003. `panel_reports = PanelHistoryReport.objects.all()` в главном меню

**Файл:** `main_menu/views.py:33`

```python
panel_reports = PanelHistoryReport.objects.select_related("panel").all().order_by('-time')
```

Без лимита. При 50k записей и 300 панелей = `select_related` тянет всё в один SELECT.

**Фикс:** `[:100]`.

---

### PERF-004. `position` как @property → итерация в Python

**Файл:** `zip/models.py:143-157`, использование: `service/views.py:62-63`

```python
cell = Cell.objects.filter(display=display)
cell = next((c for c in cell if c.position == get_position), None)
```

Тянет все ячейки экрана в Python, потом ищет.

**Фикс:** вычислять (row, col) из position_string, делать `.get(display, row, col)`.

---

### PERF-005. `free_panels` без select_related

**Файл:** `service/views.py:74`

```python
free_panels = Panels.objects.filter(department='zip', display__name=display_name)
```

В шаблоне:
```django
{% for free_panel in free_panels %}
    {{ free_panel.name }} {{ free_panel.condition.icon }}
{% endfor %}
```

`condition.icon` = отдельный SQL на каждую панель. 30 панелей = 30 SQL.

**Фикс:** `.select_related('condition__icon')`.

---

## Средние

### PERF-006. `get_display_application` = 9 отдельных `.filter(status=...)`

**Файл:** `application/utils.py:234-249`

```python
return {
    'application_sent_to_control': applications.filter(status='application_sent_to_control'),
    'application_apply_in_control': applications.filter(status='application_apply_in_control'),
    'application_sent_to_service': applications.filter(status='application_sent_to_service'),
    ...
}
```

Это **ленивые** QuerySets — сами по себе SQL не выполняют. Но в шаблоне идут `{% if applications.application_sent_to_control %}` + `{% for %}` = каждый раз по два SQL (один для `.exists()`, один для списка).

**Фикс:** один запрос + группировка в Python или в БД:

```python
from django.db.models import Count
applications_at_display.values('status__name').annotate(cnt=Count('*'))
```

---

### PERF-007. `PhotoDisplay.objects.filter(display_id=display_id)` — нет индекса

**Файл:** `zip/models.py:425-440`

```python
class PhotoDisplay(models.Model):
    display = ForeignKey(Display, ...)
    image = ImageField(...)
    uploaded_at = DateTimeField(auto_now_add=True)
```

FK даёт индекс автоматически. OK. Но:

- Нет индекса по `uploaded_at`, а сортировка идёт по `ordering = ['id']` (по id ≈ по времени, но не точно).
- При большом объёме фото (сейчас /media/photos = 3.2MB — мало, но растёт) — `list_display` в админке с сортировкой по времени будет тормозить.

---

### PERF-008. `ApplicationHistoryReport.user` — CharField, не FK

**Файл:** `application/models.py:117`

```python
user = models.CharField(max_length=40, unique=False, verbose_name='Пользователь')
```

Причина — не было нужды. Но:
1. Нельзя JOIN'ом получить полную инфу о пользователе
2. Поиск по истории «все заявки, к которым приложил руку Иван» = `filter(user__icontains='Иван')` — медленно, без индекса
3. Удаление пользователя не каскадит

**Фикс:** при миграции на `ActivityLog` поле `actor` будет FK(User).

---

### PERF-009. `allowed_city` M2M проверяется через Python

**Файл:** `service/views.py:37-38`

```python
user_cities = request.user.allowed_city.all()   # 1 SQL
user_access = any(city.name == city_name for city in user_cities)   # loop в Python
```

**Фикс:**
```python
user_access = request.user.allowed_city.filter(name=city_name).exists()   # 1 SQL с EXISTS
```

---

### PERF-010. DailyTask `check_iteration` зовёт `.save()` дважды

**Файл:** `zip/models.py:313-316`

```python
def check_iteration(self, current_datetime):
    if self.last_completed_date != current_datetime.date():
        message_delivered = self.check_status(current_datetime)  # ← внутри уже save()
        self.save()  # ← второй save()
```

Внутри `check_status` → `self.save()` 3 раза (по веткам). Плюс ещё один снаружи. На 100 задач = 400 UPDATE в минуту.

**Фикс:** один `save()` в конце `check_iteration`.

---

## Мелкие, но навязчивые

### PERF-011. Запросы в templatetags без prefetch

**Файл:** `service/templatetags/panel_tags.py:34-55`

```python
@register.simple_tag()
def qtg_get_panels(department_name, ..., user):
    user_cities = user.allowed_city.all()   # 1 SQL внутри шаблонного рендера
    queryset = Panels.objects.select_related(...).filter(
        display__city__in=user_cities
    )
    print(queryset.count(), department_name)   # 1 SQL на print!
    ...
```

- `print(queryset.count())` → SELECT COUNT(*)
- `user_cities` — новый SQL
- шаблонный таг вызывается **4 раза** подряд в шаблоне `zip.html` с разными department_name

Итого: 8+ SQL внутри рендера шаблона (минимум).

**Фикс:** вытащить в view, передать готовые querysets в context.

---

### PERF-012. `SomeModel.objects.select_related('field').get(field='value')`

Паттерн `.get(name='application_sent_to_control')` встречается **десятки раз**. Каждый — SELECT по имени из таблицы `application_status` (6 записей, пофиг). НО — это всё равно round-trip.

**Фикс:** кешировать справочники через `django-cacheops` или просто хранить `dict_of_statuses` в app-wide cache (`app_ready`).

---

### PERF-013. Все `.all()` в админке без пагинации по умолчанию

Не блокер — Django Admin сам пагинирует по 100, но:

```python
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'display', 'panel', 'status', 'last_update_date_time')
```

Без `list_select_related` → в `list_display` каждый `display/panel/status` = отдельный SQL × 100 строк = 300 SQL на открытие списка.

**Фикс:** `list_select_related = ('display', 'panel', 'status')`.

---

## Baseline для нагрузки (на будущее)

После фазы 3 (REST API) нужно замерить:

| Метрика                     | Цель      |
|-----------------------------|-----------|
| GET /api/v1/displays/       | < 100ms   |
| GET /api/v1/displays/:slug/ | < 150ms   |
| GET /api/v1/panels/?display=X | < 150ms |
| POST /api/v1/applications/  | < 200ms   |
| GET /api/v1/activity/?target=display&id=X&limit=50 | < 200ms |
| main menu page load (SPA)   | < 1s      |

Замеряем через:
- `django-silk` в dev
- `django-prometheus` + Grafana в prod
- `k6` для нагрузочных тестов
