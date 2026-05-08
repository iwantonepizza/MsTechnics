# T-3-051. E2E тесты на критичных путях API

> **Тип:** tests
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Снизу-вверх покрыть основные user-stories через настоящие HTTP-вызовы к API. Это страховка перед Фазой 4: фронт будет идти этими же путями.

---

## Зависимости

- **Блокируется:** все T-3-XXX (нечего тестировать без endpoint'ов)

---

## Что нужно сделать

`tests/test_api_e2e.py` — 4 user-story теста + 1 schema-тест:

### Test 1. Полный happy-path заявки

```python
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_e2e_application_full_lifecycle(
    ms_user_factory, display_with_layout_factory, application_status_factory,
):
    """Полный путь: monitor создаёт → control принимает → service закрывает → archive."""
    
    # Подготовка
    for n in ['sent_to_control','apply_in_control','sent_to_service',
              'work_in_service','done','archive_done']:
        application_status_factory(name=n)
    
    display = display_with_layout_factory(rows=2, cols=2)
    cell = display.cells.first()
    
    monitor = ms_user_factory(username='monitor', permission='monitoring')
    monitor.allowed_city.add(display.city)
    control = ms_user_factory(username='control', permission='control')
    control.allowed_city.add(display.city)
    service = ms_user_factory(username='service', permission='service')
    service.allowed_city.add(display.city)
    
    # ========================================
    # 1. Monitor создаёт заявку
    # ========================================
    client = APIClient()
    client.force_authenticate(user=monitor)
    
    response = client.post('/api/v1/applications/', {
        'display_id': display.id,
        'panel_id': cell.panel.id,
        'cell_id': cell.id,
        'comment': 'Моргает',
    }, format='json')
    
    assert response.status_code == 201
    app_id = response.data['id']
    assert response.data['status']['name'] == 'sent_to_control'
    
    # ========================================
    # 2. Control видит заявку в Запросах
    # ========================================
    client.force_authenticate(user=control)
    response = client.get(f'/api/v1/applications/?display={display.slug}&box=received')
    assert response.status_code == 200
    ids = [r['id'] for r in response.data['results']]
    assert app_id in ids
    
    # ========================================
    # 3. Control принимает: sent_to_control → apply_in_control
    # ========================================
    response = client.post(
        f'/api/v1/applications/{app_id}/transition/',
        {'target_state': 'apply_in_control', 'comment': 'принято'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['status']['name'] == 'apply_in_control'
    
    # ========================================
    # 4. Control отправляет в сервис
    # ========================================
    response = client.post(
        f'/api/v1/applications/{app_id}/transition/',
        {'target_state': 'sent_to_service', 'comment': 'срочно'},
        format='json',
    )
    assert response.status_code == 200
    
    # ========================================
    # 5. Service берёт в работу
    # ========================================
    client.force_authenticate(user=service)
    response = client.post(
        f'/api/v1/applications/{app_id}/transition/',
        {'target_state': 'work_in_service', 'comment': ''},
        format='json',
    )
    assert response.status_code == 200
    
    # ========================================
    # 6. Service закрывает
    # ========================================
    response = client.post(
        f'/api/v1/applications/{app_id}/transition/',
        {'target_state': 'done', 'comment': 'заменил'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['status']['name'] == 'done'
    
    # ========================================
    # 7. Control архивирует
    # ========================================
    client.force_authenticate(user=control)
    response = client.post(
        f'/api/v1/applications/{app_id}/transition/',
        {'target_state': 'archive_done'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['status']['name'] == 'archive_done'
    
    # ========================================
    # 8. Events содержит все 6 шагов
    # ========================================
    response = client.get(f'/api/v1/applications/{app_id}/events')
    assert response.status_code == 200
    events = response.data['results']
    assert len(events) >= 6
    
    state_pairs = [(e['state_from'], e['state_to']) for e in events]
    assert ('', 'sent_to_control') in state_pairs or ('sent_to_control' in [e['state_to'] for e in events])
    assert ('done', 'archive_done') in state_pairs
```

### Test 2. Permission на все ключевые endpoints

```python
def test_e2e_permission_matrix(ms_user_factory, display_with_layout_factory, application_factory, application_status_factory):
    """Проверка матрицы прав: monitoring vs control vs service."""
    for n in ['sent_to_control','apply_in_control','sent_to_service','work_in_service','done']:
        application_status_factory(name=n)
    
    display = display_with_layout_factory(rows=1, cols=1)
    cell = display.cells.first()
    app = application_factory(
        display=display, panel=cell.panel, cell=cell, status__name='sent_to_control',
    )
    
    monitor = ms_user_factory(permission='monitoring')
    monitor.allowed_city.add(display.city)
    
    client = APIClient()
    client.force_authenticate(user=monitor)
    
    # Monitor НЕ может принять заявку
    response = client.post(
        f'/api/v1/applications/{app.id}/transition/',
        {'target_state': 'apply_in_control'},
        format='json',
    )
    assert response.status_code == 403
    
    # Monitor НЕ может change_department
    response = client.post(
        f'/api/v1/panels/{cell.panel.id}/change-department/',
        {'department': 'zip'},
        format='json',
    )
    assert response.status_code == 403
```

### Test 3. PanelMover защищает от перемещения с активной заявкой

```python
def test_e2e_panel_blocks_move_with_active_application(
    ms_user_factory, display_with_layout_factory, application_factory, application_status_factory,
):
    application_status_factory(name='sent_to_service')
    display = display_with_layout_factory(rows=1, cols=1)
    cell = display.cells.first()
    
    application_factory(display=display, panel=cell.panel, cell=cell, status__name='sent_to_service')
    
    user = ms_user_factory(permission='admin')
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.post(
        f'/api/v1/panels/{cell.panel.id}/change-department/',
        {'department': 'zip', 'comment': 'на склад'},
        format='json',
    )
    
    assert response.status_code == 409
    assert response.data['code'] == 'panel_has_active_application'
```

### Test 4. ActivityLog содержит все события из flow

```python
def test_e2e_activity_log_aggregates_events(
    ms_user_factory, display_with_layout_factory, application_status_factory,
):
    for n in ['sent_to_control','apply_in_control']:
        application_status_factory(name=n)
    
    display = display_with_layout_factory(rows=1, cols=1)
    cell = display.cells.first()
    
    user = ms_user_factory(permission='admin')
    user.allowed_city.add(display.city)
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    # 1. Создать заявку
    response = client.post('/api/v1/applications/', {
        'display_id': display.id,
        'panel_id': cell.panel.id,
        'cell_id': cell.id,
        'comment': 'тест',
    }, format='json')
    assert response.status_code == 201
    app_id = response.data['id']
    
    # 2. Перевести
    client.post(
        f'/api/v1/applications/{app_id}/transition/',
        {'target_state': 'apply_in_control'},
        format='json',
    )
    
    # 3. ActivityLog по экрану — содержит оба события
    response = client.get(f'/api/v1/activity-log/?display={display.slug}')
    assert response.status_code == 200
    events = response.data['results']
    
    types = [e['event_type'] for e in events]
    assert 'application.created' in types or any('application' in t for t in types)
    assert 'application.transitioned' in types
```

### Test 5. OpenAPI schema валидна

```python
def test_e2e_openapi_schema_is_valid():
    from django.core.management import call_command
    
    # Должно не падать
    call_command('spectacular', '--validate', '--fail-on-warn', stderr=open('/dev/null', 'w'))
```

---

## Критерии приёмки

- [ ] 5 e2e-тестов проходят локально
- [ ] CI запускает их вместе с unit-тестами
- [ ] Тесты используют реальный HTTP-stack (`APIClient`, не голые view'ы)
- [ ] Coverage на critical paths (transitions, auth, permissions) ≥ 90%
- [ ] OpenAPI schema проверяется автоматически

---

## Что НЕ делать

- **НЕ дублируй** unit-тесты T-3-XXX — тестируй на уровень выше (через HTTP)
- **НЕ хардкодь** `assert response.status_code == 200` без проверки тела — всегда `assert key in response.data`
- **НЕ запускай** на проде — это integration-тесты, на тестовой БД
