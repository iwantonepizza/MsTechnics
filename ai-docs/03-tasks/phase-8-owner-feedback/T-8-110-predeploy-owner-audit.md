# T-8-110. Pre-deploy owner audit: daily tasks, activity feed, panel delete, contrast

> **Статус:** review
> **Исполнитель:** GPT-5 Codex
> **Дата старта:** 2026-06-04
> **Приоритет:** P0 до prod
> **Scope:** Backend + Frontend + миграции + документация

## Контекст

Владелец повторно проверил продукт перед prod и подтвердил пять требований:

1. В мониторинге и контроле должны отображаться ежедневные задачи.
2. На главной снизу нужна лента последних действий с фильтрами периода и вида действия; видимость управляется администратором на пользователя.
3. Администратор должен удалять панель вместе со связанными архивными заявками и историями за одно действие.
4. Все кнопки и выпадающие меню должны иметь читаемый контраст.
5. Нужна итоговая проверка незакрытых задач и prod-readiness.

## Результат архитектурного аудита

- `DailyTask` API и UI существуют, но физическая legacy-таблица хранит `daily_task.city_id` как имя города, а active-модель ожидает числовой PK. Нужна forward-only миграция `name -> id`. UI также скрывает ошибку API под сообщением «Задач нет».
- Лента на `/menu`, поле `MsUser.show_activity_feed` и admin-toggle уже существуют. Не хватает фильтра вида действия.
- Каскадное удаление панели уже реализовано через `apps.directory.panels.services.delete_panel`, запрещает удаление при активной заявке и имеет backend/frontend тесты. Повторная очистка legacy-истории после удаления заявки обязательна: post-delete signal создаёт финальную запись.
- Secondary-кнопки и native select используют semantic tokens, но светлые `--fg-mute`/`--fg-faint` имеют недостаточный контраст и массово используются для мелкого текста.
- Документация прогресса устарела: Round 2.1 реализован в коде, но всё ещё указан как остаток; OpenAPI schema и prod-миграции требуют отдельной проверки.

## План работ

1. Добавить идемпотентную forward-only PostgreSQL-миграцию для `daily_task.city_id`.
2. Ограничить DailyTask API разрешёнными городами, добавить тесты и явное состояние ошибки в UI.
3. Добавить на ленту `/menu` фильтр сущности действия: все / заявки / панели / экраны.
4. Повторно проверить каскадное удаление панели и admin-only доступ.
5. Исправить общие contrast tokens и закрепить автоматической проверкой.
6. Прогнать backend/frontend проверки, проверить миграции/OpenAPI/prod blockers.
7. Обновить `progress.md`, Round 2 tracker и создать отчёт `08-reports/T-8-110.md`.

## Критерии приёмки

- [ ] После миграции существующие DailyTask корректно связаны с `city.id`: миграция готова, нужен прогон на копии prod PostgreSQL.
- [x] Мониторинг видит и выполняет ежедневные задачи; контроль видит read-only список.
- [x] Ошибка загрузки задач не отображается как пустой список.
- [x] Лента на главной фильтруется по 1/2 месяцам и виду действия.
- [x] `show_activity_feed` остаётся per-user toggle в Django admin.
- [x] Admin, включая multi-role admin, удаляет панель со всеми связанными архивными данными; активная заявка блокирует удаление.
- [x] Secondary-кнопки, вкладки, select/option и мелкий muted-текст имеют проверяемый контраст в light/dark.
- [x] Выполнены targeted tests, full tests, typecheck/build, Django check и encoding check.
- [x] Зафиксирован честный список оставшихся prod blockers.

## Итог аудита 2026-06-04

### Реализовано

- Добавлена forward-only PostgreSQL-миграция `workflow_daily_tasks.0004_convert_daily_task_city_fk_to_id`.
- DailyTask API больше нельзя вывести за `allowed_city` явным query-параметром; невалидный `city` возвращает 422.
- DailyTasks UI показывает ошибку API отдельно от пустого списка.
- В ленту `/menu` добавлены фильтры: все / заявки / панели / экраны и 1 / 2 месяца.
- Подтверждён per-user toggle `show_activity_feed` в Django admin.
- Подтверждено каскадное удаление панели, архивных заявок, событий и legacy-историй; добавлены проверки запрета для `service`/`all` и доступа multi-role admin.
- Исправлены общие contrast tokens и прямые неконтрастные использования; добавлен автоматический WCAG-тест токенов.
- Актуализированы `api-schema.yaml` и `frontend/src/shared/api/schema.d.ts`; `roles` теперь корректно описан как `string[]`.
- `AUTH_COOKIE_SECURE` теперь реально включает `SESSION_COOKIE_SECURE` и `CSRF_COOKIE_SECURE`.

### Проверки

- `pytest -q`: 141 passed.
- `npm run test`: 105 passed.
- `npm run typecheck`, `npm run build`, `manage.py check`, `makemigrations --check --dry-run`, `check_encoding.py`, targeted `ruff`/`black`, `git diff --check`: зелёные.
- OpenAPI генерируется, но остаётся baseline: 38 warnings и 12 errors из-за трёх APIView без serializer.

### Блокеры перед prod

1. Прогнать `workflow_daily_tasks.0004` и весь migration graph на копии prod PostgreSQL; локально это заблокировано остановленным Docker daemon.
2. Выполнить owner-side ротацию секретов по `T-6-005`.
3. Выполнить cutover-runbook с обязательным backup/restore smoke и явным `migrate`; `RUN_MIGRATIONS` в текущем локальном `.env` равен `0`.
4. Подтвердить TLS-терминацию и решить `SECURE_SSL_REDIRECT`/HSTS. Secure session/CSRF cookies уже включаются через `AUTH_COOKIE_SECURE`.
5. Провести ручную визуальную приёмку кнопок/select и mobile layout в реальном браузере.
6. Закрыть инфраструктурный baseline: отсутствует рабочий frontend ESLint config/CI, `ruff` 313, `black` 116 файлов, `mypy` 99 ошибок; dependency audit не запускается без lockfile/`pip-audit`.

## Что не делать

- Не удалять панель с активной заявкой.
- Не удалять legacy history tables до завершения post-cutover окна.
- Не скрывать ошибки API пустыми состояниями.
- Не менять контракт ActivityLog: использовать существующий `kind` prefix filter.
