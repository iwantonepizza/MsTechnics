# T-2-010. Переименовать `MsServiceControl/` → `config/`

> **Тип:** refactor
> **Приоритет:** P1
> **Оценка:** 1 час
> **Фаза:** 2
> **Статус:** done

---

## Цель

Имя `MsServiceControl` — реликт, соответствует старому названию проекта. Переименовать в `config/` — стандартное имя для Django settings-пакета (используется в Cookiecutter-Django, djangopackages и т.п.).

Это подготовка к task T-2-011 — вынесению приложений в `apps/`.

---

## Зависимости

- **Блокируется:** T-1-007 (там settings разделён на `dev/prod/test`) — но если T-1-007 ещё не сделан, **сначала эту делать не надо**
- **Блокирует:** T-2-011, T-2-012

---

## Что нужно сделать

1. **Переименовать папку:**
   ```bash
   git mv MsServiceControl config
   ```

2. **Обновить все ссылки** (grep — основной инструмент):
   ```bash
   grep -rln "MsServiceControl" --include="*.py" .
   grep -rln "MsServiceControl" --include="*.cfg" --include="*.toml" --include="*.yml" --include="*.yaml" .
   ```
   Заменить на `config` везде:
   - `manage.py`: `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')`
   - `config/wsgi.py`, `config/asgi.py`: аналогично
   - `Dockerfile`: `CMD ["gunicorn", "config.wsgi:application", ...]`
   - `docker-compose.yml`: `command: gunicorn config.wsgi:application...`
   - `pyproject.toml`: `DJANGO_SETTINGS_MODULE = "config.settings.test"`
   - `.env.example`: `DJANGO_SETTINGS_MODULE=config.settings.dev`
   - Если есть `setup.cfg` или `pytest.ini` — тоже

3. **Проверить:**
   ```bash
   python manage.py check
   python manage.py migrate --dry-run
   pytest
   ```

4. **Прод-деплой:** при переименовании нужно обновить systemd unit / docker compose / gunicorn startup скрипты. Обновить в `infra/` или где они лежат.

5. **Коммит одним атомарным:**
   ```
   refactor(config): rename MsServiceControl → config
   
   Standard Django layout (cookiecutter-django style).
   All import paths updated, prod deploy scripts updated.
   
   Refs: T-2-010
   ```

---

## Критерии приёмки

- [ ] `MsServiceControl/` удалено, `config/` существует
- [ ] `python manage.py check` — чисто
- [ ] `pytest` — проходит
- [ ] `docker compose up` — работает (локально проверить)
- [ ] `grep -rn "MsServiceControl" .` — пусто
- [ ] PR содержит 1 большой коммит, легко откатывается

---

## Что НЕ делать

- **НЕ дели** на два коммита (rename + import updates) — атомарно.
- **НЕ рефактори** settings в этой задаче (она делалась в T-1-007).
- **НЕ трогай** содержимое файлов кроме rename-рефакторинга.

---

## Риски

- **Git history.** После rename может показаться, что все файлы новые. Используй `git log --follow config/settings.py` или `git blame -C` — история сохранится.
- **Прод-кэш.** `.pyc` в проде может ссылаться на `MsServiceControl` — очисть `__pycache__` при деплое.
- **Третьи стороны.** Если есть cron-скрипты или мониторинг, которые импортируют через путь — обновить их.

---

## Проверка после деплоя

На проде:
```bash
curl -I https://mstechnics.ru/admin/
# Ожидание: 302 (redirect на login) или 200
```
Если 500 — откат на предыдущий коммит, смотрим логи, находим непокрытый импорт.
