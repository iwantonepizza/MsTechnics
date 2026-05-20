# ai-docs/ — документация проекта MsTechnics

Оглавление. Если не знаешь, куда смотреть — сюда.

## Структура

```
ai-docs/
├── README.md                          ← ты здесь
│
├── 00-architecture/                   Целевая архитектура
│   ├── target-architecture.md         Как должен выглядеть проект после рефакторинга
│   ├── domain-model.md                Модели домена и их связи
│   ├── layering.md                    Слои приложений (core → directory → workflow → integrations → interface)
│   └── data-flow.md                   Как данные текут между слоями
│
├── 01-current-state/                  Что сейчас не так
│   ├── audit-report.md                Полный список багов и антипаттернов
│   ├── security-issues.md             Критические проблемы безопасности (читать первым!)
│   └── performance-issues.md          Узкие места
│
├── 02-roadmap/                        План работ
│   └── roadmap.md                     6 фаз рефакторинга и production cutover
│
├── 03-tasks/                          Атомарные задачи (1-3 часа каждая)
│   ├── README.md                      Навигация по задачам
│   ├── TEMPLATE.md                    Шаблон задачи
│   ├── phase-1-foundation/            Фаза 1: базис (безопасность, конфиг, типы)
│   ├── phase-2-models/                Фаза 2: нормализация моделей, миграции
│   ├── phase-3-rest-api/              Фаза 3: REST API, сервисы, use-cases
│   ├── phase-4-spa/                   Фаза 4: React SPA
│   └── phase-5-integrations/          Фазы 5-6: integrations, security, production cutover
│
├── 04-conventions/                    Как мы пишем
│   ├── code-style.md                  Python/TS style
│   ├── git-workflow.md                Ветки, коммиты, PR
│   ├── commit-format.md               Формат сообщений коммитов
│   └── api-conventions.md             REST API: URL, статусы, ошибки, пагинация
│
├── 05-review-checklists/              Что проверяет архитектор
│   ├── backend-review.md              Чеклист для Python/Django/DRF
│   ├── frontend-review.md             Чеклист для React
│   ├── migration-review.md            Чеклист для миграций БД (особо опасно!)
│   └── pr-checklist.md                Общий чеклист перед открытием PR
│
├── 06-integrations/                   Внешние интеграции
│   ├── notifications-redesign.md      Редизайн уведомлений (TG сломан в РФ)
│   ├── max-bot.md                     Бот в мессенджере МАХ
│   ├── telegram-russia-workaround.md  Обход блокировки TG в РФ
│   └── gmail-alarms.md                Парсер писем от VNNOX
│
├── 07-frontend/                       Всё для Claude Design
│   ├── design-brief.md                ГЛАВНЫЙ файл — даётся на вход Claude Design
│   ├── screens-map.md                 Карта всех экранов + состояний
│   ├── components.md                  Библиотека компонентов
│   ├── states-and-flows.md            User flows по ролям
│   └── api-contract.md                Контракт SPA ↔ API
│
├── 08-reports/                        Отчёты по выполненным задачам
│   ├── README.md                      Протокол отчётов
│   └── TEMPLATE.md                    Шаблон отчёта
│
├── 09-user-tasks-tracker.md           15 задач от владельца → formal tasks
├── 10-glossary.md                     Глоссарий терминов
└── adr/                               Architecture Decision Records (по мере появления)
    └── ADR-001-frontend-react-spa.md
```

---

## Быстрые ссылки по частым вопросам

| Хочу узнать                              | Файл                                              |
|------------------------------------------|---------------------------------------------------|
| Что такое «панель», «заявка», «слот»?    | `10-glossary.md`                                  |
| Какая целевая архитектура?               | `00-architecture/target-architecture.md`         |
| Что сейчас сломано?                      | `01-current-state/audit-report.md`               |
| С чего начать рефакторинг?               | `02-roadmap/roadmap.md`                          |
| Как писать код?                          | `04-conventions/code-style.md`                   |
| Как назвать коммит?                      | `04-conventions/commit-format.md`                |
| Как устроен REST API?                    | `04-conventions/api-conventions.md`              |
| Как оформить миграцию?                   | `05-review-checklists/migration-review.md`       |
| Какие экраны во фронте?                  | `07-frontend/screens-map.md`                     |
| Как оформить отчёт о выполненной задаче? | `08-reports/TEMPLATE.md`                         |
| Задача от владельца #N — что с ней?      | `09-user-tasks-tracker.md`                       |

---

## Порядок чтения для нового агента

### Backend-кодер (GPT)

1. `AGENTS.md` (корень репо)
2. `ai-docs/README.md` (этот файл)
3. `10-glossary.md` (5 минут)
4. `00-architecture/domain-model.md`
5. `00-architecture/target-architecture.md`
6. `00-architecture/layering.md`
7. `01-current-state/audit-report.md` (только чтобы понять, что избегать)
8. `04-conventions/code-style.md`
9. `04-conventions/git-workflow.md`
10. `05-review-checklists/backend-review.md`
11. `03-tasks/phase-1-foundation/` — первая задача

### Frontend-агент (Claude Design)

1. `AGENTS.md` (корень)
2. `ai-docs/README.md`
3. `10-glossary.md`
4. `07-frontend/design-brief.md` — ГЛАВНЫЙ файл
5. `07-frontend/screens-map.md`
6. `07-frontend/states-and-flows.md`
7. `07-frontend/components.md`
8. `07-frontend/api-contract.md`
9. `04-conventions/code-style.md` (TS секция)

### Ревьюер / Архитектор

1. `02-roadmap/roadmap.md` — смотреть прогресс
2. `03-tasks/` — брать задачу, которую берём в работу
3. `05-review-checklists/` — при ревью PR
4. `08-reports/` — при закрытии задачи
