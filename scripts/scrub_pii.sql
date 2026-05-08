-- scrub_pii.sql — очистка персональных данных из dev-копии прод-БД
-- Запуск: psql "$DATABASE_URL" -f scripts/scrub_pii.sql

BEGIN;

-- Пользователи: email, telegram_id → обезличенные значения
UPDATE "user"
SET
    email          = CONCAT('user', id, '@example.test'),
    telegram_id    = NULL,
    -- Пароль всех юзеров → 'devpassword' (не нужно помнить реальные)
    password       = 'pbkdf2_sha256$720000$devsalt$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
WHERE id IS NOT NULL;

-- Исполнители: обезличиваем имя и контакты
UPDATE departure_executor
SET
    name        = CONCAT('Исполнитель ', id),
    telegram_id = NULL
WHERE id IS NOT NULL;

-- Gmail-письма: содержат PII (тема, адреса, тело)
TRUNCATE TABLE mail_gmailmessage CASCADE;

COMMIT;

\echo 'PII scrub завершён.'
