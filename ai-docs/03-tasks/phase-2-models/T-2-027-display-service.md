# T-2-027. Вынести `Display.save()` в `DisplayService.create()`

> **Тип:** refactor
> **Приоритет:** P1
> **Оценка:** 2 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Сейчас `Display.save()` в одном вызове:
1. Создаёт Display
2. Создаёт Cells bulk
3. Создаёт Panels bulk
4. Назначает Panel к каждой Cell
5. Пишет History records

Это **нарушение Single Responsibility**: save() должен только сохранять. Кроме того — side effects в save() ломают:
- Unit-тесты (нельзя создать Display без каскада)
- Миграции (при создании через `apps.get_model(...).objects.create()` — эти side effects не срабатывают, данные неконсистентны)
- Сценарии "создать пустой Display через admin" — не работают без хаков

---

## Зависимости

- **Блокируется:** T-2-013 (Display в новом месте)
- **Блокирует:** None, но рекомендуется до публичного API

---

## Целевое решение

Вынести логику в сервис `DisplayService.create_with_layout()`.

### Шаг 1. `apps/directory/displays/services.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone
import structlog

from apps.activity.services import activity_logger
from apps.directory.displays.models import Display, Cell
from apps.directory.panels.models import Panel, Department

logger = structlog.get_logger(__name__)


@dataclass
class DisplayLayoutSpec:
    name: str
    city_id: int
    rows: int
    cols: int
    description: str = ''
    slug: str = ''
    extra_panels: int = 10


class DisplayService:
    """Сервис для сложных операций с Display (создание с layout, удаление с каскадом)."""
    
    def create_with_layout(
        self,
        spec: DisplayLayoutSpec,
        actor=None,
    ) -> Display:
        """Создать Display + все его Cell + начальный набор Panel + заполнить ячейки.
        
        Эквивалент legacy Display.save() для нового объекта.
        """
        if spec.rows < 1 or spec.cols < 1:
            raise ValueError('rows и cols должны быть >= 1')
        
        with transaction.atomic():
            # 1. Display
            display = Display.objects.create(
                name=spec.name,
                city_id=spec.city_id,
                rows=spec.rows,
                cols=spec.cols,
                description=spec.description,
                slug=spec.slug or spec.name,
            )
            
            # 2. Cells
            cells = [
                Cell(display=display, row=r, col=c)
                for r in range(1, spec.rows + 1)
                for c in range(1, spec.cols + 1)
            ]
            Cell.objects.bulk_create(cells)
            
            # 3. Panels
            total_panels = len(cells) + spec.extra_panels
            monitor_dept = Department.objects.get(name='monitor')
            panels = [
                Panel(
                    name=f'{spec.name}-{i + 1}',
                    display=display,
                    comment='Создана автоматически с экраном',
                    department=monitor_dept,
                )
                for i in range(total_panels)
            ]
            Panel.objects.bulk_create(panels)
            
            # 4. Назначить панели ячейкам
            created_cells = list(Cell.objects.filter(display=display).order_by('id'))
            created_panels = list(Panel.objects.filter(display=display).order_by('id'))
            
            for cell, panel in zip(created_cells, created_panels):
                cell.panel = panel
            
            Cell.objects.bulk_update(created_cells, ['panel'])
            
            # 5. Лог (через ActivityLog, не через старые HistoryReport)
            def _after_commit():
                for cell, panel in zip(created_cells, created_panels):
                    activity_logger.log(
                        event_type='display.panel_installed',
                        target=display,
                        actor=actor,
                        description=f'⬇️ {panel.name} → {cell.position}',
                        comment='Установлена автоматически при создании экрана',
                        payload={'cell_id': cell.id, 'panel_name': panel.name},
                    )
                activity_logger.log(
                    event_type='display.created',
                    target=display,
                    actor=actor,
                    description=f'Создан экран {display.name} ({spec.rows}×{spec.cols})',
                    payload={'rows': spec.rows, 'cols': spec.cols},
                )
            
            transaction.on_commit(_after_commit)
            
            logger.info('display_created_with_layout',
                        display_id=display.id,
                        cells=len(cells),
                        panels=len(panels),
                        actor=getattr(actor, 'username', None))
        
        return display


display_service = DisplayService()
```

### Шаг 2. Упростить `Display.save()`

```python
class Display(models.Model):
    # ... поля ...
    
    # save() становится ДЕФОЛТНЫМ Django-поведением (удалить override)
    # Если кто-то вызовет Display.objects.create(name=...) — просто сохранит Display без Cells/Panels
    
    class Meta:
        db_table = 'display'
        # ...
```

### Шаг 3. Обновить админ

Админка `DisplayAdmin.save_model()`:
```python
@admin.register(Display)
class DisplayAdmin(admin.ModelAdmin):
    # ...
    
    def save_model(self, request, obj, form, change):
        if change:
            # Обновление — стандартно
            super().save_model(request, obj, form, change)
        else:
            # Создание — через сервис
            from apps.directory.displays.services import display_service, DisplayLayoutSpec
            display_service.create_with_layout(
                spec=DisplayLayoutSpec(
                    name=obj.name,
                    city_id=obj.city_id,
                    rows=obj.rows,
                    cols=obj.cols,
                    description=obj.description,
                    slug=obj.slug,
                    extra_panels=getattr(obj, '_extra_panels', 10),
                ),
                actor=request.user,
            )
            # NB: obj после create_with_layout — не тот же объект. Для admin это норм (он не переиспользуется).
```

### Шаг 4. Обновить fixture / management commands

Если где-то было:
```python
Display.objects.create(name='X', city=c, rows=10, cols=10)
```
и ожидалось что cells создадутся — заменить на:
```python
from apps.directory.displays.services import display_service, DisplayLayoutSpec
display_service.create_with_layout(spec=DisplayLayoutSpec(name='X', city_id=c.id, rows=10, cols=10))
```

### Шаг 5. Фабрика обновляется

`zip/tests/factories.py`:
```python
class DisplayFactory(DjangoModelFactory):
    """Создаёт Display БЕЗ cells/panels. Для интеграции используй DisplayWithLayoutFactory."""
    class Meta:
        model = Display
    
    name = factory.Sequence(lambda n: f'display-{n}')
    city = factory.SubFactory(CityFactory)
    rows = 0
    cols = 0


class DisplayWithLayoutFactory:
    """Не DjangoModelFactory, а wrapper над сервисом."""
    
    @staticmethod
    def create(rows=3, cols=3, city=None, **kwargs):
        from apps.directory.displays.services import display_service, DisplayLayoutSpec
        city = city or CityFactory()
        return display_service.create_with_layout(
            spec=DisplayLayoutSpec(
                name=f'display-{rows}x{cols}-{fuzzy_suffix()}',
                city_id=city.id,
                rows=rows, cols=cols,
                extra_panels=kwargs.get('extra_panels', 2),
            ),
        )
```

---

## Критерии приёмки

- [ ] `DisplayService.create_with_layout(spec, actor)` работает, создаёт Display + Cells + Panels
- [ ] `Display.save()` — без side-effects (стандартное Django-поведение)
- [ ] Admin при создании через UI работает
- [ ] Regression-тест `test_display_save_creates_cells_equal_rows_times_cols` из T-2-003 — **меняется** (теперь через сервис)
- [ ] Unit-тесты на `DisplayService` покрывают:
  - Успешное создание
  - `rows=0` или `cols=0` → ValueError
  - extra_panels=0
  - Проверка что история пишется в ActivityLog (не в старые HistoryReport)
- [ ] `python manage.py check` — чисто
- [ ] Ручной smoke: в админке создать новый Display — всё работает

---

## Что НЕ делать

- **НЕ сохраняй** старый код `Display.save()` как backup-проверку — тесты покроют
- **НЕ добавляй** retry/loop — идемпотентность сервиса не нужна (Display.name unique)
- **НЕ храни** state в сервисе — он stateless

---

## Риски

- **Data-migrations могут зависеть** от поведения старого `Display.save()`. Проверить все migrations, если есть `Display.objects.create(...)` — они могли ожидать каскада. Миграции редко создают Display, но проверить.
- **Ручной тест в админке важен** — сервисный слой может сломать форму если Django-форма не ожидает.
