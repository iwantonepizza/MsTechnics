# T-1-010. Ограничить querysets в reports до 50 записей

> **Тип:** performance / bugfix
> **Приоритет:** P2
> **Оценка:** 0.5 часа
> **Фаза:** 1
> **Статус:** done

---

## Цель

Убрать потенциальную OOM / медленный запрос от querysets без LIMIT.

---

## Контекст

В `main_menu/views.py` (и других) есть:
```python
panel_reports = HistoryReportPanel.objects.all().order_by('-time')
# передаётся в template и цикл {% for %}
```

Если таблица `HistoryReportPanel` распухла до 100к+ записей — страница будет грузиться минутами и сожрёт память.

---

## Зависимости

- **Блокируется:** нет
- **Блокирует:** нет (но закроет PRF-004 из performance-issues.md)

---

## Что нужно сделать

1. Найти все report-querysets без LIMIT:
   ```bash
   grep -rn "\.order_by" --include="*.py" main_menu main application control monitoring service zip departure
   ```

2. По каждому — если передаётся в template без пагинации:
   ```python
   # было:
   panel_reports = HistoryReportPanel.objects.all().order_by('-time')

   # стало:
   panel_reports = HistoryReportPanel.objects.all().order_by('-time')[:50]
   ```

3. Дополнительно: `.select_related('user', 'panel__display')` где применимо (для того же `panel_reports`).

4. Проверить и `applications.all_new` / `applications.all` — убедиться что также обрезаются. В `ApplicationManager` (в `application/models.py`) добавить `.order_by('-last_update_date_time')`.

---

## Критерии приёмки

- [ ] Все query, результат которых идёт в `{% for %}` в template — ограничены `[:50]` (или `[:N]` с явным комментарием почему именно N)
- [ ] `select_related` добавлен, где очевидно нужно (проверить через Django Debug Toolbar или `connection.queries` после)
- [ ] Ручная проверка 3-4 основных страниц (главное меню, service, zip) — открываются быстро, запросов не больше 20

---

## Что НЕ делать

- **НЕ добавляй** пагинацию в этой задаче — это для Фазы 3, в SPA
- **НЕ переписывай** queryset'ы на raw SQL
- **НЕ добавляй** кэш в этой задаче — отдельная задача

---

## Диагностика

Для измерения — в dev-окружении установить `django-debug-toolbar` (в `pyproject.toml dev extra`), открыть страницу, посмотреть «SQL» панель. Должно быть < 20 запросов на страницу, каждый < 100ms.
