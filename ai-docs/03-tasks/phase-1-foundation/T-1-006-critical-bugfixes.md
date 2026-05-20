# T-1-006. Фиксы критических багов: registration view, signals, if Panels

> **Тип:** bugfix
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 1
> **Статус:** done

---

## Цель

Убрать три активных бага, которые любой прохожий может эксплуатировать или которые ломают работу каждый день.

---

## Контекст

### Баг 1: SEC-007 — registration view создаёт захардкоженного пользователя

Файл `user/views.py:51-56`:
```python
def registration(request):
    answer = create_user(username='izhevsk11', email=None, password='ff420qk3g')
    context = {'title': 'Меню сервис',
               answer: 'answer', }
    return render(request, 'user/registration.html', context)
```

Это ЭНДПОИНТ в роутинге, который при **любом** GET-запросе к `/user/registration/` создаёт пользователя `izhevsk11` с паролем `ff420qk3g`. Пароль в репо. Эндпоинт открытый.

### Баг 2: MDL-009 — signal сохраняет класс sender'а в CharField(40)

Файл `<app>/signals.py` (найти через `grep -rn "def.*sender.*" */signals.py`). Паттерн:
```python
@receiver(post_save)
def log_save(sender, **kwargs):
    Report.objects.create(sender=sender)  # sender — это класс модели, не строка!
```

`Report.sender` — `CharField(40)`. Django падает или усекает строку `<class 'app.models.Thing'>` до 40 символов. Иногда падает, иногда нет — интермиттент.

### Баг 3: MDL-010 — `if Panels:` вместо `if panel:`

Файл `zip/models.py` или `zip/views.py`. Паттерн:
```python
if Panels:  # Panels — это класс модели, truthy всегда
    ...
```

Проверка никогда не фолс.

---

## Зависимости

- **Блокируется:** нет. Фиксить срочно.

---

## Что нужно сделать

### Баг 1: registration view

1. **Немедленно:** переименовать `create_user(username='izhevsk11', ...)` — вынести из view.
2. Если этот юзер уже создан в проде (скорее всего) — сменить ему пароль через админку, `ff420qk3g` не использовать.
3. В `user/views.py`:
   ```python
   # удалить функцию registration
   ```
4. В `user/urls.py` — удалить маршрут к `registration`.
5. В `templates/user/registration.html` — удалить файл.
6. Если где-то есть ссылка на этот URL — найти и убрать:
   ```bash
   grep -rn "registration" --include="*.html" --include="*.py" .
   ```
7. Если нужна страница регистрации для админа — отдельная задача, делаем через Django admin или кастомную форму с `is_superuser` проверкой. В этой задаче **не добавляй**.

### Баг 2: signals

1. Найти все `signals.py`:
   ```bash
   find . -name "signals.py" -not -path "*/node_modules/*"
   ```
2. Посмотреть, где `sender` (который класс модели) сохраняется в CharField. Пример:
   ```python
   Report.objects.create(sender=sender, ...)  # неправильно
   ```
3. Исправить на:
   ```python
   Report.objects.create(sender=sender._meta.model_name, ...)  # "application"
   # или просто не передавать, если поле не нужно
   ```
4. Если поле `sender` на Report больше не нужно — увеличить до `CharField(100)` или убрать, зафиксировать миграцией. Это структурное изменение, согласовать с архитектором через комментарий в отчёте.

### Баг 3: if Panels

1. Найти все места:
   ```bash
   grep -rn "if Panels" --include="*.py" .
   grep -rn "if Panels:" --include="*.py" .
   ```
2. По каждому — разобраться что имелось в виду (`if panel:`? `if Panels.objects.exists():`?), исправить.
3. Добавить тест на каждое место — проверить что ветка `else` действительно работает.

---

## Критерии приёмки

- [ ] Эндпоинт `/user/registration/` возвращает 404 (удалён)
- [ ] Пользователь `izhevsk11` в проде — пароль сменён (проверить руками, зафиксировать в отчёте **как сделано**)
- [ ] `git grep "ff420qk3g"` — ничего не находит в проекте
- [ ] `git grep "izhevsk11"` — находит только в миграциях или данных, не в коде
- [ ] `git grep "if Panels"` — пусто
- [ ] В тестах — regression-тест на каждую исправленную условность
- [ ] В signals — сохраняется осмысленное строковое значение, а не класс

---

## Что НЕ делать

- **НЕ чини** одновременно другие баги из audit-report. Только эти три.
- **НЕ рефакторь** signal-ы «пока тут». Миниминум правок.
- **НЕ меняй** пароль пользователя через код (в миграции, в fixture). Только руками через admin.

---

## Последовательность действий

1. Смени пароль `izhevsk11` в проде **первым делом**
2. Открой PR с фиксами
3. Приложи в отчёт: скриншот админки со сменой пароля (закрывая пароль) ИЛИ запись в incident-лог
