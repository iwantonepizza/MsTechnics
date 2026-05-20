# scripts/

- `dump_prod.sh` — dump prod PostgreSQL. Requires `PROD_DATABASE_URL=postgres://...`
- `restore_to_dev.sh` — restore `*.dump` into dev/staging, then run `showmigrations`, `migrate`, `check`. Accepts `DATABASE_URL=postgres://...` or `DATABASE_*`
- `backup-db.sh` — operational PostgreSQL backup: `pg_dump -Fc` + retention + optional encrypted off-host sync
- `restore-db.sh` — restore artifact created by `backup-db.sh` (`*.dump`, `*.dump.enc`, `*.sql`, `*.sql.gz`)
- `scrub_pii.sql` — scrub PII from dev DB (email, telegram_id, phone, passwords)
- `bootstrap_dev.sh` — full dev bootstrap: restore + scrub + migrate
- `compile-deps.sh` — regenerate `requirements.lock` via `uv`
