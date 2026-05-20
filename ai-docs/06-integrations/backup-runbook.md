# Backup Runbook

Дата: 2026-05-13

Цель: обеспечить операционный backup PostgreSQL до и после prod-cutover без привязки к нестабильной ручной процедуре.

---

## 1. Принятое решение

Для текущего масштаба MsTechnics выбран **вариант 2 из T-6-002**:

- ежедневный backup через `pg_dump -Fc` в custom format;
- хранение локально в `/var/backups/mstechnics`;
- ротация последних 14 backup-артефактов;
- optional off-host sync через `rsync`;
- если backup уходит off-host, использовать `BACKUP_ENCRYPTION_PASSPHRASE` и отправлять **только encrypted artifact** `*.dump.enc`.

Почему не `pgBackRest` сейчас:

- карточка допускает `pg_dump cron` как минимально достаточный вариант;
- точная prod-конфигурация PostgreSQL и layout `/etc/postgresql/...` ещё не зафиксированы в `T-6-001`;
- для небольшой БД безопаснее сначала внедрить простой и понятный backup/restore path, который владелец сможет реально прогнать и поддерживать.

---

## 2. Что устанавливаем на сервере

Нужны пакеты:

```bash
sudo apt update
sudo apt install -y postgresql-client rsync openssl
```

Каталог backup'ов:

```bash
sudo mkdir -p /var/backups/mstechnics
sudo chown "$USER":"$USER" /var/backups/mstechnics
sudo chmod 700 /var/backups/mstechnics
```

Если backup будет запускаться от отдельного service user, права выдать ему.

---

## 3. Обязательные env-переменные

Скрипт `scripts/backup-db.sh` умеет работать двумя способами:

1. Через `DATABASE_URL=postgres://...`
2. Через существующие `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`

Для off-host копии дополнительно:

```bash
BACKUP_REMOTE_TARGET=backup-vps:/var/backups/mstechnics/
BACKUP_ENCRYPTION_PASSPHRASE=<сгенерировать-через-openssl-rand-hex-32>
```

По умолчанию plaintext off-host sync запрещён.

---

## 4. Ручной тест backup

На сервере проекта:

```bash
cd /opt/mstechnics
chmod +x scripts/backup-db.sh scripts/restore-db.sh
./scripts/backup-db.sh
ls -lah /var/backups/mstechnics
```

Успех:

- появился новый `mstechnics_YYYYMMDD_HHMMSS.dump` или `*.dump.enc`;
- рядом лежит `*.sha256`;
- если настроен `BACKUP_REMOTE_TARGET`, артефакт скопирован и на удалённый хост.

---

## 5. Systemd timer

Установка:

```bash
sudo cp infra/systemd/mstechnics-db-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mstechnics-db-backup.timer
systemctl list-timers 'mstechnics-db-backup*'
```

Разовый тестовый запуск:

```bash
sudo systemctl start mstechnics-db-backup.service
sudo systemctl status mstechnics-db-backup.service --no-pager
journalctl -u mstechnics-db-backup.service -n 50 --no-pager
```

---

## 6. Проверка восстановления

Backup без restore-проверки не считается рабочим.

### Вариант A. Отдельная staging/test БД

```bash
createdb mstechnics_restore_test
export DATABASE_NAME=mstechnics_restore_test
./scripts/restore-db.sh /var/backups/mstechnics/<последний-backup>.dump
psql -d mstechnics_restore_test -c "SELECT COUNT(*) FROM auth_user;"
```

Если backup encrypted:

```bash
export BACKUP_ENCRYPTION_PASSPHRASE=...
./scripts/restore-db.sh /var/backups/mstechnics/<последний-backup>.dump.enc
```

### Вариант B. Через `DATABASE_URL`

```bash
DATABASE_URL=postgres://user:pass@host:5432/mstechnics_restore_test \
  ./scripts/restore-db.sh /var/backups/mstechnics/<последний-backup>.dump
```

### Минимальные smoke-checks после restore

```sql
SELECT COUNT(*) FROM django_migrations;
SELECT COUNT(*) FROM user_msuser;
SELECT COUNT(*) FROM application;
SELECT COUNT(*) FROM zip_panel;
```

Если restore делается на копии prod-дампа после cutover, дополнительно:

```bash
python manage.py migrate --plan
python manage.py migrate
python manage.py check
```

---

## 7. Что делать при реальной потере данных

1. Остановить web и фоновые процессы, чтобы не писать поверх повреждённой БД.
2. Зафиксировать время инцидента и выбрать последний консистентный backup.
3. Восстановить backup **сначала в staging/test БД**, не сразу поверх prod.
4. Проверить счётчики ключевых таблиц и базовые логины.
5. Только после smoke-check заменить prod-БД восстановленной копией.
6. Поднять web и проверить:
   - `/api/v1/health/live`
   - login
   - список заявок
   - доставку уведомлений

---

## 8. RPO / RTO

- Текущий вариант `pg_dump` даёт **RPO до 24 часов** между ежедневными backup'ами.
- **RTO** зависит от размера БД и скорости сервера, для текущего объёма ожидаемо минуты, не часы.
- Если после cutover подтвердится, что потери до 24 часов неприемлемы, следующий шаг — отдельная задача на `pgBackRest` или WAL archiving/PITR.

---

## 9. Что не делать

- Не хранить backup в git.
- Не отправлять plaintext dump на публичный bucket.
- Не считать задачу принятой без хотя бы одного успешного test restore.
