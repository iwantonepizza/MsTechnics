# T-2-028. `Panel.application_status` — удалить поле, вычислять

> **Тип:** migration / refactor
> **Приоритет:** P1
> **Оценка:** 2 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Panel имеет поле `application_status: FK(ApplicationStatus)`, которое хранит "текущий статус активной заявки на этой панели". Это **рассинхронизация** — то же значение есть в `Application.status` у активной заявки. Два источника правды.

Типичный баг: заявка переведена в `archive_done`, но `panel.application_status` забыли обновить — панель показывает оранжевый цвет (в работе) вместо серого (нет заявок).

**Решение:** удалить поле, вычислять через property / annotate в querysets.

---

## Зависимости

- **Блокируется:** T-2-013, T-2-014
- **Блокирует:** рендеринг сетки в SPA Фазы 4

---

## Что нужно сделать

### Шаг 1. Property на Panel

`apps/directory/panels/models.py`:

```python
class Panel(models.Model):
    # ... существующие поля БЕЗ application_status ...
    
    @property
    def active_application(self):
        """Активная заявка на этой панели (не в архиве), если есть."""
        from apps.workflow.applications.models import Application
        return Application.objects.filter(
            panel=self,
        ).exclude(
            status__name__in=['archive_done', 'archive_unable']
        ).order_by('-last_update_date_time').first()
    
    @property
    def application_status(self):
        """ApplicationStatus активной заявки, или 'default' если нет."""
        app = self.active_application
        if app:
            return app.status
        
        # fallback — в старом коде это был ApplicationStatus(name='default')
        from apps.workflow.applications.models import ApplicationStatus
        return ApplicationStatus.objects.filter(name='default').first()
```

### Шаг 2. Queryset-level `.with_application_status()`

Для шаблонов и API, чтобы не делать N+1:

```python
# apps/directory/panels/managers.py

class PanelQuerySet(models.QuerySet):
    def with_application_status(self):
        """Аннотирует queryset полем `_active_application_status_name`."""
        from django.db.models import OuterRef, Subquery
        from apps.workflow.applications.models import Application
        
        active_app_status = Application.objects.filter(
            panel=OuterRef('pk'),
        ).exclude(
            status__name__in=['archive_done', 'archive_unable']
        ).order_by('-last_update_date_time').values('status__name')[:1]
        
        return self.annotate(
            _active_application_status_name=Subquery(active_app_status)
        )


class PanelManager(models.Manager.from_queryset(PanelQuerySet)):
    pass


class Panel(models.Model):
    # ...
    objects = PanelManager()
```

Использование в шаблоне (legacy):
```django
{% for panel in panels %}
  {{ panel._active_application_status_name|default:'default' }}
{% endfor %}
```

В API Фазы 3 — отдаём через сериализатор:
```python
class PanelSerializer(serializers.ModelSerializer):
    application_status = serializers.CharField(source='_active_application_status_name', default='default')
```

### Шаг 3. Миграция — удаление поля

```python
# apps/directory/panels/migrations/00XX_remove_panel_application_status.py
class Migration(migrations.Migration):
    dependencies = [('directory_panels', 'XXXX_previous')]
    operations = [
        migrations.RemoveField(model_name='panel', name='application_status'),
    ]
```

**Важно:** перед применением — убедиться, что **никто** в коде не пишет `panel.application_status = ...`:

```bash
grep -rn "application_status" --include="*.py" . | grep -v migrations | grep -v test
# Проверить каждый результат — это чтение (ок) или запись (надо исправить)
```

Все места записи (`panel.application_status = <что-то>; panel.save()`) — удалить. Чтения через property продолжат работать.

### Шаг 4. Компенсация в шаблонах

В legacy-шаблонах (`panel_info_block.html`, `central_block.html`) использование `panel.application_status.color.hex_color` — **продолжит работать** через property. Но property бьёт по БД за каждым вызовом в цикле — N+1.

Решение: во views передавать `Panel.objects.with_application_status()` и в шаблоне использовать annotated поле.

Пример legacy `zip/views.py`:
```python
# было:
panels = Panels.objects.filter(...)

# стало:
panels = Panel.objects.with_application_status().select_related(
    'display', 'condition', 'department'
).filter(...)
```

### Шаг 5. Тесты

```python
def test_panel_active_application_returns_non_archived(panels_factory, application_factory, display_factory):
    display = display_factory(rows=2, cols=2)
    cell = display.cells.first()
    panel = cell.panel
    
    # Архивная заявка
    application_factory(display=display, panel=panel, cell=cell, status__name='archive_done')
    # Активная заявка  
    active = application_factory(display=display, panel=panel, cell=cell, status__name='sent_to_service')
    
    assert panel.active_application == active
    assert panel.application_status.name == 'sent_to_service'


def test_panel_application_status_default_when_no_active(panels_factory):
    panel = panels_factory()
    # По умолчанию — "default" статус
    assert panel.application_status.name == 'default'


def test_with_application_status_annotation_works_in_queryset(panels_factory, application_factory, ...):
    # проверить что аннотация возвращает строку, не делает N+1
    from django.db import connection
    panel = panels_factory()
    application_factory(panel=panel, status__name='sent_to_control')
    
    with connection.queries_log as log:
        panels = list(Panel.objects.with_application_status())
        for p in panels:
            _ = p._active_application_status_name
    
    # В логе должно быть 1 запрос (с Subquery), не N+1
    assert len(connection.queries) == 1
```

---

## Критерии приёмки

- [ ] Поле `Panel.application_status` удалено из модели и БД
- [ ] Property `Panel.application_status` работает как fallback
- [ ] QuerySet метод `with_application_status()` возвращает annotation
- [ ] В legacy views — замена на `with_application_status()` + `select_related`
- [ ] Смоук-тест сетки панелей (`/service/<city>/<display>`): 1 запрос на рендер сетки (+1-2 на related) вместо N+1
- [ ] Regression-тесты — проходят
- [ ] `grep -n "panel.application_status =" --include="*.py" .` — пусто

---

## Что НЕ делать

- **НЕ сохраняй** поле как cached_property или column с ручным обновлением через signals — это возврат к рассинхронизации
- **НЕ меняй** логику определения "активной заявки" в этой задаче — используй существующее правило (not archive_*)
- **НЕ оставляй** legacy-signal'ы которые писали в `panel.application_status` — удалить

---

## Риски

- **Shadowing имени.** Property `application_status` может конфликтовать с полем если оно не удалено. Убедиться что миграция применена до использования.
- **N+1 в шаблонах.** Без `with_application_status()` через каждый `{{ panel.application_status }}` будет запрос. Тщательно пройтись по всем шаблонам.
