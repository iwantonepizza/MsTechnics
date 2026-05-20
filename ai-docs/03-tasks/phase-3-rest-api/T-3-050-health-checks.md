# T-3-050. Health-check endpoints

> **Тип:** infra
> **Приоритет:** P2
> **Оценка:** 0.5 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Endpoint'ы для мониторинга / load balancer'а / Kubernetes probes. Простые, без аутентификации.

---

## Эндпоинты

```
GET /api/v1/health/live      # liveness — проц жив (всегда 200 если процесс работает)
GET /api/v1/health/ready     # readiness — готов принимать трафик (проверяет БД + Redis)
```

---

## Что нужно сделать

`apps/interface/api/v1/health/views.py`:

```python
from django.db import connection
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
import redis


class LivenessView(APIView):
    """Liveness probe. Всегда 200 если процесс работает."""
    permission_classes = [AllowAny]
    authentication_classes = []
    
    @extend_schema(tags=['health'], summary='Liveness probe')
    def get(self, request):
        return Response({'status': 'alive'})


class ReadinessView(APIView):
    """Readiness probe. Проверяет зависимости (DB, Redis)."""
    permission_classes = [AllowAny]
    authentication_classes = []
    
    @extend_schema(tags=['health'], summary='Readiness probe')
    def get(self, request):
        checks = {
            'database': self._check_db(),
            'redis': self._check_redis(),
        }
        all_ok = all(c['ok'] for c in checks.values())
        return Response(
            {'status': 'ready' if all_ok else 'unready', 'checks': checks},
            status=200 if all_ok else 503,
        )
    
    def _check_db(self):
        try:
            with connection.cursor() as cur:
                cur.execute('SELECT 1')
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}
    
    def _check_redis(self):
        try:
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'error': str(e)}
```

URLs:

```python
from django.urls import path
from .views import LivenessView, ReadinessView

urlpatterns = [
    path('health/live',  LivenessView.as_view(),  name='health-live'),
    path('health/ready', ReadinessView.as_view(), name='health-ready'),
]
```

---

## Критерии приёмки

- [ ] `GET /api/v1/health/live` → 200 без аутентификации
- [ ] `GET /api/v1/health/ready` → 200 если все зависимости работают, 503 иначе
- [ ] Не требуется аутентификация
- [ ] Нет throttling
- [ ] Тесты: live always 200, ready проверяет ответ ok/error

---

## Что НЕ делать

- **НЕ открывай** этот endpoint наружу публично, если он содержит подробные ошибки — `error: str(e)` может протечь stack trace или connection string
- **НЕ кешируй** ответ — readiness должен быть «здесь и сейчас»
