# T-6-003. Observability: метрики, дашборды, alerts

> **Тип задачи:** infra + monitoring
> **Приоритет:** P1
> **Оценка:** 3-4 часа
> **Фаза:** 6 (production)
> **Статус:** ready
> **Исполнитель:** (заполняется при взятии в работу)

---

## Цель

После prod-cutover нужно знать о падениях до того, как пользователь напишет «не работает». Сейчас на проде: Sentry (T-1-008, optional) + структурный лог в stdout. Этого мало. Нужны: непрерывная uptime-проверка, метрики (request rate, error rate, p95 latency, очередь уведомлений), дашборд, алёрты в TG/MAX/email.

---

## Контекст

Что уже есть:
- `T-1-008` — `sentry-sdk[django]` инициализируется, если задан `SENTRY_DSN`. Захватывает исключения.
- `structlog` пишет JSON в stdout с `request_id`, `user_id`.
- `/api/v1/health/live` endpoint существует (T-3-050).
- `NotificationDeliveryAttempt` пишется в БД на каждую попытку отправки уведомления.

Чего не хватает:
- Прометей-метрики (request count, latency, by status code).
- Дашборд (Grafana).
- Alert при `notification_all_channels_failed` > N в окне.
- Внешний uptime-monitor — чтобы не зависеть от того же сервера.

---

## Зависимости

- **Блокируется:** T-6-001 (prod должен жить, чтобы мониторить).
- **Блокирует:** ничего.

---

## Что нужно сделать

### Шаг 1. django-prometheus

```bash
pip install django-prometheus
```

В `pyproject.toml` добавить `django-prometheus>=2.3`.

В `Config/settings.py`:

```python
INSTALLED_APPS = [
    "django_prometheus",
    # ...
]
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    # ... остальные middleware ...
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]
```

В `Config/urls.py`:

```python
path("metrics/", include("django_prometheus.urls")),
```

`metrics/` отдаёт текстовый формат для Prometheus scrape. Эндпоинт **только** в внутренней сети — не публиковать через nginx наружу.

### Шаг 2. Кастомные метрики в notifications

`apps/notifications/dispatcher.py` уже пишет `NotificationDeliveryAttempt`. Добавить также Prometheus counter:

```python
from prometheus_client import Counter

notification_sent_total = Counter(
    "mstechnics_notification_sent_total",
    "Notifications sent",
    ["channel", "status"],
)

# При успешной/неуспешной отправке
notification_sent_total.labels(channel="telegram", status="success").inc()
notification_sent_total.labels(channel="telegram", status="failed").inc()
```

Аналогично — счётчик `notification_all_channels_failed_total` (когда fallback не помог).

### Шаг 3. Развернуть Prometheus + Grafana

`docker-compose.yml` дополнить:

```yaml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus_data:/prometheus
  command:
    - "--config.file=/etc/prometheus/prometheus.yml"
    - "--storage.tsdb.retention.time=30d"

grafana:
  image: grafana/grafana:latest
  volumes:
    - grafana_data:/var/lib/grafana
    - ./infra/grafana/provisioning:/etc/grafana/provisioning
  ports:
    - "127.0.0.1:3001:3000"   # только localhost, наружу через nginx с basic-auth
```

`infra/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: django
    static_configs:
      - targets: ["web:8000"]
    metrics_path: /metrics/
```

### Шаг 4. Базовый дашборд Grafana

`infra/grafana/provisioning/dashboards/mstechnics.json` — минимум 6 панелей:

1. Request rate (req/s) по pathу.
2. Error rate (5xx / total).
3. p95 latency по endpoint'у.
4. Notifications sent by channel (TG/MAX/email).
5. `all_channels_failed` rate.
6. Active connections / open SSE connections.

Datasource — Prometheus. Импорт в Grafana через provisioning при старте.

### Шаг 5. Внешний uptime monitor

Любой бесплатный — UptimeRobot, Better Stack, Healthchecks.io. Проверять `https://<prod-host>/api/v1/health/live` каждую минуту. При downtime > 2 мин — алёрт в TG / email владельцу.

### Шаг 6. Alerts на критичные метрики

В Grafana / Alertmanager:

- `notification_all_channels_failed_total` > 5 за 10 мин → severity=high.
- 5xx rate > 5% за 5 мин → severity=high.
- p95 latency > 2s за 10 мин → severity=medium.
- DB connections close to limit (если есть прометей-экспортёр postgres) → severity=medium.

Куда слать — в тот же TG-канал владельца, через тот же `TelegramChannel` (или отдельный admin-bot).

### Шаг 7. Документация

`ai-docs/06-integrations/observability-runbook.md`:

- Как открыть Grafana локально / на проде.
- Что значат каждая из 6 панелей.
- Как реагировать на каждый из 4 алёртов.
- Где смотреть Sentry events.

---

## Критерии приёмки

- [ ] `/metrics/` отдаёт Prometheus-формат.
- [ ] `docker compose up -d prometheus grafana` поднимает оба.
- [ ] Дашборд в Grafana доступен и показывает данные из 5+ панелей.
- [ ] Внешний uptime monitor настроен и шлёт алёрт владельцу при downtime.
- [ ] Хотя бы один алёрт (нпр. `all_channels_failed`) сработал в тестовом сценарии.
- [ ] `06-integrations/observability-runbook.md` написан.
- [ ] Отчёт в `08-reports/T-6-003.md`.

---

## Что НЕ нужно делать

- Не публиковать `/metrics/` наружу без авторизации.
- Не делать собственный custom-monitoring (cron + curl + bash) — есть готовые инструменты.
- Не подключать ELK/Loki/Jaeger в одной задаче — это отдельные проекты.

---

## Отчёт

(Заполняет кодер.)
