# Incident 2026-05-29. Auth Refresh + SSE Hotfix

> **Приоритет:** P0
> **Автор:** GPT-5 Codex
> **Дата:** 2026-05-29
> **Статус:** mitigated

---

## Что произошло

Прод по адресу `http://45.91.8.95` начал выбрасывать пользователей из SPA после истечения access token.
Во фронте это выглядело как:

- `GET /api/v1/me` → `401 Unauthorized`
- `POST /api/v1/auth/refresh/` → `401 Unauthorized`
- `GET /api/v1/events/stream?...` → `406 Not Acceptable`

Итог для пользователя: приложение открывалось, но после протухания access token не могло обновить сессию, а SSE-клиент уходил в постоянные ошибки переподключения.

---

## Корневая причина

Проблема состояла из двух независимых дефектов.

1. Refresh cookie ставилась с `Secure`, если `DEBUG=False`.
Прод работал по обычному `HTTP`, без TLS termination, поэтому браузер не отправлял refresh cookie обратно на `/api/v1/auth/refresh/`.
Пока access token был ещё жив, сайт казался рабочим. Когда access token истекал, refresh переставал работать, и SPA получала `401`.

2. SSE endpoint не был зарегистрирован как `text/event-stream` renderer в DRF.
Из-за этого запросы `EventSource` с `Accept: text/event-stream` упирались в DRF content negotiation и получали `406 Not Acceptable`.

---

## Почему раньше работало

- До истечения access token пользователь мог работать на уже выданном access token, поэтому дефект с refresh был скрыт.
- Если логин был выполнен недавно, падение начиналось не сразу, а через срок жизни access token.
- SSE-дефект мог быть незаметен как “шумная ошибка в консоли”, если пользователь в этот момент не зависел от realtime-обновлений.
- Системно это проявилось после прод-сборки, где `DEBUG=False`, но HTTPS на площадке `45.91.8.95` так и не был включён.

То есть не “что-то внезапно сломалось в JWT”, а накопилось несоответствие между прод-конфигурацией cookie и фактическим транспортом `HTTP`.

---

## Что сделано

- В `project_config.settings` добавлен явный флаг `AUTH_COOKIE_SECURE`.
- В auth views refresh cookie переведена с логики `secure=not DEBUG` на `secure=settings.AUTH_COOKIE_SECURE`.
- В `.env.example` добавлен `AUTH_COOKIE_SECURE=True`.
- Для SSE добавлен DRF renderer `text/event-stream`.
- Добавлены регрессионные тесты:
  - login умеет отключать `Secure` для refresh cookie через settings
  - SSE endpoint больше не отвечает `406` только из-за `Accept: text/event-stream`

---

## Прод-действия

- Изменения закоммичены и отправлены в `origin/main`, commit `2d719f2`.
- На сервере `/opt/mstechnics` подтянут этот commit.
- В `Config/.env` на проде выставлено `AUTH_COOKIE_SECURE=False`, потому что текущая площадка работает по `HTTP`.
- Контейнер `mstechnics-web-1` перезапущен с обновлёнными Python-файлами.

Follow-up того же дня:

- при разборе повторного `500` на `POST /api/v1/auth/login/` выяснилось, что контейнер `mstechnics-db-1` находился в состоянии `Created`, а не `Up`
- из-за этого backend падал в `django.db.utils.OperationalError: [Errno -3] Temporary failure in name resolution` при любой попытке обратиться к PostgreSQL по хосту `db`
- контейнер `db` был поднят вручную, после чего `web` был пересоздан через `docker compose up -d web`
- после восстановления БД login endpoint вернулся к штатному поведению: `401 invalid_credentials` на неверный пароль вместо `500`

Полная пересборка через `docker compose build web` на сервере упиралась в `BuildKit DeadlineExceeded`, поэтому для аварийного восстановления применён прямой hotfix контейнера после `git pull`.

---

## Тесты

- Новых файлов с тестами: 0
- Добавлено тестов: 2
- Что покрыто:
  - конфигурация refresh cookie
  - content negotiation SSE endpoint
- Локально зелёные:
  - `.\.venv\Scripts\python.exe -m pytest apps/interface/tests/test_auth.py -q`
  - `.\.venv\Scripts\python.exe -m pytest apps/interface/tests/test_security.py -q`

---

## Миграции

N/A

---

## Нагрузка / производительность

N/A

---

## Дальнейшие шаги

- Поднять HTTPS termination на Nginx и перевести прод с IP на домен.
- После этого вернуть `AUTH_COOKIE_SECURE=True`.
- Убрать зависимость безопасности cookie от `DEBUG`.
- Нормализовать прод-деплой: hotfix через `docker cp` допустим только как аварийная мера, не как штатный процесс.

---

## Вывод

Инцидент был вызван не одной ошибкой, а несовпадением прод-среды и ожиданий кода:
код JWT-auth был написан под HTTPS, а площадка реально работала по HTTP; SSE endpoint был реализован как streaming response, но не был доведён до корректной интеграции с DRF negotiation.
