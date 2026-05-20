# T-7-001. Rebranding: «MsTechnics» → «Суперсимметрия» в UI

> **Тип задачи:** frontend + content
> **Приоритет:** P1 (не блокер prod cutover, но первая фронтовая задача после стабилизации)
> **Оценка:** 1.5-2 часа
> **Фаза:** 7 (product / post-cutover)
> **Статус:** review (SVG получен 2026-05-17, лежит в `frontend/public/logo-supersymmetria.svg`)
> **Исполнитель:** GPT-5 Codex

---

## Цель

Заменить в UI рабочее имя «MsTechnics» на брендовое «Суперсимметрия». Поставить новый логотип. **Бэкенд / БД / URL / Django app names не трогаются** — см. `ADR-002`.

---

## Контекст

- Решение владельца, фиксировано в [`ADR-002-rebranding-supersymmetria.md`](../../adr/ADR-002-rebranding-supersymmetria.md).
- Лого прислан как PNG в чате. Дизайнер векторизует в SVG, кодер ставит как файл.
- Палитра НЕ меняется в этой задаче — это T-7-002. Здесь только имя + лого + метаданные.

---

## Зависимости

- **Блокируется:** получением SVG-логотипа (дизайнер).
- **Блокирует:** T-7-002 (design tokens v2) — желательно сделать сначала T-7-001, чтобы palettes-замена не смешалась с rebranding.

---

## Что нужно сделать

### Шаг 1. Положить ассет

`frontend/public/logo-supersymmetria.svg` — оригинал.
`frontend/public/favicon.ico` + `favicon-16x16.png` + `favicon-32x32.png` — собрать из логотипа.
`frontend/public/icon-192.png`, `icon-512.png` — для PWA manifest (если будет).

### Шаг 2. Заменить тексты «MsTechnics» в frontend

```bash
grep -rln "MsTechnics\|MSTechnics\|mstechnics" frontend/src/ --include='*.{ts,tsx,html}'
```

В каждом найденном месте — заменить пользовательский текст на «Суперсимметрия». **Не** трогать:
- import paths типа `from 'mstechnics-shared'` (если такие есть).
- URL `mstechnics.ru` если он где-то фигурирует в коде.
- Имена переменных вроде `mstechnicsConfig` — это код, не product surface.

Конкретные места, где **точно** надо менять:

- `frontend/index.html` → `<title>Суперсимметрия — система управления экранами</title>` + `<meta name="description">`.
- `frontend/src/pages/login/LoginPage.tsx` (или аналог) — заголовок над формой.
- `frontend/src/widgets/Header/` — логотип-картинка + текст.
- Footer, если есть.
- 404 / error pages — копирайт текст.

### Шаг 3. PWA manifest (если есть)

`frontend/public/manifest.webmanifest`:

```json
{
  "name": "Суперсимметрия",
  "short_name": "Суперсимметрия",
  "description": "Система управления экранами",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "theme_color": "#040f1d",
  "background_color": "#fafcff",
  "display": "standalone"
}
```

### Шаг 4. Бэкенд — только product-surface

```bash
grep -rln "MsTechnics" apps/ shared/ Config/ --include='*.py'
```

Что трогаем:
- Email templates (если есть): `subject`, `from_name`, signature → «Суперсимметрия».
- TG/MAX notification templates (`apps/notifications/migrations/000*_seed_templates.py` — **только текст**, не имена).
- Django admin `site_header`, `site_title`, `index_title` в `Config/urls.py` или `Config/admin.py`.
- API docs (`drf-spectacular`) — `SPECTACULAR_SETTINGS['TITLE'] = "Суперсимметрия API"`.

**Не трогаем:**
- Имена Django apps (`apps.core`, `apps.directory`, etc.).
- Имя БД (`mstechnics`).
- `package.json` name, `pyproject.toml` name — это идентификаторы, не UI.

### Шаг 5. README.md (опционально)

Если README — внутренний для разработчиков, можно оставить «MsTechnics» как кодовое имя проекта. Если он есть на главной репо для внешних читателей — короткий первый абзац: «Внутреннее имя — MsTechnics, бренд продукта — Суперсимметрия».

---

## Критерии приёмки

- [ ] Логотип SVG лежит в `frontend/public/`.
- [ ] Favicon заменён.
- [ ] PWA manifest обновлён (если есть).
- [ ] `grep -rln "MsTechnics" frontend/src/` — пусто (или только в комментариях / dev-only коде).
- [ ] Login страница и Header показывают новый логотип + «Суперсимметрия».
- [ ] `<title>` в браузере — «Суперсимметрия — …».
- [ ] Email/notification templates обновлены.
- [ ] Django admin показывает «Суперсимметрия» в заголовке.
- [ ] API docs (`/api/v1/docs/`) показывает «Суперсимметрия API».
- [ ] `frontend/build` + smoke на login зелёные.
- [ ] Отчёт в `08-reports/T-7-001.md`.

---

## Что НЕ делать

- **Не переименовывать** Django apps / Python modules / package.json name / БД.
- Не менять домен / SSL / DNS — это решение владельца.
- Не вводить новую палитру здесь — это T-7-002.
- Не делать dark mode toggle здесь — это T-7-002.
- Не вычищать абсолютно **все** упоминания «mstechnics» в комментариях и dev-доках — фокус на user-visible surface.

---

## Вопросы для архитектора

- [ ] Лого SVG получен? Если нет — задача в blocked до получения от дизайнера.
- [ ] Меняем ли копирайт год в footer? — **Ответ:** оставить как есть, отдельная задача.

---

## Отчёт по выполнению

(Заполняет кодер.)
