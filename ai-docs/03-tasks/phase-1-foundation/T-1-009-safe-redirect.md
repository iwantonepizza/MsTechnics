# T-1-009. Заменить `redirect(HTTP_REFERER)` на `safe_redirect`

> **Тип:** security / bugfix
> **Приоритет:** P1
> **Оценка:** 1 час
> **Фаза:** 1
> **Статус:** done

---

## Цель

Убрать уязвимость open-redirect. Сейчас почти каждая view делает `redirect(request.META['HTTP_REFERER'])` — злоумышленник может направить пользователя на подготовленный URL, провести социнженерию с возвратом на поддельный сайт.

---

## Контекст

Найти все места:
```bash
grep -rn "HTTP_REFERER" --include="*.py" .
```

Типичный паттерн:
```python
def do_something(request):
    # ... логика ...
    return redirect(request.META.get('HTTP_REFERER', '/'))
```

Проблемы:
- `HTTP_REFERER` — под контролем клиента, может быть любым внешним URL
- В проде `DEBUG=False` Django мог пропустить проверку — зависит от `SECURE_REFERRER_POLICY`

---

## Зависимости

- **Блокируется:** нет
- **Блокирует:** T-3 (SPA использует программный роутинг, views идут в прошлое)

---

## Что нужно сделать

1. Создать утилиту `shared/http.py`:
   ```python
   from urllib.parse import urlparse

   from django.conf import settings
   from django.http import HttpRequest, HttpResponseRedirect
   from django.urls import reverse


   def safe_redirect(
       request: HttpRequest,
       fallback: str = "main_menu:index",
       *,
       fallback_is_url: bool = False,
   ) -> HttpResponseRedirect:
       """Редирект на referer, если он на нашем домене; иначе на fallback.

       Args:
           request: текущий HTTP-request.
           fallback: URL name для reverse(), либо absolute URL если fallback_is_url=True.
           fallback_is_url: если True, fallback интерпретируется как готовый URL.

       Returns:
           HttpResponseRedirect на безопасный URL.
       """
       referer = request.META.get("HTTP_REFERER", "")
       if referer and _is_safe_url(referer, request):
           return HttpResponseRedirect(referer)

       target = fallback if fallback_is_url else reverse(fallback)
       return HttpResponseRedirect(target)


   def _is_safe_url(url: str, request: HttpRequest) -> bool:
       """Проверка что URL относится к нашему хосту."""
       try:
           parsed = urlparse(url)
       except ValueError:
           return False

       # относительный URL — безопасен
       if not parsed.netloc:
           return True

       # абсолютный — должен совпадать с нашим хостом
       allowed_hosts = set(settings.ALLOWED_HOSTS)
       if request.get_host() in allowed_hosts:
           allowed_hosts.add(request.get_host())

       # поддержка wildcard "*" — разрешаем только текущий хост
       if "*" in allowed_hosts:
           return parsed.netloc == request.get_host()

       return parsed.netloc in allowed_hosts
   ```

2. Тесты `tests/shared/test_http.py`:
   ```python
   @pytest.mark.parametrize("referer,expected_ok", [
       ("/some/path", True),
       ("https://mstechnics.ru/x", True),
       ("https://evil.com/phishing", False),
       ("", False),
       ("javascript:alert(1)", False),
   ])
   def test_is_safe_url(referer, expected_ok, rf):
       request = rf.get("/", HTTP_HOST="mstechnics.ru")
       request.META["HTTP_REFERER"] = referer
       ...
   ```

3. Заменить **все** `redirect(request.META.get('HTTP_REFERER', ...))`:
   ```bash
   grep -rln "HTTP_REFERER" --include="*.py" .
   ```
   По каждому файлу:
   ```python
   # было:
   return redirect(request.META.get('HTTP_REFERER', '/'))

   # стало:
   from shared.http import safe_redirect
   return safe_redirect(request)
   ```

4. Убедиться что `DJANGO_ALLOWED_HOSTS` выставлен в prod (см. T-1-007).

---

## Критерии приёмки

- [ ] `shared/http.py` создан с `safe_redirect`
- [ ] Тесты покрывают все граничные кейсы (javascript:, data:, внешний домен, относительный, пустой)
- [ ] `git grep "HTTP_REFERER"` — пусто (кроме миграций и тестов)
- [ ] Все кнопки «Назад» в шаблонах работают как прежде (ручная проверка 5-10 переходов)
- [ ] `ruff` и `mypy` — чисто

---

## Что НЕ делать

- **НЕ возвращай** `HttpResponseRedirect(...)` напрямую с referer — используй только `safe_redirect`
- **НЕ добавляй** список «доверенных доменов» — только наш host и ALLOWED_HOSTS

---

## Известные сложности

- Если в коде есть `reverse_lazy(...)` или `redirect(some_url_name)` — оставь как есть, эти **безопасны** (generate URL, не take from user).
- В некоторых views после смены состояния делается редирект по JS с `window.location.reload()` — эти не трогаем (они другая история), только `redirect(HTTP_REFERER)`.
