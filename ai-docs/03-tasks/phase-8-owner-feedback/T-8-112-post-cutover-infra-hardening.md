# T-8-112. Post-cutover infra hardening

Статус: review
Исполнитель: GPT-5
Дата старта: 2026-06-05

## Контекст

После закрытия `T-8-111` production уже развёрнут через git, но остались эксплуатационные хвосты:

- внешние `/health/live` и `/health/ready` должны стабильно отдавать JSON, а не SPA fallback;
- `/metrics` не должен быть публичным через Nginx;
- `mstechnics-vnnox-pull.timer` нельзя включать без Gmail OAuth token и заполненных `Display.vnnox_device_id`;
- локальный DB backup работает, но off-host encrypted backup не настроен;
- SSH получает автоматические попытки входа, нужен fail2ban; смену пароля делает владелец.

## Что сделать

1. Зафиксировать production Nginx snippets для health aliases и закрытого `/metrics`.
2. Актуализировать systemd unit-файлы под фактический production path `/root/DisplayControl/MsTechnics`.
3. Подготовить fail2ban jail для sshd без изменения пароля и без отключения текущего способа входа.
4. Проверить production состояние VNNOX, backup, observability и SSH hardening.
5. Обновить документацию и отчёт.

## Критерии приёмки

- [x] В repo есть Nginx snippet для `/health/live`, `/health/ready` и локального-only `/metrics`.
- [x] В repo systemd units используют текущие production paths.
- [x] VNNOX pull timer не включается, пока нет `Config/token.pickle` и `Display.vnnox_device_id`.
- [x] Fail2ban jail подготовлен в repo.
- [x] Fail2ban установлен и активирован на production.
- [x] Public `/metrics` на production возвращает 403, локальный `/metrics` доступен для scrape.
- [ ] Production `git pull` выполнен после push.

## Production результат

На 2026-06-05 серверные изменения применены через SSH по `mstechnics.ru`.
Адрес `185.251.88.12` из сообщения владельца не совпадает с DNS production `mstechnics.ru -> 185.251.88.121` и не использовался для финальных действий.

Проверки после применения:

- public `/metrics` -> `403`;
- local `/metrics` через `https://127.0.0.1/metrics` + `Host: mstechnics.ru` -> `200`;
- `/health/live` -> `200`;
- `/health/ready` -> `200`;
- `fail2ban` -> `active`, jail `sshd` включён.

## Отчёт по выполнению

См. `ai-docs/08-reports/T-8-112.md`.
