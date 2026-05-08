from django.db import connection
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class LivenessView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=["health"], summary="Liveness probe")
    def get(self, request):
        return Response({"status": "alive"})


class ReadinessView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=["health"], summary="Readiness probe")
    def get(self, request):
        checks = {"database": _check_db(), "redis": _check_redis()}
        ok = all(c["ok"] for c in checks.values())
        return Response({"status": "ready" if ok else "unready", "checks": checks},
                        status=200 if ok else 503)


def _check_db():
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _check_redis():
    try:
        import redis
        redis.from_url(settings.REDIS_URL).ping()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
