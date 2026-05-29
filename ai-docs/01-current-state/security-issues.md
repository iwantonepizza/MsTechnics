# Критические проблемы безопасности (читать первым!)

Это не рекомендации — это то, что нужно починить **в первые часы работы над проектом**.
Если этот файл лежит в репозитории дольше 48 часов в исходном виде — кто-то прокосячил.

---

## 🔴 SEC-001. Google OAuth client_secret закоммичен в репо

**Файл:** `Config/client_secret.json`

```json
{
  "web": {
    "client_id": "320806079726-dck3103ahc67t845tlfvieffvq8ogm0u.apps.googleusercontent.com",
    "client_secret": "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",  ← УТЕКШИЙ СЕКРЕТ
    ...
  }
}
```

### Что делать **прямо сейчас**

1. В Google Cloud Console → этот проект (`ms-contol-cloud`) → OAuth credentials → **Reset secret**
2. Новый секрет положить в `.env` (переменная `GOOGLE_OAUTH_CLIENT_SECRET`) и в прод
3. Удалить `Config/client_secret.json` из индекса и из всей истории git (`git filter-repo` или BFG)
4. Добавить в `.gitignore`:
   ```
   Config/.env
   Config/client_secret.json
   Config/token.pickle
   *.pickle
   .env*
   !.env.example
   ```
5. Выпустить новый `.env.example` с пустыми/фейковыми значениями

### Почему критично

Эти ключи дают доступ на чтение Gmail аккаунта, к которому привязан проект. Утечка через git-историю = любой, у кого был доступ к репозиторию, имеет доступ к письмам.

---

## 🔴 SEC-002. SECRET_KEY не защищён

**Файл:** `MsServiceControl/settings.py:12`

```python
SECRET_KEY = os.environ.get('SECRET_KEY')
```

### Проблемы

- Если переменной нет в окружении — `SECRET_KEY = None`, Django упадёт неинформативно
- Ротация не предусмотрена
- Нет fallback'а для генерации в dev

### Решение

```python
# backend/config/settings/base.py
SECRET_KEY = env('DJANGO_SECRET_KEY')   # django-environ, падает с ясной ошибкой

# backend/config/settings/dev.py
SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-dev-only-XXXXXXXXXXXX')
```

В prod обязательно задаётся. В `.env.example`:

```
DJANGO_SECRET_KEY=replace-me-with-strong-random-50-chars
```

---

## 🔴 SEC-003. DEBUG = строка

**Файл:** `settings.py:14`

```python
DEBUG = os.environ.get('DEBUG')
```

### Проблема

`os.environ.get('DEBUG')` возвращает строку. `DEBUG="False"` **truthy**. То есть в проде, если в .env стоит `DEBUG=False` — Django всё равно в debug-режиме.

### Последствия

1. Стектрейсы наружу при ошибках
2. Debug Toolbar, если установлен (а он установлен)
3. Утечка переменных окружения, SQL-запросов
4. Отключение HTTPS-редиректов, если они настроены через условие на DEBUG

### Решение

```python
from environ import Env
env = Env()
DEBUG = env.bool('DJANGO_DEBUG', default=False)
```

---

## 🔴 SEC-004. ALLOWED_HOSTS хардкод + IP в коде

**Файл:** `settings.py:16`

```python
ALLOWED_HOSTS = ['127.0.0.1', 'www.mstechnics.ru', 'mstechnics.ru', '185.251.88.121']
# потом заменить
```

«Потом заменить» лежит полгода. IP сервера торчит в git.

### Решение

```python
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost'])
```

В `.env.example`:
```
DJANGO_ALLOWED_HOSTS=mstechnics.ru,www.mstechnics.ru
```

---

## 🔴 SEC-005. Открытый редирект

**Файл:** `application/views.py:54` и **десятки** других мест

```python
return redirect(request.META['HTTP_REFERER'])
```

### Проблемы

1. **Открытый редирект:** злоумышленник делает страницу с формой POST на наш домен с `Referer: https://evil.com`. Пользователь кликает, пост проходит, его редиректит на evil.com.
2. **500 при отсутствии реферера:** если POST пришёл от curl/postman без Referer → `KeyError`.
3. **Не работает на SPA.** При миграции на React это вообще не актуально — API возвращает JSON, фронт сам решает, куда переходить.

### Решение (в новой архитектуре проблемы нет)

API-эндпоинты возвращают `{"status": "ok", "id": N}`. Навигацию делает фронт. Но **до миграции** фронта:

```python
from django.utils.http import url_has_allowed_host_and_scheme

referer = request.META.get('HTTP_REFERER', '')
if url_has_allowed_host_and_scheme(referer, allowed_hosts=settings.ALLOWED_HOSTS):
    return redirect(referer)
return redirect('main:index')
```

---

## 🔴 SEC-006. OAUTHLIB_INSECURE_TRANSPORT = '1'

**Файл:** `mail/views.py:60`

```python
def oauth2callback(request):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Только для разработки
    ...
```

### Проблемы

1. Устанавливается **глобально в процессе Django**, остаётся для всех последующих запросов
2. Отключает проверку HTTPS на OAuth callback → MITM-атаки
3. `redirect_uri="http://localhost:8000/gmail/oauth2callback/"` — в проде **не должно** быть http
4. В проде код выполнится и снова ослабит безопасность

### Решение

В dev — ставить через переменную окружения **до** запуска Django (в `docker-compose.dev.yml`), а не внутри кода.
В прод — этой переменной вообще не должно быть.
`redirect_uri` — из settings, разный для dev/prod.

---

## 🔴 SEC-007. Пароль в коде регистрации

**Файл:** `user/views.py:52`

```python
def registration(request):
    answer = create_user(username='izhevsk11', email=None, password='ff420qk3g')
    ...
```

**Это создаёт пользователя с хардкод-паролем при каждом вызове эндпоинта `/user/registration/`.**

### Действия

1. Удалить view полностью — **сейчас любой может создать аккаунт** (или получить 500 при повторе, не проверял)
2. Регистрация делается только админом через Django Admin
3. Пароль `ff420qk3g` в истории git — считать скомпрометированным, сменить у всех, где мог быть использован

---

## 🟠 SEC-008. CSRF exempt без обоснования

**Файл:** `service/views.py:30`

```python
@csrf_exempt
@login_required
def service_main(request, city_name, display_name):
    ...
```

GET-запрос `@csrf_exempt` — не страшно, но **выставлен** без причины. В коде view используется только `request.GET`.

### Решение

Убрать `@csrf_exempt`. Если появилась причина — документировать её в докстринге.

---

## 🟠 SEC-009. `request.user.is_superuser` как единственная проверка

**Файл:** `templates/base.html:70-74`

```django
{% if request.user.is_superuser %}
    <a href="{% url 'main:mail:google_auth' %}">AUS</a>
    <a href="{% url 'main:mail:get_emails' %}">check</a>
    <a href="{% url 'admin:index' %}">Админ</a>
{% endif %}
```

При этом во view `google_auth` и `get_emails` **проверки прав нет вообще**:

```python
def google_auth(request):       # ❌ нет @login_required, нет проверки прав
    ...
def get_emails(request):        # ❌ то же
    ...
```

Любой неавторизованный пользователь может зайти в `/gmail/auth/` и пройти OAuth flow под нашим client_id.

### Решение

Добавить `@login_required` и `@user_passes_test(lambda u: u.is_superuser)` на уровне views. В новой архитектуре — `IsAdminUser` permission class на DRF ViewSet.

---

## 🟠 SEC-010. Пароль в User.password — TextField в SQL дампе (если утечёт)

Стандартные Django-пароли хешированные (PBKDF2). Но `fixtures/user.json` **вероятно** содержит хеши паролей. Эти хеши:

- Можно подбирать офлайн
- Могут быть заменены брутфорсом для слабых паролей

### Решение

- Fixtures пользователей не должны быть в репо. Только demo-юзер для dev, с пометкой «demo/demo».
- В `.gitignore` добавить `fixtures/user.json`.
- В ветке сделать `git filter-repo --invert-paths --path fixtures/user.json`.

---

## 🟠 SEC-011. JSON.parse без валидации в модалках

**Файл:** `application/views.py:147-149`

```python
def modal_change_executor(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            executors = Executor.objects.all()
            data['executors'] = executors
            return render(request, "modals/change_executor.html", data)
```

`data` прямиком идёт в шаблон. Если `data = {"title": "<script>...</script>"}` — XSS (Django автоэскейпит, но в `|safe` местах рванёт). Валидации через форму/сериалайзер нет.

### Решение

```python
class ModalChangeExecutorRequest(Serializer):
    application_id = IntegerField()

def modal_change_executor(request):
    serializer = ModalChangeExecutorRequest(data=json.loads(request.body))
    serializer.is_valid(raise_exception=True)
    ...
```

И в новой архитектуре — SPA вообще не дёргает сервер для рендера модалки.

---

## 🟡 SEC-012. `except Exception as e: messages.error(request, f"Ошибка: {e}")`

Встречается **30+ раз**. В `str(e)` может попасть стектрейс с секретами:
- `IntegrityError('could not connect to server: postgres://user:PASSWORD@host/db')`
- `OperationalError('FATAL: password authentication failed for user "postgres"')`

### Решение

```python
try:
    do_stuff()
except ExpectedError as e:
    messages.error(request, "Не удалось сделать X")
    logger.exception("domain-specific error", user=request.user.id)
```

Пользователь видит generic-сообщение. Логи — у админа.

---

## 🟡 SEC-013. SQL injection риск? — нет, но есть другое

Django ORM защищает. Но!

**Файл:** `main/Db/orm_query.py:22` → `if Panels:` вместо `if panel:`. Это не SQLi, но это баг, который «работает случайно». При рефакторинге рискует сломаться логика.

---

## 🟡 SEC-014. CORS не настроен

Нет `django-cors-headers`. Когда поднимется React SPA на `localhost:5173` в dev — запросы к `localhost:8000` упадут по CORS.

### Решение

Фаза 3. Добавить `django-cors-headers`, настроить `CORS_ALLOWED_ORIGINS` через env. В prod — тот же домен, нет проблем.

---

## 🟡 SEC-015. Cookies без `Secure` / `HttpOnly` / `SameSite`

В `settings.py` не выставлены:

- `SESSION_COOKIE_SECURE = True`
- `SESSION_COOKIE_HTTPONLY = True`
- `SESSION_COOKIE_SAMESITE = 'Lax'`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_SSL_REDIRECT = True`
- `SECURE_HSTS_SECONDS = 31536000`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`

В prod.py всё выше должно быть `True`.

---

## Приоритеты

| Приоритет | Issue    | Задача в плане              |
|-----------|----------|-----------------------------|
| СРОЧНО    | SEC-001  | T-0001 (до всего остального)|
| P0        | SEC-002, 003, 004, 007 | Фаза 1, T-001..T-005|
| P0        | SEC-005  | Фаза 3 (вместе с миграцией на API)|
| P1        | SEC-006, 008, 009, 010 | Фаза 1-2  |
| P2        | SEC-011, 012 | Фаза 2-3 (с переездом на DRF)|
| P2        | SEC-013 | При рефакторинге orm_query |
| P2        | SEC-014, 015 | Фаза 4 (прод-деплой) |

---

## SEC-016. Прод по HTTP ломает refresh-cookie и вынуждает ослаблять auth

**Инцидент:** `ai-docs/08-reports/incident-2026-05-29-auth-sse-hotfix.md`

### Что выявлено

На проде `2026-05-29` площадка работала как `http://45.91.8.95` без HTTPS termination.
SPA-auth хранит refresh token в cookie. Для безопасного prod-режима cookie должна быть `Secure`, но по HTTP браузер такую cookie не отправляет обратно.

Получается развилка:

- `Secure=True` -> refresh не работает, пользователь вылетает после истечения access token
- `Secure=False` -> сайт работает, но refresh cookie передаётся по незашифрованному HTTP

Это не баг конкретного view, а инфраструктурная проблема prod-cutover.

### Временная мера

Для восстановления работоспособности был введён hotfix:

```env
AUTH_COOKIE_SECURE=False
```

### Что нужно сделать

1. Поднять HTTPS на Nginx.
2. Перевести пользователей на доменное имя, а не на прямой IP.
3. После включения TLS вернуть `AUTH_COOKIE_SECURE=True`.
4. Зафиксировать это в финальном prod runbook.

### Приоритет

P0 для infra/prod.
