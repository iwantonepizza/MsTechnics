# Observability Runbook

Дата: 2026-05-13

Цель: поднять минимально достаточную observability-обвязку вокруг MsTechnics до и сразу после prod-cutover.

---

## 1. Что входит в стек

- `django-prometheus` в самом Django runtime
- endpoint `/metrics`
- custom metrics:
  - `mstechnics_notification_delivery_total`
  - `mstechnics_notification_all_channels_failed_total`
  - `mstechnics_sse_connections_active`
- `prometheus` в `docker-compose.yml`
- `grafana` в `docker-compose.yml`
- provisioning datasource + dashboard из `infra/grafana`
- sample alert rules из `infra/prometheus/alerts/mstechnics.rules.yml`

---

## 2. Зависимости

В runtime добавлен `django-prometheus`.

По данным официальной страницы PyPI, актуальный stable release на момент проверки — `2.4.1` от `2025-06-25`, пакет опубликован проектом `django-commons` и подходит для современного Django 5.1 stack. Источник: PyPI `django-prometheus` 2.4.1.

---

## 3. Как поднять локально

```bash
docker compose up -d web redis prometheus grafana
```

После старта:

- Django metrics: `http://127.0.0.1:8000/metrics`
- Prometheus UI: `http://127.0.0.1:9090`
- Grafana UI: `http://127.0.0.1:3001`

Grafana defaults в compose:

- user: `admin`
- password: `admin`

На проде этот пароль нужно заменить через env/secret management.

---

## 4. Что смотреть в Grafana

Dashboard: `MsTechnics Overview`

Панели:

1. `Request Rate`
   Показывает общий request throughput по HTTP method.

2. `5xx Error Ratio`
   Доля server-side ошибок относительно общего объёма ответов.

3. `p95 Latency by View`
   Медленные endpoint'ы по p95 latency.

4. `Notification Delivery Rate`
   Доставка уведомлений по каналам и статусам.

5. `All Channels Failed (15m)`
   Количество ситуаций, где Telegram/MAX/email все провалились.

6. `Active SSE Connections`
   Текущее число открытых SSE-подключений.

---

## 5. Alerts

В Prometheus добавлены sample rules:

- `MsTechnicsNotificationAllChannelsFailed`
- `MsTechnicsHigh5xxRate`
- `MsTechnicsHighLatencyP95`

Это только правила оценки. Для реальной доставки alert'ов владельцу нужен следующий operational шаг:

- либо поднять Alertmanager,
- либо настроить alerting уже внутри Grafana,
- и связать канал доставки с TG/email.

В рамках `T-6-003` repo-side правила подготовлены, но реальный routing на владельца остаётся server-side действием.

---

## 6. Внешний uptime monitor

Рекомендуемый минимум:

- UptimeRobot, Better Stack или Healthchecks.io
- проверка `GET https://<prod-host>/api/v1/health/live`
- интервал: 60 секунд
- alert condition: downtime > 2 minutes

Важно:

- `/metrics` наружу через публичный Nginx не публиковать
- production Nginx должен использовать allowlist для `/metrics`: `127.0.0.1` и `::1`; готовый snippet лежит в `infra/nginx/mstechnics-prod-locations.conf`
- uptime monitor должен проверять только `health/live`

---

## 7. Smoke-check после выката

1. Открыть `/api/v1/health/live`
2. Проверить `/metrics` локально с server host, публичный `/metrics` должен возвращать `403` или `404`
3. Убедиться, что Prometheus видит job `django` как `UP`
4. Открыть Grafana dashboard
5. Спровоцировать одно тестовое уведомление
6. Проверить рост `mstechnics_notification_delivery_total`

Если нужен негативный сценарий:

1. Временно подставить невалидный TG token в staging
2. Отправить тестовое уведомление
3. Убедиться, что растут `failed` delivery labels
4. При полном падении fallback chain проверить `mstechnics_notification_all_channels_failed_total`

---

## 8. Ограничения текущего решения

- Внешний uptime monitor и реальная alert delivery не могут быть полностью проверены без живого prod/staging после `T-6-001`.
- В compose нет отдельного postgres exporter; DB-specific метрики пока ограничены readiness probe.
- Если позже понадобится полноценная инцидентная цепочка, следующий шаг — отдельная задача на Alertmanager и/или Loki.
