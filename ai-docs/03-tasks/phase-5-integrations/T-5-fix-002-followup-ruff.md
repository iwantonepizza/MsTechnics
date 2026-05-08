# T-5-fix-002-followup. Разбор lint/type baseline после поднятия dev/test tooling

> **Тип:** cleanup / infra
> **Приоритет:** P3
> **Оценка:** 2-3 часа
> **Фаза:** 5
> **Статус:** blocked
> **Исполнитель:** —

---

## Цель

После `T-5-fix-002` инструменты наконец запускаются, но показывают большой существующий baseline:

- `ruff check apps shared Config` -> 291 ошибок
- `black --check apps shared Config` -> 96 файлов на переформатирование
- `mypy apps` -> 16 ошибок в 12 файлах

Эта задача нужна, чтобы разобрать baseline отдельно от staging cutover и migration hotfix'ов.

---

## Зависимости

- **Блокируется:** `T-5-fix-001` и staging smoke. До cutover не нужен большой форматный churn.
- **Блокирует:** ничего.

---

## Что сделать

1. Разбить `ruff` ошибки по категориям и выбрать безопасные автофиксы.
2. Отдельно прогнать `ruff --fix` на точечных папках без массового переформатирования migrations.
3. Согласованно применить `black` там, где это не создаёт лишний шум в legacy-коде.
4. Добить `mypy` ошибки или задокументировать accepted ignores.
5. В конце добиться:

```bash
ruff check apps shared Config
black --check apps shared Config
mypy apps
```

---

## Что НЕ делать

- Не смешивать с migration/state cleanup.
- Не трогать большие legacy-модули без явной причины.
- Не переписывать миграции ради косметики, если это только churn.

---

## Критерии приёмки

- [ ] `ruff check apps shared Config` -> exit 0
- [ ] `black --check apps shared Config` -> exit 0
- [ ] `mypy apps` -> baseline устранён или явно зафиксирован новыми ignores
- [ ] Изменения отделены от staging/migration hotfix

