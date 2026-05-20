# Дизайн-бриф для Claude Design (раунд 4)

> **Цель раунда:** comprehensive design audit + полировка всех экранов **после фактического внедрения Phase 7**.
> **Дата:** 2026-05-19
> **Контекст:** Phase 7 фронт-блок практически закрыт кодером — все компоненты есть, новая палитра подключена, dark mode работает, NotificationBell в Header, DnD в ZIP, и т.д. Теперь нужен **проход глазами дизайнера** по всему UI: что в брендбук попало, что нет, что криво в dark theme, что не работает на планшете.

---

## Часть 1. Промпт для Claude Design (копировать целиком)

```
Привет, Claude Design.

В предыдущих раундах ты сделал эталон Display View v2 + Main Menu v2 (Round 0)
и 5 базовых экранов под этот эталон (Round 3). Спасибо.

С тех пор:
1) Принят новый брендинг «Суперсимметрия» — старое имя `MsTechnics` остаётся
   только в коде/БД/домене. UI везде «Суперсимметрия». Решение в ADR-002.
2) Получены брендбук (PDF) + гайдбук (PDF) от агентства Be Art. Выжимка для
   разработки — в `ai-docs/07-frontend/brand-guidelines-supersymmetria.md`.
   Палитра — `brand-palette-supersymmetria.md`. Логотип SVG + шрифт TT Travels
   получены и лежат в `frontend/public/`.
3) Кодер (Claude Opus в роли coder) полностью внедрил Phase 7 фронт-блок:
   rebranding, tokens v2, dark mode + theme toggle, поиск через Cmd+K,
   карточка заявки для печати, ConfirmDialog, история юзера в Profile,
   звуковые уведомления, колокольчик в Header, DnD ZIP колонок, CRUD
   панелей через UI, sort+фильтр городов, quick-links на карточках.
4) Владелец отказался от 2-недельного prod-stable window — вместо этого
   поднимает тестовый сервер с прод-дампом и кликает руками.

Это **не «всё переделать»**. Это **дизайн-аудит** реально внедрённого UI
+ полировка без переделки архитектуры. Большая часть твоей работы —
СКАЗАТЬ что переделать, а не самой переделывать.

ЧТО ОТ ТЕБЯ ЖДУ В ЭТОМ РАУНДЕ:

A. AUDIT — пройди ножками по всем 9 экранам в обеих темах и составь
   баг-лист «что сейчас не по брендбуку / не по эталону». Формат:
   [экран] / [light|dark] / [проблема] / [предлагаемое исправление].

B. ПЯТЬ ЭКРАНОВ POLISH — для каждого из 5 экранов Round-3 проверь как
   реально получилось vs твой эталон. Где есть отклонения — JSX-патчи.

C. НОВЫЕ КОМПОНЕНТЫ PHASE 7 REVIEW — проверь 6 компонентов от Opus
   (ConfirmDialog, NotificationBell, CreatePanelModal, PanelDeleteButton,
   ThemeToggle, новая секция «Звуковые уведомления» в Profile).
   Соответствует ли visual системе? Где «программистский UI», который
   надо подтянуть.

D. MOBILE / ANDROID ADAPTATION — A2 ответ владельца: «сервисмены работают
   со стационарных компов, ноутбуков и Android-телефонов». Сейчас UI
   только desktop (≥1280). Нужно: breakpoints, что сжимать/прятать на
   tablet (~10"), что показать на phone (~6"). НЕ ВСЁ — только то, что
   реально нужно сервисмену в полевых условиях.

E. MICROINTERACTIONS + ACCESSIBILITY — focus rings, hover states, loading
   skeletons (уже есть, но единообразны ли?), анимация для notification
   bell, transitions для theme switch, ARIA labels на icon-buttons.

ПРАВИЛО ПЕРЕД КАЖДЫМ ИЗ A-E:

Сначала ВЕРБАЛЬНЫЙ план — что ты планируешь делать, где. Только после
моего OK — JSX и скриншоты. Это сократит итерации.

ЧТО НЕ ДЕЛАТЬ:

— Не переписывать tokens.css. Палитра зафиксирована брендбуком.
— Не менять шрифты (TT Travels уже подключен, Biform ждём, временно
  тоже TT Travels для body).
— Не предлагать новые цвета. Только из палитры.
— Не делать админку для управления цветами / шрифтами. Бренд статичен.
— Не предлагать переписать ConfirmDialog/Modal/Button API — кодер уже
  написал, тесты зелёные, юзается. Только косметика.
— Не предлагать «давайте уберём dark mode» — это требование владельца A3.
— Не предлагать переход на CSS-in-JS / другой CSS framework. У нас
  Tailwind + CSS vars, остаёмся.
— Не предлагай 2-3 варианта — рекомендуй один с обоснованием.

ЧТО ВЗЯТЬ С СОБОЙ ОБЯЗАТЕЛЬНО:

— frontend/src/app/styles/tokens.css — это источник правды по цветам.
— frontend/src/app/styles/fonts.css — @font-face.
— ai-docs/07-frontend/brand-guidelines-supersymmetria.md — полный свод.
— ai-docs/07-frontend/brand-palette-supersymmetria.md — палитра с hex'ами.
— ai-docs/07-frontend/screens-map.md — карта экранов и их состояний.
— ai-docs/07-frontend/owner-answers-2026-05-13.md — ответы владельца
  по UX (включая раунд 2026-05-17 про шрифты/SVG/snятие панели).
— Логотип: frontend/public/logo-supersymmetria.svg (горизонталь,
  currentColor) + frontend/public/logo-supersymmetria-black.svg
  (для печати).
— Брендбук + гайдбук (PDF) — в dumps/brand-pdf/ локально, не в git.
  Спросишь у владельца, он пришлёт.

ЕСЛИ НЕОБХОДИМО ВЫЗВАТЬ КОДЕРА (Claude Opus) для bug-fix'а:

Не правь сама бэкенд-логику и FSM. Дай мне список того, что нужно
исправить в коде — я передам кодеру отдельной задачей T-7-followup-xxx.
```

---

## Часть 2. Контекст — что уже сделано

### Брендинг

- ✅ Имя «Суперсимметрия» во всех user-visible местах (`<title>`, login, header, footer, email).
- ✅ Логотип SVG (горизонталь): `frontend/public/logo-supersymmetria.svg`.
- ✅ Чёрно-белая версия для печати: `frontend/public/logo-supersymmetria-black.svg`.
- ✅ Favicon + 192/512 PNG для PWA — `frontend/public/`.
- ✅ Title в Django admin + DRF spectacular «Суперсимметрия API».
- ✅ Email signature.
- 🟡 Нет отдельного **знака** (без надписи) для favicon — сейчас favicon собран из общего wordmark. Если у дизайнера будет квадратный mark — переэкспортируем.

### Палитра v2 + Dark mode

- ✅ `tokens.css` v2 содержит брендовую палитру (Призрачно белый / Платина / Серебро / Ночное небо / Ночная дымка / Солнечный луч / Ночное окно / Закат).
- ✅ `[data-theme="dark"]` инвертирует фоны/текст; акцент остаётся ярко-жёлтым.
- ✅ `prefers-color-scheme` fallback когда юзер не выбрал явно.
- ✅ Theme toggle: кнопка в Header (☀️/🌙) + radio-group в Profile с 3 опциями (light/dark/system).
- ✅ WCAG ratios проверены — таблица в отчёте T-7-002.

### Шрифты

- ✅ **TT Travels** (11 весов в WOFF+TTF, woff2 сгенерированы для Regular/Medium/Bold) — `frontend/public/fonts/tt-travels/`.
- ✅ `@font-face` в `frontend/src/app/styles/fonts.css`.
- 🟡 **Biform Regular** (по гайдбуку — наборный) **ещё не получен**. Временно `--font-body` указывает на TT Travels. Когда Biform будет — отдельный mini-PR.
- 🟡 Дополнение: гайдбук указывает «TT Travels **Text**» (typetype.ru), у владельца лицензия на просто «TT Travels» (Transfonter 2017). Это разные родственные шрифты. На практике для UI разница не критична.

### Внедрённые компоненты Phase 7 (для аудита)

| Компонент | Файл | Назначение |
|---|---|---|
| **ConfirmDialog** | `src/shared/ui/ConfirmDialog.tsx` | Универсальный «Точно?» для опасных действий (Md5). Используется в PanelDeleteButton. |
| **NotificationBell** | `src/widgets/navigation/NotificationBell.tsx` | Колокольчик в Header с бейджем и popover (X2). |
| **PanelCreateButton** | `src/features/panels/PanelCreateButton.tsx` | Кнопка «+ Панель» в шапке ZIP + inline-модалка (Z7). |
| **PanelDeleteButton** | `src/features/panels/PanelDeleteButton.tsx` | Кнопка удаления панели admin-only (Z8). |
| **ThemeToggle** | `src/shared/ui/ThemeToggle.tsx` | Кнопка ☀️/🌙 в Header. |
| **Profile sound section** | `src/pages/profile/ProfilePage.tsx` (часть) | Секция «Звуковые уведомления» — Volume2/VolumeX, toggle, кнопка «Прослушать» (A8). |
| **Profile activity section** | `src/pages/profile/ProfilePage.tsx` (часть) | Секция «История действий» (P2). |
| **CommandPalette** | `src/shared/ui/CommandPalette.tsx` (T-7-010) | Глобальный поиск через `/` или `Cmd+K` (X1). |
| **DnD on ZipPage** | `src/pages/zip/ZipPage.tsx` (часть) | HTML5 native DnD для перемещения панелей между колонками (Z2). |
| **Quick-links** | `src/pages/department/DepartmentPage.tsx` (часть) | ЗИП/Заявки/История под карточкой экрана (D5). |
| **Sort + city filter** | `src/pages/department/DepartmentPage.tsx` (часть) | Сортировка экранов + поиск города (D6/D7). |
| **PrintApplicationSheet** | `src/entities/application/ApplicationDetailSheet.tsx` + CSS | `@media print` карточка заявки для сервисмена (X4). |

### Что владелец явно сказал НЕ ДЕЛАТЬ

- Не делать SPA-админку — Django admin.
- Не делать мобильную версию **раньше** (Round 3) — теперь это **отменено**, Mobile сейчас в zone D.
- Не предлагать 2-3 варианта — один с обоснованием.

---

## Часть 3. ПЯТЬ ЗОН РАБОТЫ ДЛЯ ДИЗАЙНЕРА

### Зона A — Comprehensive design audit (4-6 часов)

**Что:** пройти ножками по UI в light + dark теме, составить **баг-репорт** для кодера.

**Покрытие:**

1. `/login` — экран входа.
2. `/menu` — главная.
3. `/monitoring`, `/control`, `/service` — DepartmentList (списки экранов).
4. `/monitoring/:city/:slug` — DisplayView мониторинг.
5. `/control/:city/:slug` — DisplayView контроль.
6. `/service/:city/:slug` — DisplayView сервис (эталон).
7. `/zip` и `/zip/:slug` — ZIP overview.
8. `/departures` — список выездов.
9. `/lk` — Profile (3 секции: Личный кабинет / Тема / Звук / История).

**Формат каждой записи в баг-репорте:**

```
[A-001] /login / dark / Логотип wordmark рендерится цветным (currentColor
        работает через <img>, не работает через JSX import).
        FIX: использовать `vite-plugin-svgr` или `<svg>` inline.
```

Минимум 30 пунктов ожидается на 9 экранов × 2 темы.

**Особое внимание:**

- Использует ли компонент **CSS-переменные** или **hardcoded hex**? Hex недопустим (кроме `Condition.color` из БД).
- Есть ли `surface-2` / `bg-bg-1` / другая legacy classnaming? Должно быть единообразие.
- Высоты строк, паддинги — есть ли «дрожание» от страницы к странице?
- Где остался **MsTechnics** в текстах (любых, включая subtitle/placeholder/error message)?

**Deliverable:** `ai-docs/07-frontend/design-audit-2026-05-19.md` — таблица багов.

---

### Зона B — Полировка 5 экранов Round-3 (6-8 часов)

Round-3 у тебя были эскизы. Кодер реализовал. Теперь **сравни** твой эскиз с тем, что фактически в коде. Где отклонения — JSX-патчи.

#### B.1 DepartmentList

- Сейчас в коде есть **новые элементы от меня** (sort dropdown, city filter, quick-links под карточкой). Они логически работают, но **визуально** могут не вписываться в эталон.
- Проверь: плотность toolbar (сейчас `flex-wrap items-end justify-between gap-4`), стиль `<select>` и `<input type="search">` (нативные, не stylized).
- Quick-links под карточкой — три текстовых ссылки с микро-иконками. Это **минималистично**, но возможно нужно увеличить touch target для tablet/mobile.

#### B.2 DisplayView (3 роли)

- Эталон — сервис (Round 0). Сейчас в коде он `DisplayViewPage`, общий для трёх ролей с прокидыванием `department` prop.
- Проверь как варианты для control и monitoring отличаются от эталона. Должны ли отличаться визуально, или только по доступным actions?

#### B.3 ZIP Overview

- 6 колонок: 4 отдела (zip/hand/service/monitor) + Расходники + История.
- Сейчас 4 «отдельных» отдела + расходники справа. После моего DnD (T-7-033) колонки 1-3 принимают drop, monitor — нет. Есть outline-индикация dragHover.
- Проверь: visual hierarchy между панелями (chip), расходниками (карточка с count) и историей (timeline). Нет ли «каши»?

#### B.4 Departures

- Список выездов. Проверь как сейчас рендерится таблица/карточки.
- Гибкая связь заявка↔выезд (DE5) пока не реализована (blocked T-7-004). Но визуально нужно подготовиться: «эта заявка входит в выезды #5 и #7» как показывать?

#### B.5 Модалки transition + 5 specialized

- TransitionModal + CreateApplicationModal + PanelRemovalModal + PanelChange* + PanelMoveToCell + теперь ConfirmDialog от меня.
- Все ли модалки используют один `<Modal>` основной компонент? Где есть отличия — это норма или баг?

**Deliverable для каждого экрана:** список конкретных JSX-патчей (3-10 на экран).

---

### Зона C — Новые компоненты Phase 7 review (3-4 часа)

Проверь 6+ компонентов от Opus (см. таблицу в Часть 2). Для каждого:

1. **Соответствует ли visual системе?** Не «программистский UI» ли?
2. **В обеих темах** ли работает?
3. **Микро-взаимодействия** — есть ли hover/focus/active?
4. **Иконка из lucide-react** ли (а не emoji/raw SVG)?

Особо ожидаются комментарии по:

- **ConfirmDialog** — заголовок «Точно?» дефолтный. Должен ли быть subtitle с описанием действия? Или достаточно как есть?
- **NotificationBell** — popover 250px ширины. На tablet/phone норм? Когда юзер впервые видит — понимает ли что это?
- **PanelCreateButton** — inline `<select>`. Эстетично, но не выпадающий комбобокс. Норм для 8 экранов?
- **PanelDeleteButton** — title диалога показывает имя панели. Когда есть backend ошибка, она тоже в title (переписывает «Удалить панель X?»). Не запутает ли это юзера?
- **Profile sound section** — кнопка «Прослушать» рядом с toggle. Норм UX?
- **Profile activity section** — плоский список вместо timeline. Альтернатива — связать с EventTimeline компонентом из DisplayView?

**Deliverable:** короткий обзор по каждому из 6+ компонентов (1-2 параграфа на каждый) + список конкретных правок.

---

### Зона D — Mobile / Android adaptation (8-10 часов)

**Новое требование** (A2 ответ владельца): сервисмены работают **со стационарных компов, ноутбуков и Android-телефонов**.

Сейчас весь UI рассчитан на ≥ 1280px desktop. Нужно:

1. **Breakpoints определить:**
   - `mobile` — 360-767px (Android phone, портретная)
   - `tablet` — 768-1023px (Android планшет, ноутбук в split)
   - `desktop` — ≥ 1024px

2. **Что критично для сервисмена в полевых условиях:**
   - Посмотреть **свои назначенные заявки** (DisplayView / service, но фильтр «мои»).
   - **Снять / поставить панель** — модалка с фото-аплоадом.
   - **Изменить condition** панели (быстрый action).
   - **Открыть карточку заявки** для печати — здесь печать с phone не работает, но **открыть на чтение** — да.

3. **Что показывать на phone (≤ 767px):**
   - Login, Menu (карточки в 1 столбец).
   - DepartmentList без grid'а — список карточек.
   - DisplayView — упрощённый вид: нет сетки экрана **визуально**, только список заявок с возможностью открыть конкретную.
   - **NO**: ZIP (нет смысла на phone — это для офиса).
   - **NO**: Departures (это для контроля, не для сервисмена в поле).
   - **NO**: глобальный поиск через `/` (нет физической клавиши).
   - Notification bell — есть, popover full-width.

4. **Что меняется на tablet (768-1023px):**
   - DisplayView — сетка экрана сжимается, RightRail сворачивается в bottom-sheet.
   - ZIP — все 6 колонок в одну строку — невозможно. Переход на табы по отделам.

**Deliverable:**
- `ai-docs/07-frontend/mobile-adaptation-plan.md` — план breakpoints + что показывать на каждом.
- JSX-эскизы для **mobile**: Login, Menu, DepartmentList, DisplayView service.
- Tailwind responsive utilities (`md:`, `lg:`, `xl:`) — где, что.

---

### Зона E — Microinteractions + accessibility (3-4 часа)

Точечная полировка деталей:

1. **Focus rings** — все интерактивные элементы (button, input, select, link) должны иметь видимый focus при клавиатурной навигации. Сейчас не везде.
2. **Loading states** — `<Skeleton>` есть, но единообразен ли по плотности? Сейчас в разных местах разный rows/height.
3. **Theme switch transition** — пока резкий. Добавить `transition: background-color 0.15s` на body? Или это вызовет flash?
4. **Notification bell** — pulse-анимация когда приходит новый item (subtle).
5. **DnD** в ZIP — outline `2px dashed var(--accent)` при hover. Достаточно? Может, тонкая прозрачность 50% на исходной колонке?
6. **ARIA** — каждый icon-button должен иметь `aria-label`. Сейчас часть есть, часть нет.
7. **Toast** — сейчас `sonner` дефолтный. Подкрашен ли он темой?
8. **Кнопки в Header** — text-fg-mute vs text-fg-dim — выбрать одно и держать единообразно.

**Deliverable:** список из 20-30 точечных fix'ов с конкретными CSS-патчами.

---

## Часть 4. Что владелец отвечал на UX (выжимка из owner-answers-2026-05-13.md)

| ID | Ответ владельца | Что это значит для тебя как дизайнера |
|---|---|---|
| A1 | Desktop + mobile mixed | Zone D обязательна |
| A2 | Сервисмены — комп/ноут/Android | Zone D обязательна |
| A3 | Тёмная тема нужна | Обе темы проверять параллельно |
| A8 | Звук при новой заявке | Bell + sound опция в Profile |
| D5 | Quick-links на карточке экрана | Сделано, проверь визуал |
| D6 | Сортировка экранов в городе | Сделано, проверь |
| D7 | Поиск/фильтр городов при 10+ | Сделано, проверь |
| DV-M7 | Пустая ячейка — чёрный | Не трогать |
| Md5 | Подтверждение «Точно?» | ConfirmDialog — проверь нет ли визуального дисбаланса |
| X1 | Глобальный поиск через `/` | CommandPalette — проверь визуал |
| X2 | Колокольчик уведомлений | NotificationBell — проверь визуал |
| X4 | Печать карточки заявки | ApplicationDetailSheet — проверь PDF preview |

---

## Часть 5. Открытые вопросы для архитектора (ты возвращаешь, я отвечаю)

Дизайнер задаёт **в ответном сообщении** до начала работы:

- [ ] Слоган «Соединяем важное» — показывать в footer? На login subtitle?
- [ ] Дескриптор «Бюро визуальных коммуникаций» — где, кроме email подписи?
- [ ] Маркерное выделение из брендбука (жёлтый highlighter на ключевых словах) — используем где-то в UI? Search match — это уместно. Где ещё?
- [ ] Стилеобразующая рамка «машинное зрение» — точно не использовать в табличном UI?
- [ ] На mobile фильтрация заявок по «мои» / «все» — где placement? Tab? Filter chip?
- [ ] Touch target минимум — 44px? 48px Material? Что берём?
- [ ] Для печати — лого только чёрный или допустимо «outline» вариант?

---

## Часть 6. Deliverables — чек-лист

В конце раунда от дизайнера ожидается **минимум**:

- [ ] `ai-docs/07-frontend/design-audit-2026-05-19.md` — баг-репорт ≥ 30 пунктов.
- [ ] `ai-docs/07-frontend/mobile-adaptation-plan.md` — план + breakpoints.
- [ ] JSX-патчи для 5 экранов Round-3 (zone B).
- [ ] Обзор новых компонентов (zone C) — 6+ заметок.
- [ ] Список 20-30 точечных fix'ов (zone E).
- [ ] **Что НЕ сделано в этом раунде** — отдельный раздел с обоснованием.

**Не ожидается:**
- Полный mobile-redesign (это отдельный последующий раунд).
- Переделка модалок «с нуля».
- Новая палитра / шрифты / темы.
- Storybook (мелкое замечание из прошлых ревью).

---

## Часть 7. Артефакты / референсы для дизайнера

Когда владелец передаёт проект, проверь что доступны:

- [ ] **Брендбук PDF** — `dumps/brand-pdf/brendbook-fitz.txt` (text-extract) или оригинал у владельца.
- [ ] **Гайдбук PDF** — там же.
- [ ] `ai-docs/07-frontend/brand-guidelines-supersymmetria.md` — выжимка от архитектора.
- [ ] `ai-docs/07-frontend/brand-palette-supersymmetria.md` — палитра.
- [ ] `ai-docs/07-frontend/screens-map.md` — карта экранов.
- [ ] `ai-docs/07-frontend/states-and-flows.md` — flows по ролям.
- [ ] `ai-docs/07-frontend/api-contract.md` — API правда (если потребуется проверить какие данные есть).
- [ ] `ai-docs/07-frontend/owner-answers-2026-05-13.md` — ответы владельца (включая раунд 2026-05-17).
- [ ] `ai-docs/08-reports/T-7-batch-2026-05-19.md` — что Opus внедрил последним раундом.
- [ ] `ai-docs/adr/ADR-002-rebranding-supersymmetria.md` — решение по rebranding.
- [ ] Текущий `frontend/src/` — реальный код.
- [ ] Логотип SVG + чёрно-белая версия + favicon + woff2 шрифты — в `frontend/public/`.

---

## Часть 8. Когда дизайнер сдаёт работу — что делает архитектор

1. Принимаю баг-репорт и patches.
2. Разбираю на конкретные задачи: какие — точечные (`T-7-followup-<screen>-design`), какие — части следующих P-задач.
3. Для каждого визуального fix'а в коде Opus — мини-задача кодеру в `03-tasks/phase-7-product/`.
4. Mobile-план идёт отдельной фазой — Phase 8 «Mobile adaptation» или вписывается в существующую.
5. Обновляю `screens-map.md` под актуальное состояние.

---

## Что НЕ входит в этот раунд (отложено)

- Полный mobile-redesign (только план в Round-4, исполнение в Round-5).
- Дизайн-система с Storybook (отдельный проект).
- Animated micro-interactions на уровне Framer Motion (на этом масштабе overkill).
- Брендинговая «рамка машинного зрения» в UI (для маркетинговых материалов, не для рабочего инструмента).

---

*Файл готовится архитектором. Передаётся владельцу. Владелец прикрепляет к этому файлу:*
1. *Свежий ZIP всего проекта.*
2. *Два PDF (брендбук + гайдбук) если у дизайнера их ещё нет.*
3. *Этот файл целиком как промпт в Claude Design.*

*Дизайнер отвечает в new conversation thread и работает в течение нескольких сессий пока не сдаст все deliverables из Части 6.*
