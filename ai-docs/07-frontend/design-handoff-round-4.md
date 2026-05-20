# Round 4 hand-off для кодера — «Суперсимметрия»

> **Дата:** 2026-05-19
> **От:** дизайнер (Round 4 / Claude Design)
> **К:** кодеру (Claude Opus или человек)
> **Объём:** ~5–6 рабочих дней.
> **Статус:** исторический handoff. Пакет `frontend-patches/` уже интегрирован и удалён из репо cleanup-PR'ом; для фактического результата см. `ai-docs/08-reports/T-7-100-pr-*.md`.

---

## TL;DR

Аудит фактически внедрённого Phase 7 UI выявил **9 P0**, **24 P1**, **10 P2** проблем. Самые крупные:

1. **D5/D6/D7 (sort/filter/quick-links) физически нет в проде** — фичи реализованы в мёртвом `DepartmentPage.tsx`, но App.tsx маршрутизирует `DepartmentListPage.tsx`. Слияние — основной PR этого раунда.
2. **`DeparturesPage` использует мёртвые `bg-surface-*` классы** — в живом UI рендерится без фона/границ. Это P0, исправляется одним PR.
3. **17 эмодзи в production-UI** (ZipPage, EventTimeline, EmptyState, TRANSITION_LABELS) — против явного запрета брендгайда §3 и §5. Замена на lucide-react.
4. **`<html class="dark">` хардкод + Inter в шрифтах** — техдолг от старой темы.
5. **`--bg-2` (Серебро) одинаковая в обеих темах** — используется как surface, в dark светло-серый «обрубок».

После применения пакета — UI соответствует брендгайду «Суперсимметрия», dark theme работает корректно, фичи Phase 7 фактически включены.

---

## Что лежало в исходном пакете

```
.
├── HANDOFF.md                          ← ты здесь
├── ai-docs/07-frontend/
│   ├── design-audit-2026-05-19.md      ← баг-репорт, 43 пункта, severity-grouped
│   ├── design-polish-round-3.md        ← JSX-диффы для 5 экранов Round-3 + 6 компонентов Phase 7
│   ├── microinteractions-a11y-fixes.md ← 20 точечных fix'ов: focus rings, skeletons, transitions, ARIA, motion
│   └── mobile-adaptation-plan.md       ← план Phase 8 / зоны D
├── frontend-patches/                  ← исторический пакет, удалён после интеграции
│   ├── README.md                       ← карта файлов пакета
│   ├── INTEGRATION.md                  ← пошаговый план интеграции, 10 PR'ов ←★★★
│   ├── index.html                      ← drop-in
│   ├── app/globals.css                 ← drop-in
│   ├── app/styles/tokens-additions.css.snippet  ← append-only
│   ├── app/App.tsx-toaster.snippet     ← inline-замена
│   ├── shared/lib/useIsMobile.ts       ← new
│   ├── shared/ui/Toggle.tsx            ← new
│   ├── shared/ui/EmptyState.tsx        ← drop-in
│   ├── shared/ui/ThemeToggle.tsx       ← drop-in
│   ├── shared/ui/Modal.tsx             ← drop-in
│   ├── pages/login/LoginPage.tsx       ← drop-in
│   ├── pages/profile/...snippet        ← inline-замена секции
│   ├── pages/departures/DeparturesPage.tsx        ← drop-in
│   ├── pages/department/DepartmentListPage.tsx    ← drop-in (большой merge)
│   └── widgets/navigation/{Header,NotificationBell}.tsx  ← drop-in
├── design-system-preview.html          ← было в handoff-пакете, в текущем репо отсутствует
├── mobile-sketches.html                ← было в handoff-пакете, в текущем репо отсутствует
└── (...)
```

---

## Порядок работы

1. **Прочитать** `ai-docs/07-frontend/design-audit-2026-05-19.md` — поймёшь **что** и **почему**.
2. **Открыть** `ai-docs/07-frontend/design-audit-2026-05-19.md` и `design-polish-round-3.md` — это основной surviving reference по правкам.
3. Для фактической последовательности интеграции см. `ai-docs/08-reports/T-7-100-pr-1.md` ... `T-7-100-pr-11.md`.
4. Каждый PR — отдельный коммит с reference на followup ID. Не складывай всё в один PR.
5. Для **mobile** и **tablet** — это **Phase 8**, не сейчас. Эскизы лежат в `mobile-sketches.html` как direction.
6. **Не трогать** (явные ограничения от владельца):
   - `tokens.css` палитру (только append в конец через snippet);
   - шрифты (TT Travels уже подключен, Biform ждём);
   - API `<Button>`, `<Modal>`, `<ConfirmDialog>` — только косметика.

---

## Что от тебя ждётся

- **5–6 дней работы**, разбитых на 10 PR'ов.
- Каждый PR смержить отдельно, чтобы можно было откатить точечно.
- **Не пиши новых компонентов**, кроме `Toggle.tsx` и `useIsMobile.ts` — они уже даны.
- **Не выдумывай решения** для open questions — они помечены в документах. Поднимай архитектору.

## Open questions (для архитектора, не для кодера)

| ID | Вопрос | Блокирует |
|---|---|---|
| 1 | `aggregated_condition` экрана в DTO `/displays/`? | DL-003 (status bullet) |
| 2 | `/dashboard/` отдаёт `app.display.city.slug`? | M-001 (PR-10 dashboard-app-link) |
| 3 | В эталоне Round-0 DisplayView были bottom-tabs? | DV-003 |
| 4 | PWA для phone — нужна? Минимальный Android? | Phase 8 |
| 5 | Control-роль на phone доступна? | Phase 8 |

Кодеру эти вопросы не нужны для PR-1..9. Для PR-10 нужен ответ на #2.

---

## Контракт качества

После применения всего пакета, кодер должен подтвердить:

- [ ] `git grep 'bg-surface-'` — 0 совпадений в `frontend/src/`.
- [ ] `git grep 'text-text-'` — 0 совпадений.
- [ ] `git grep -P '[\\x{1F300}-\\x{1FAFF}]'` в production-коде (исключая тесты и Condition.icon из БД) — 0.
- [ ] `git grep -E '#[0-9a-fA-F]{3,8}'` — только в `tokens.css` и `ApplicationDetailSheet*` (печать). Нигде больше.
- [ ] Light и dark mode визуально проверены на всех 9 экранах.
- [ ] Tab по любой странице — каждый интерактивный элемент имеет видимый focus ring.
- [ ] `npm test` зелёный.

---

## Ссылки на конкретные документы

| Что хочу | Куда смотреть |
|---|---|
| «Что вообще плохо в текущем UI?» | `ai-docs/07-frontend/design-audit-2026-05-19.md` |
| «Как ровно интегрировали этот пакет?» | `ai-docs/08-reports/T-7-100-pr-1.md` ... `T-7-100-pr-11.md` |
| «Как должен выглядеть компонент X?» | `ai-docs/07-frontend/design-audit-2026-05-19.md` + `design-polish-round-3.md` |
| «Что делать с микровзаимодействиями (focus, transitions, ARIA)?» | `ai-docs/07-frontend/microinteractions-a11y-fixes.md` |
| «JSX-дифф для конкретного места» | `ai-docs/07-frontend/design-polish-round-3.md` |
| «Что насчёт мобильной версии?» | `ai-docs/07-frontend/mobile-adaptation-plan.md` + `mobile-sketches.html` |

---

Удачи. Если что-то непонятно — открой соответствующий .md в `ai-docs/`, там объяснено «почему», не только «как».
