# T-1-011. Скрыть архивные заявки из главного меню и дашбордов

> **Тип:** feature / bugfix
> **Приоритет:** P2
> **Оценка:** 1 час
> **Фаза:** 1
> **Статус:** done
> **User task:** #7

---

## Цель

Задача владельца #7. Архивные заявки (`archive_done`, `archive_unable`) не должны попадать в сводки главного меню и виджеты отделов — только во вкладку «Архив».

---

## Контекст

В `application/models.py` есть `ApplicationManager`:
```python
class ApplicationManager(models.Manager):
    def all_new(self):
        return self.exclude(status__name__in=['archive_done', 'archive_unable'])
```

Но в некоторых views используется просто `.all()` вместо `.all_new()`. Нужно пройтись.

Найти:
```bash
grep -rn "Application.objects\." --include="*.py" .
grep -rn "application_set\." --include="*.py" .
```

---

## Зависимости

- **Блокируется:** нет

---

## Что нужно сделать

1. Для каждого места вызова `Application.objects.all()` или `.filter()` без статус-фильтра — решить:
   - **Это список для отдела / главного меню / дашборда?** → заменить на `.all_new()` (исключая архив)
   - **Это специально для архивной вкладки?** → оставить как есть
   - **Это для админки или отчёта?** → оставить

2. Типичные места:

   - `main_menu/views.py`:
     ```python
     # все три отдела
     applications = Application.objects.all_new().filter(status__name='apply_in_control')
     service_applications = Application.objects.all_new().filter(status__name__in=['sent_to_service', 'work_in_service'])
     ```

   - `control/views.py`, `service/views.py`, `monitoring/views.py`:
     - Во views для отдельных вкладок (archive / application_history) — оставить `.all()`
     - Для главного списка, который показывается «по умолчанию» — использовать `.all_new()`

   - `application/templatetags/` если есть — аналогично.

3. Проверить что вкладка «Архив» продолжает работать — она должна использовать:
   ```python
   archive = Application.objects.filter(status__name__in=['archive_done', 'archive_unable'])
   ```

4. Добавить regression-тесты:
   ```python
   def test_menu_hides_archived_applications(client, user_with_all_permissions):
       ApplicationFactory(status__name='sent_to_control')
       ApplicationFactory(status__name='archive_done')
       
       response = client.get(reverse('main_menu:index'))
       
       # Only non-archived application in context
       assert len(response.context['applications']) == 1
   ```

---

## Критерии приёмки

- [ ] В главном меню (`/menu`) не видно архивных заявок
- [ ] В дашбордах отделов (без явного перехода в «Архив») не видно архивных
- [ ] Во вкладке «Архив» всё по-прежнему работает
- [ ] Во вкладке «Все» (`application_box_chosen='all_application'`) — поведение не меняется (видно ВСЁ)
- [ ] Regression-тесты на каждый затронутый view
- [ ] Ручная проверка: создать заявку, довести до архива, убедиться что она не всплывает в дашбордах

---

## Что НЕ делать

- **НЕ удаляй** `.all()` из `ApplicationManager` — он нужен для админки
- **НЕ меняй** поведение вкладки «Все» — это запасной режим увидеть абсолютно всё

---

## Уточнение к задаче владельца

В задаче владельца #7 имеется в виду:
> «Не показывать в меню и в менюхах отделов архивные заявки»

То есть:
- «Меню» = `/menu` (главное) — **скрыть** архив ✅
- «Менюхи отделов» = `/control`, `/service`, и т.п. на уровне выбора города — **скрыть** архив (если там есть список заявок, как в control) ✅
- Внутри конкретного экрана `/service/izhevsk/display-1` — **оставить** вкладку «Архив», чтобы был доступ

Уточнение: «Все» вкладка по-прежнему показывает всё, включая архив — это сознательное действие пользователя.
