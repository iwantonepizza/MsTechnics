# Production Cutover Runbook

Дата: 2026-05-13

Цель: убрать legacy compat-path и выполнить один поддерживаемый сценарий `pg_restore -> showmigrations -> migrate -> check` для выката на Linux-сервере. `scripts/prod_dump_compat.sql` больше не используется и не должен возвращаться ни в каком виде.

## Актуальная prod-топология 2026-06-04

- Рабочий каталог: `/root/DisplayControl/MsTechnics`.
- Python runtime: отдельный venv `/root/DisplayControl/venv-<revision>`.
- Запуск: native PostgreSQL 16 + Redis + nginx + systemd `gunicorn.service`.
- Health: `/api/v1/health/live` и `/api/v1/health/ready` без завершающего `/`.
- Backup: `mstechnics-db-backup.timer`, локальные dumps в
  `/var/backups/mstechnics/scheduled`.
- Для SSE gunicorn обязан использовать `--worker-class gevent --worker-connections 1000`.
  Sync workers блокируются долгоживущими `/api/v1/events/stream` и уходят в timeout.
- Для nginx нужен отдельный `location = /api/v1/events/stream` с `proxy_buffering off`,
  длинным `proxy_read_timeout` и `access_log off`, чтобы query JWT не попадал в access log.

Команды ниже по-прежнему используют `/opt/mstechnics` как стандартный шаблон. На текущем native
prod заменить путь на фактический из списка выше.

## 1. Что подготовить заранее

- Подтвердить, где именно лежит рабочий каталог проекта на сервере. Ниже по умолчанию используется `/opt/mstechnics`.
- Подтвердить, что секреты уже ротированы по `T-6-005`, или хотя бы зафиксировать риск отдельно до maintenance window.
- Подтвердить способ запуска прод-окружения:
  - `docker compose` для `db`, `web`, `redis`;
  - либо нативный PostgreSQL/systemd. Если сервер не compose-based, адаптировать только команды запуска сервисов. Порядок `restore -> migrate -> smoke` не меняется.
- Подготовить свежий custom-format dump `*.dump`.
- Убедиться, что на Linux host есть:
  - `bash`
  - `python3.12`
  - `psql`
  - `pg_restore`
  - `curl`
- `pg_restore --version` должен быть не старше major-version dump/server PostgreSQL. Для dump из PostgreSQL 16 использовать PostgreSQL 16 client tools.
- Убедиться, что `.env` содержит актуальные `DATABASE_*`, `SECRET_KEY`, OAuth/token secrets и не содержит старые утёкшие значения.

## 2. Pre-flight checklist

- Окно простоя согласовано.
- Есть backup текущей prod-БД, сделанный непосредственно перед cutover.
- `git status --short` в рабочем каталоге пустой.
- В репозитории отсутствует `scripts/prod_dump_compat.sql`.
- `python manage.py showmigrations | tail -100` с сервера сохранён в отдельный файл перед началом работ.
- На сервер залит свежий `*.dump`, который будет восстанавливаться.

## 3. Backup перед выкатом

Никогда не пропускать этот шаг.

```bash
cd /opt/mstechnics
mkdir -p logs /var/backups/mstechnics

export BACKUP_TS="$(date -u +%Y%m%d_%H%M%S)"
export PRE_CUTOVER_DUMP="/var/backups/mstechnics/pre_cutover_${BACKUP_TS}.dump"

PGPASSWORD="$DATABASE_PASSWORD" \
  pg_dump \
    --format=custom \
    --no-owner \
    --no-privileges \
    -h "$DATABASE_HOST" \
    -p "$DATABASE_PORT" \
    -U "$DATABASE_USER" \
    -f "$PRE_CUTOVER_DUMP" \
    "$DATABASE_NAME"
```

Проверка:

```bash
ls -lh "$PRE_CUTOVER_DUMP"
```

## 4. Обновить код

```bash
cd /opt/mstechnics
git fetch origin
git checkout main
git pull --ff-only origin main
```

Если deployment идёт из другой ветки или тега, заменить `main` на согласованный ref, но не возвращать `prod_dump_compat.sql`.

## 5. Восстановить dump и прогнать миграции

Пример ниже предполагает, что новый dump лежит в `/var/backups/mstechnics/mstechnics.dump`.

```bash
cd /opt/mstechnics

export DATABASE_URL="postgres://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT}/${DATABASE_NAME}"

bash ./scripts/restore_to_dev.sh /var/backups/mstechnics/mstechnics.dump \
  2>&1 | tee logs/t6_001_final_run.log
```

Скрипт сам выполняет:

1. `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`
2. `pg_restore --clean --if-exists --no-owner --no-privileges`
3. `python manage.py showmigrations | tail -60`
4. `python manage.py migrate --noinput`
5. `python manage.py check`

Если на сервере нет `DATABASE_URL`, можно использовать `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`.

## 6. Compose-based запуск приложения

Если прод развёрнут через `docker compose`, после успешного restore/migrate:

```bash
cd /opt/mstechnics
docker compose up -d --build redis web
docker compose ps
```

Если процессы запускаются через systemd/gunicorn вне compose, вместо этого выполнить локальный restart соответствующих unit-файлов.

Перед restart native gunicorn проверить, что unit не запускает sync workers:

```bash
systemctl cat gunicorn
gunicorn --check-config \
  --worker-class gevent \
  --worker-connections 1000 \
  project_config.wsgi:application
```

После изменения unit:

```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl status gunicorn --no-pager
```

## 7. Smoke после cutover

Минимальный smoke:

```bash
cd /opt/mstechnics
python manage.py check 2>&1 | tee logs/t6_001_check.log
curl -sf http://127.0.0.1:8000/api/v1/health/live | tee logs/t6_001_smoke_live.txt
```

Если есть тестовый пользователь с валидным паролем, дополнительно:

```bash
TOKEN="$(curl -sX POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"<smoke-user>","password":"<smoke-password>"}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["access"])')"

curl -sf \
  -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8000/api/v1/displays/ \
  | tee logs/t6_001_smoke_displays.json
```

Ожидание:

- `/api/v1/health/live` -> `200`
- `/api/v1/auth/login/` -> токен
- `/api/v1/displays/` -> `200` и валидный JSON

## 8. Troubleshooting

### 8.1 `showmigrations` и `migrate` разошлись

Снять матрицу:

```bash
cd /opt/mstechnics
python manage.py showmigrations 2>&1 | tee logs/t6_001_showmigrations_before.log
```

`[X]` означает, что migration отмечена applied в `django_migrations`, `[ ]` — нет.

Если видно, что конкретная migration уже отражена физически в БД, но не синхронизирована в state, использовать только точечный `--fake`:

```bash
python manage.py migrate <app_label> <migration_name> --fake
```

`--fake-initial` как универсальный флаг не использовать.

### 8.2 Падение на SQL-ошибке

Снять подробный лог:

```bash
cd /opt/mstechnics
python manage.py migrate --verbosity=3 2>&1 | tee logs/t6_001_migrate_error.log
```

Дальше смотреть конкретную migration и сравнивать её ожидания с реальной физической схемой. Первое, что нужно проверить: не был ли ранее вручную применён старый compat-патч. Если был, БД нужно восстановить заново из чистого dump без compat.

### 8.3 Нельзя понять, в каком состоянии сервер

Снять данные напрямую из `django_migrations`:

```bash
PGPASSWORD="$DATABASE_PASSWORD" \
  psql \
    -h "$DATABASE_HOST" \
    -p "$DATABASE_PORT" \
    -U "$DATABASE_USER" \
    "$DATABASE_NAME" \
    -c "SELECT app, name, applied FROM django_migrations ORDER BY applied;"
```

## 9. Rollback

Если smoke не проходит:

```bash
cd /opt/mstechnics
docker compose stop web redis || true

PGPASSWORD="$DATABASE_PASSWORD" \
  pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    -h "$DATABASE_HOST" \
    -p "$DATABASE_PORT" \
    -U "$DATABASE_USER" \
    -d "$DATABASE_NAME" \
    "$PRE_CUTOVER_DUMP"
```

Дальше:

- вернуть предыдущий git ref;
- поднять прежние сервисы;
- отдельно сохранить логи текущего неудачного запуска;
- не пытаться «дочинить на живой БД» старым compat-патчем.

## 10. Post-cutover наблюдение

Первые 24 часа мониторить:

- `GET /api/v1/health/live`
- ошибки в логах web/gunicorn
- доставку уведомлений
- ошибки Gmail/MAX/Telegram интеграций
- базовые counts по `Display`, `Panel`, `Application`

Если прод уже использует наблюдаемость из `T-6-003`, дополнительно проверить `/metrics`, Prometheus targets и firing alerts.
