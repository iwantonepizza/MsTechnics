# T-6-002. Backup strategy — pgBackRest или WAL-G + cron rotation

> **Тип задачи:** infra
> **Приоритет:** P1 (нужно до prod-cutover, иначе первый сбой = потеря данных)
> **Оценка:** 2-3 часа
> **Фаза:** 6 (production)
> **Статус:** ready
> **Исполнитель:** (заполняется при взятии в работу)

---

## Цель

Поднять автоматизированные резервные копии прод-БД с PITR (point-in-time recovery). Сейчас стратегия — «руками `pg_dump`, когда вспомним» — это не стратегия. На внутренней системе с реальными заявками первый же сбой диска = потеря данных за день/неделю.

---

## Контекст

`db_dumps/mstechnics.dump` в репо — это **одноразовый** дамп для cutover, не операционный backup. После prod-cutover нужно:

1. **Ежедневный полный pg_dump** (как минимум) — в `/var/backups/mstechnics/` + ротация 14 дней.
2. **WAL archiving** — для PITR с точностью до минуты на случай удаления данных по ошибке.
3. **Off-host копия** — хотя бы суточный rsync на отдельный объём / S3 / другой VPS.

---

## Зависимости

- **Блокируется:** T-6-001 (нужен живой prod, чтобы тестировать восстановление).
- **Блокирует:** ничего напрямую, но **обязательно** до закрытия 2-недельного prod-stable window.

---

## Что нужно сделать

### Вариант 1 — pgBackRest (рекомендую)

Production-grade инструмент, поддерживает full / incremental / differential backups + WAL archiving + параллельное восстановление.

```bash
sudo apt install pgbackrest
sudo mkdir -p /var/lib/pgbackrest /var/log/pgbackrest /var/spool/pgbackrest
sudo chown postgres:postgres /var/lib/pgbackrest /var/log/pgbackrest /var/spool/pgbackrest
```

Конфиг `/etc/pgbackrest/pgbackrest.conf`:

```ini
[mstechnics]
pg1-path=/var/lib/postgresql/16/main
pg1-port=5432

[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=2
repo1-retention-diff=7
repo1-cipher-type=aes-256-cbc
repo1-cipher-pass=<сгенерировать openssl rand -hex 32>
log-level-console=info
log-level-file=detail
process-max=2
```

В `postgresql.conf`:

```
archive_mode = on
archive_command = 'pgbackrest --stanza=mstechnics archive-push %p'
max_wal_senders = 3
wal_level = replica
```

Инициализация:

```bash
sudo -u postgres pgbackrest --stanza=mstechnics stanza-create
sudo -u postgres pgbackrest --stanza=mstechnics check
```

Cron:

```cron
# полный backup воскресенье 02:00
0 2 * * 0 postgres pgbackrest --stanza=mstechnics --type=full backup
# incremental ежедневно 03:00
0 3 * * 1-6 postgres pgbackrest --stanza=mstechnics --type=incr backup
```

### Вариант 2 — простой pg_dump cron (минимум)

Если pgBackRest перебор для размера БД (несколько МБ):

```bash
sudo mkdir -p /var/backups/mstechnics
sudo chown postgres:postgres /var/backups/mstechnics
```

`/etc/cron.daily/mstechnics-backup`:

```bash
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR=/var/backups/mstechnics
DATE=$(date +%Y%m%d_%H%M%S)
sudo -u postgres pg_dump -Fc mstechnics > "$BACKUP_DIR/mstechnics_$DATE.dump"
gzip "$BACKUP_DIR/mstechnics_$DATE.dump"
# ротация — оставляем 14 последних
ls -t "$BACKUP_DIR"/mstechnics_*.dump.gz | tail -n +15 | xargs -r rm
```

### Off-host копия (любой из вариантов)

В тот же cron — `rsync` на другой VPS / S3 / Yandex Object Storage:

```bash
rsync -avz /var/backups/mstechnics/ backup-vps:/var/backups/mstechnics/
```

### Проверка восстановления

**Обязательно** один раз пройти полный цикл backup → удалить таблицу → restore — на staging-копии БД. Без проверки backup'а его как будто нет.

```bash
# Создать тестовую staging-БД
sudo -u postgres createdb mstechnics_test
sudo -u postgres pg_restore -d mstechnics_test /var/backups/mstechnics/mstechnics_*.dump.gz
psql mstechnics_test -c "SELECT COUNT(*) FROM application;"
```

### Документация

`ai-docs/06-integrations/backup-runbook.md` — что делать при потере данных:

1. Остановить web/voркеры.
2. `pg_restore` последнего backup на staging.
3. Проверить, что данные на месте (`SELECT COUNT(*)` ключевых таблиц).
4. Заменить прод-БД восстановленной копией.
5. Запустить web заново.

Оценка по времени (для разной величины потери): минута/час/день.

---

## Критерии приёмки

- [ ] Один из двух вариантов (pgBackRest или pg_dump cron) развёрнут на проде.
- [ ] Cron отрабатывает по расписанию — провести тестовый запуск.
- [ ] Off-host копия льётся на отдельный хост.
- [ ] Проведено одно тестовое **восстановление** на staging-БД — это критерий приёмки.
- [ ] `06-integrations/backup-runbook.md` написан.
- [ ] Отчёт в `08-reports/T-6-002.md`.

---

## Что НЕ нужно делать

- Не настраивать репликацию (master/replica) — это отдельная задача, нам пока хватит backup'а.
- Не использовать `pg_dump --globals-only` без `--data-only` — нам нужны **и** схема, и данные.
- Не лить backup в git / S3-bucket с публичным доступом — это PII. Шифровать.

---

## Отчёт

(Заполняет кодер.)
