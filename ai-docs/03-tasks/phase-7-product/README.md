# Phase 7 — продуктовые требования владельца (раунд 2026-05-13)

Это **первая фаза после prod cutover**, в которой проект из режима рефакторинга переходит в режим продуктовой разработки. Источник требований — ответы владельца в [`07-frontend/owner-answers-2026-05-13.md`](../../07-frontend/owner-answers-2026-05-13.md).

Не все задачи Phase 7 закрываются параллельно — большая часть **blocked до prod stable + 2 недели**. Только rebranding/tokens могут идти параллельно с post-cutover окном (они frontend-only, не трогают БД).

---

## Группы задач

### A. Rebranding & визуальная переработка

| ID | Название | Статус | Часов | Зависит |
|---|---|---|---|---|
| [T-7-001](T-7-001-rebranding-supersymmetria.md) | Rebranding в UI: имя «Суперсимметрия», новый логотип | done | 1.5-2 | SVG-лого от дизайнера |
| [T-7-002](T-7-002-design-tokens-v2-dark-mode.md) | Design tokens v2 + dark mode + theme toggle | done | 3-4 | T-7-001 |

### B. Backend-модели (BC-breaking, blocked)

| ID | Название | Статус | Часов | Зависит |
|---|---|---|---|---|
| [T-7-003](T-7-003-multi-role-and-fine-grained-permissions.md) | Multi-role + fine-grained permissions (A5, Z5) | review (Wave 1+2 done, Wave 3 — отдельная итерация 2-4 нед) | 6-8 | — (владелец 2026-05-18: 2-недельный stability window отменён, прод-проверка через тестовый сервер) |
| T-7-004 | Departure ↔ Application: FK → ManyToMany (DE5 «гибкая» связь) | ready | 4-5 | — (то же, 2-нед окно снято) |
| [T-7-005](T-7-005-storage-extensions-and-low-stock.md) | Storage: PowerBlocks + Connectors + `low_stock_threshold=3` (Z3, Z4) | done | 2-3 + 1.5 | — |

### C. FSM + бизнес-логика

| ID | Название | Статус | Часов | Зависит |
|---|---|---|---|---|
| T-7-006 | Новый transition «service_decline» — сервисмен возвращает заявку (DV-S4) | blocked | 2-3 | T-7-003 |
| [T-7-007](T-7-007-panel-removal-conditional-reason.md) | Снятие панели: 2 сценария (в заявке `condition` required, без заявки optional) | done | 1.5-2 | — |
| T-7-008 | ConfirmDialog для опасных действий + useConfirmDialog хук (Md5) | review | 1 | — |

### D. Новые фичи (frontend + backend support)

| ID | Название | Статус | Часов | Зависит |
|---|---|---|---|---|
| [T-7-010](T-7-010-global-search.md) | Глобальный поиск через `/` (X1) — все 6 категорий | done | 4-6 | — |
| T-7-011 | Колокольчик уведомлений в хедере + unread counter (X2) — endpoint `/notifications/inbox/` + Bell с popover + localStorage read-state | review | 3-4 | — |
| T-7-012 | Звук при новой заявке + opt-in в Profile (A8) — Web Audio API beep, SSE-триггер на `application.create` | review | 1-2 | — (зависимость от T-7-011 снята: централизованный SOUND_EVENTS set) |
| [T-7-013](T-7-013-print-application-card.md) | Print-friendly карточка заявки (X4 — только заявка) | done | 2-3 | — |
| T-7-014 | История действий юзера в Profile (P2) — `useMyActivity` + UI секция | review | 1.5 | — |
| T-7-015 | Админ → ссылка восстановления пароля (L2) | blocked | 3-4 | T-7-003 (extra_perm `can_send_password_reset`) — теперь не stability, а просто после T-7-003 |

### E. Расширение каналов уведомлений

| ID | Название | Статус | Часов | Зависит |
|---|---|---|---|---|
| T-7-020 | ~~VK Workspace channel~~ | **CANCELLED** | — | Владелец 2026-05-17: «что это и для чего, не пойму» — продукт не используется |
| T-7-021 | VK Community Bot channel (A7) | blocked | 3-4 | Владелец заводит community-группу + bot token (личный VK API не подходит) |
| T-7-022 | Reorder channel fallback: **MAX → Telegram → Email** (упрощено после отмены T-7-020) | blocked | 0.3 | T-7-021 опционально |

### F. Дополнительный UX

| ID | Название | Статус | Часов | Зависит |
|---|---|---|---|---|
| T-7-030 | Sortable экранов внутри города (D6) | done | 1 | — |
| T-7-031 | Поиск/фильтр городов (10+) (D7) | done | 1 | — |
| T-7-032 | Quick-links на карточках экранов (D5) — ЗИП/Заявки/История | review | 1-1.5 | — |
| T-7-033 | DnD ZIP колонок (Z2) — HTML5 native, drop в zip/hand/service | review | 2 | T-7-005 |
| T-7-034 | Low-stock highlight расходников `count < N` (Z4) | review | 0.5 | T-7-005 |
| T-7-035 | Создание панели (Z7) — backend POST `/panels/` + UI PanelCreateButton | review | 1.5 + backend | — |
| T-7-036 | Удаление панели (Z8, admin-only) — backend DELETE + UI с ConfirmDialog | review | 1 + backend | — |

### H. Design Round 4 integration (от дизайнера Claude Design, 2026-05-19)

Большой пакет полировки фактически внедрённого Phase 7 UI. Дизайнер сдал 4 ai-docs (audit/polish/microinteractions/mobile-plan) и исторический пакет из 17 готовых патчей + INTEGRATION.md. Пакет уже интегрирован и удалён из репо cleanup-PR'ом.

| ID | Название | Статус | Часов | Источник |
|---|---|---|---|---|
| [T-7-100](T-7-100-design-round-4-integration.md) | **Интеграция Design Round 4 (10 PR'ов)** | review | 25-30 (5-6 дней) | Designer handoff 2026-05-19 |
| [T-7-followup-applications-display-city](T-7-followup-applications-display-city.md) | Backend: `DisplayMiniSerializer.city` для PR-10 dashboard-app-link | review | 0.3 | Q3 от дизайнера |
| [T-7-followup-display-aggregated-condition](T-7-followup-display-aggregated-condition.md) | Backend: `aggregated_condition` в `DisplayListSerializer` для DL-003 status bullet | review | 0.5 | Q1 от дизайнера |
| [T-7-followup-bell-deeplink-resolve](T-7-followup-bell-deeplink-resolve.md) | Backend: `deep_link_path` в notification inbox для bell deep-link | review | 1-1.5 | Опционально, после applications-display-city теряет смысл |

**Артефакты дизайнера в репо:**

- `ai-docs/07-frontend/design-handoff-round-4.md` — TL;DR и план.
- `ai-docs/07-frontend/design-audit-2026-05-19.md` — 43 пункта баг-репорта (9 P0 / 24 P1 / 10 P2).
- `ai-docs/07-frontend/design-polish-round-3.md` — JSX-диффы для сложных мест (ZIP, EventTimeline, TransitionLabels).
- `ai-docs/07-frontend/microinteractions-a11y-fixes.md` — 20 точечных fix'ов.
- `ai-docs/07-frontend/mobile-adaptation-plan.md` — план Phase 8.
- Исторический пакет `_design-patches-round-4/frontend-patches/` был использован для PR-1..10 и удалён cleanup-PR'ом; источником истины остаются `ai-docs/07-frontend/*` и отчёты `08-reports/T-7-100-pr-*.md`.

### G. Technical debt из ревью T-7-005/007/010 (2026-05-17)

| ID | Название | Статус | Часов | Источник |
|---|---|---|---|---|
| T-7-040 | Прогнать миграцию T-7-005 (`PowerBlocks`/`Connectors` + `low_stock_threshold`) на копии прод-БД | review | 0.5 | T-7-005 отчёт: «копия прод-БД недоступна была» |
| T-7-041 | Стабилизировать генерацию `api-schema.yaml` — снизить unrelated diff при `make api-schema` | review | 1-2 | T-7-005/010 отчёты |
| T-7-042 | Починить глобальный `npm run typecheck` (pre-existing ошибки в `react-hook-form` и legacy типах) | review | 1-2 | T-7-005/007/010 отчёты |
| T-7-043 | Surfaced search schema в `frontend/src/shared/api/schema.d.ts` (сейчас локальные типы в `features/search/types.ts`) | review | 0.5-1 | T-7-010 отчёт |

---

## Total

- **A. Rebranding** — ~5 часов, можно делать параллельно с post-cutover окном.
- **B. Backend модели** — ~12-16 часов, blocked.
- **C. FSM** — ~4-6 часов, частично blocked.
- **D. Новые фичи** — ~12-19 часов.
- **E. Каналы уведомлений** — ~8-10 часов, blocked до получения API от владельца.
- **F. UX мелочёвка** — ~8-9 часов.

**Полный объём Phase 7:** ~50-65 часов.

---

## Порядок выполнения (рекомендация)

1. **Phase 7 A** (T-7-001, T-7-002) — параллельно с T-6-001 cutover. Frontend не трогает БД.
2. **2 недели prod stable** — наблюдение.
3. **Phase 7 B** (T-7-003, T-7-004, T-7-005) — BC-breaking. Делать **последовательно**, не параллельно.
4. **Phase 7 C, D, F** — после B, потому что большинство зависит от моделей.
5. **Phase 7 E** — параллельно с C/D/F, когда владелец предоставит API доступы.

---

## Open questions для владельца

Ответы владельца раунд 2026-05-16:

| ID | Вопрос | Ответ |
|---|---|---|
| T-7-010 | Глобальный поиск — какие категории? | ✅ **Все 6 из списка** (экраны, панели, заявки, выезды, юзеры, ЗИП-расходники) |
| T-7-013 | Что печатать? | ✅ **Карточка заявки** (только это, не выезд/экран/отчёты) |
| T-7-020 | VK Workspace API? | 🟡 **«пока хз»** — остаётся blocked до уточнения API/документации |

Закрытые ранее (через `owner-answers-2026-05-13.md`):

- A1..A8, L1..L6, D5..D7, DV-M7/C3/C4/C7/S4/S6/S7/S8, Z2/Z3/Z4/Z5/Z7/Z8, DE2/DE3/DE5, P1/P2/P3, Md5, X1..X4.

Получено в этом раунде дополнительно:

- ✅ **Брендбук Суперсимметрия 2026 v1.0** + **Гайдбук v2.0** — полные PDF получены, выжимка для разработки в [`07-frontend/brand-guidelines-supersymmetria.md`](../../07-frontend/brand-guidelines-supersymmetria.md).

Всё ещё открыто (для будущих задач):

- **T-7-007:** default-состояние при «снятии панели без выбора» — `breakdown` или новое `removed`?
- **T-7-021:** какой VK bot — community group или личный аккаунт? Token есть?
- **T-7-034:** пороги `low_stock_threshold` для каждого расходника — конкретные числа.
- **Лицензии на шрифты** TT Travels Text + Biform — есть, нужно купить или идём на Inter fallback?
- **SVG-логотип** — векторный исходник от дизайнера.
