# scripts/

- `dump_prod.sh` — дамп прод-БД. Требует `PROD_DATABASE_URL=postgres://...`
- `restore_to_dev.sh` — импорт дампа в dev. Требует `DATABASE_URL=postgres://...`
- `scrub_pii.sql` — очистка PII из dev-БД (email, telegram_id, phone, пароли)
- `bootstrap_dev.sh` — полный bootstrap dev: restore + scrub + migrate
- `compile-deps.sh` — регенерация requirements.lock через uv
