# MsTechnics SPA — Frontend

React 18 + TypeScript + Vite + TanStack Query + Zustand + Tailwind CSS

## Запуск

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173 (проксирует /api на localhost:8000)
```

## Сборка

```bash
npm run build
# → выводит в ../static/spa/
```

## Генерация TypeScript типов из OpenAPI

```bash
# Сначала экспортируй схему с бэка:
cd ..
python manage.py spectacular --file api-schema.yaml

# Затем генерируй типы:
cd frontend
npm run generate:api-types
# → src/shared/api/schema.d.ts
```

## Структура

```
src/
  app/           # Роутинг, providers, theme
  shared/
    api/         # Axios client, TypeScript types
    lib/         # queryClient, SSE, utils
    ui/          # Button, Modal, Tabs, Badge, ...
  entities/      # Одна доменная сущность
    application/ # hooks + ApplicationCard + EventTimeline
    panel/       # hooks + CellSlot
    display/     # hooks
  features/      # Одна функциональность
    auth/        # store (Zustand) + hooks + LoginPage
    applications/ # CreateModal + TransitionModal
  widgets/       # Композиция entities+features
    display-grid/     # DisplayGrid (100+ ячеек)
    applications-panel/ # Вкладки заявок
    navigation/       # AppLayout + Sidebar
  pages/         # Страницы
    login/       # /login
    menu/        # /menu — дашборд
    department/  # /monitoring, /control, /service — список экранов
    display-view/ # /:dept/:city/:display — основной рабочий экран
    zip/         # /zip — склад расходников
    departures/  # /departures — выезды
```

## Ключевые решения

- **JWT в memory** (Zustand persist для access token), **refresh в httpOnly cookie**
- **SSE** через `/api/v1/events/stream?token=<jwt>` (EventSource не поддерживает заголовки)
- **TanStack Query** инвалидирует кэш при SSE-событиях (auto-refresh без polling)
- **CellSlot** — адаптивный размер ячейки, цвет = статус заявки
- **3-панельный layout**: заявки (слева) / сетка (центр) / детали (справа)
