# T-2-001. Baseline прод-данных: дамп, импорт в dev, fixture minimal-seed

> **Тип:** infra / data
> **Приоритет:** P0 (blocker для всех миграций Фазы 2)
> **Оценка:** 2 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

До того как начать менять модели, нужно иметь:
1. Полный дамп прод-БД, который можно поднять локально для проверки миграций
2. Автоматизированный процесс: «дамп прод → импорт в dev → прогон миграций → сверка»
3. Минимальный fixture для тестов (без персональных данных, но со всеми типами состояний)

**Без этой задачи нельзя запускать ни одну миграцию Фазы 2.** Ломаем прод-данные — проект останавливается на неделю.

---

## Зависимости

- **Блокируется:** T-1-007 (секреты должны быть уже вне репо)
- **Блокирует:** все задачи T-2-0XX с миграциями

---

## Что нужно сделать

### Часть 1. Дамп прода

1. Получить у владельца доступ к прод-БД (read-only достаточно)
2. Создать скрипт `scripts/dump_prod.sh`:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   
   : "${PROD_DATABASE_URL:?env var required}"
   DUMP_DIR="${DUMP_DIR:-./dumps}"
   mkdir -p "$DUMP_DIR"
   TS="$(date -u +%Y%m%d-%H%M%S)"
   OUT="$DUMP_DIR/prod-$TS.sql.gz"
   
   pg_dump --no-owner --no-acl --format=plain "$PROD_DATABASE_URL" \
     | gzip -9 > "$OUT"
   
   echo "Dumped to: $OUT"
   echo "Size: $(du -h "$OUT" | cut -f1)"
   ```
3. `dumps/` в `.gitignore`
4. Проверить: `PROD_DATABASE_URL=... ./scripts/dump_prod.sh` создаёт файл

### Часть 2. Импорт в dev

1. `scripts/restore_to_dev.sh`:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   
   DUMP_FILE="${1:?usage: $0 <dump.sql.gz>}"
   : "${DATABASE_URL:?env var required — dev db}"
   
   # safety: не даём перезалить прод по ошибке
   if [[ "$DATABASE_URL" == *"prod"* || "$DATABASE_URL" == *":5432/mstechnics?"* ]]; then
     echo "REFUSING: DATABASE_URL looks like prod" >&2
     exit 1
   fi
   
   # drop & recreate
   psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   gunzip -c "$DUMP_FILE" | psql "$DATABASE_URL"
   echo "Restored $DUMP_FILE to $DATABASE_URL"
   ```

### Часть 3. PII-scrubber для dev-версии

**Критично:** прод-дамп содержит email, телефоны, telegram_id. В dev-среде они быть не должны.

1. `scripts/scrub_pii.sql`:
   ```sql
   -- Замена email на предсказуемые
   UPDATE user_msuser SET
     email = CONCAT('user', id, '@example.test'),
     telegram_id = NULL,
     max_chat_id = NULL;
   
   UPDATE departure_executor SET
     phone = CONCAT('+7900000', LPAD(id::text, 4, '0')),
     telegram_id = NULL;
   
   -- Пароли всех юзеров → единый 'dev_password'
   -- (хэш от 'dev_password' с django dummy-algorithm)
   UPDATE user_msuser SET
     password = 'pbkdf2_sha256$260000$dev$xxxxxxxxxxxxxxxx';
   
   -- Вычищаем прикрепления
   TRUNCATE TABLE mail_gmailmessage, mail_alarm CASCADE;
   
   -- Сообщения из воркеров логов (если они в БД)
   -- TRUNCATE ... дополнить по факту
   ```

2. Запуск: `psql "$DATABASE_URL" -f scripts/scrub_pii.sql`

3. **Сводная команда** `scripts/bootstrap_dev.sh`:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   DUMP="${1:?usage: $0 <dump.sql.gz>}"
   ./scripts/restore_to_dev.sh "$DUMP"
   psql "$DATABASE_URL" -f scripts/scrub_pii.sql
   python manage.py migrate  # применить все миграции что есть
   echo "Dev DB ready."
   ```

### Часть 4. Minimal fixture для тестов

Для unit-тестов не нужен весь прод — нужен детерминированный минимум.

1. Создать management command `apps/core/management/commands/dump_minimal_fixture.py`:
   - Выбирает: 1 город, 1 экран 3×3, 9 ячеек, 12 панелей (9 в экране + 3 в ЗИП), 2 заявки в разных статусах, 1 выезд, 2 юзера (admin + service)
   - Все справочники (Condition, ApplicationStatus, Color, Icon, Department)
   - Сохраняет в `apps/core/fixtures/minimal.json`

2. Проверить: на чистой БД `python manage.py loaddata minimal` поднимает работоспособную систему для тестов.

### Часть 5. Документация

Обновить `ai-docs/02-roadmap/roadmap.md` (раздел 2.1) — добавить ссылки на скрипты.

Создать `scripts/README.md`:
```markdown
# scripts/

- dump_prod.sh — дамп прод-БД (запускать с прод-доступом)
- restore_to_dev.sh — импорт дампа в dev
- scrub_pii.sql — очистка PII из dev-БД
- bootstrap_dev.sh — полный bootstrap dev-окружения
```

---

## Критерии приёмки

- [ ] Все 4 скрипта работают, содержат `set -euo pipefail`
- [ ] `restore_to_dev.sh` **отказывается** запускаться на prod URL
- [ ] После `bootstrap_dev.sh` в БД нет ни одного реального email/telegram_id/phone
- [ ] Фикстура `minimal.json` — загружается на чистую БД, все тесты проходят
- [ ] Документация в `scripts/README.md` актуальна
- [ ] `dumps/` в `.gitignore`, пустой дамп в репо **не попал**

---

## Что НЕ делать

- **НЕ храни** прод-дампы в git или облаке без шифрования
- **НЕ используй** прод-credentials в `.env.example`
- **НЕ давай** кодеру read-write доступ к проду — только read для dump'а
- **НЕ коммить** `minimal.json` если он весит > 100KB — сделай truncated

---

## Риски

- Прод-БД большая (1GB+) — дамп может занять 5-10 минут; не ломай прод
- Сеть между прод и твоим компом медленная — используй `pg_dump --compress=9` или делай дамп на сервере и скачивай gzipped
- Если в проде есть `pg_repack` / кастомные расширения — `pg_dump` может упасть на `CREATE EXTENSION` строках без прав. Решение: `--no-owner --no-acl`, вручную правь DUMP если нужно.

---

## Вопросы

- [ ] Есть ли автоматизированные бэкапы прода (кроме этого скрипта)?
- [ ] Может ли владелец предоставить неактуальный дамп (старый бэкап) для начала — чтобы кодер не ждал прод-доступа?
