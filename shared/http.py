"""
T-1-009: safe_redirect — защита от open-redirect уязвимости.

Проблема: redirect(request.META['HTTP_REFERER']) позволяет
злоумышленнику передать произвольный внешний URL в заголовке Referer
и перенаправить пользователя на фишинговый сайт.

Решение: разрешаем редирект только на URL того же хоста.
"""
from urllib.parse import urlparse

import structlog
from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse

logger = structlog.get_logger(__name__)


def safe_redirect(
    request: HttpRequest,
    fallback: str = "main_menu:index",
    *,
    fallback_is_url: bool = False,
) -> HttpResponseRedirect:
    """
    Безопасный редирект на предыдущую страницу.

    Берёт URL из HTTP_REFERER, проверяет что он ведёт на тот же хост.
    Если проверка не прошла — редиректит на fallback.

    Args:
        request: Django HttpRequest
        fallback: имя URL (reverse) или абсолютный URL если fallback_is_url=True
        fallback_is_url: если True — fallback используется как есть, без reverse()
    """
    referer = request.META.get("HTTP_REFERER", "")

    if referer and _is_safe_url(referer, request):
        return HttpResponseRedirect(referer)

    if referer:
        logger.warning(
            "safe_redirect_blocked_external_referer",
            referer=referer,
            path=request.path,
        )

    fallback_url = fallback if fallback_is_url else reverse(fallback)
    return HttpResponseRedirect(fallback_url)


def _is_safe_url(url: str, request: HttpRequest) -> bool:
    """Проверяет что URL ведёт на тот же хост что и текущий сайт."""
    if not url:
        return False

    # Относительные URL всегда безопасны
    parsed = urlparse(url)
    if not parsed.netloc:
        return True

    # Проверяем хост против ALLOWED_HOSTS
    allowed = getattr(settings, "ALLOWED_HOSTS", [])
    request_host = request.get_host().split(":")[0]  # убираем порт

    return parsed.netloc.split(":")[0] in (allowed + [request_host])
