"""config/urls.py — корневой URL conf."""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

admin.site.site_header = "Суперсимметрия"
admin.site.site_title = "Суперсимметрия"
admin.site.index_title = "Администрирование"

urlpatterns = [
    path("admin/", admin.site.urls),

    # ── API v1 ────────────────────────────────────────────────────────────
    path("api/v1/", include("apps.interface.api.v1.urls")),

    # ── Legacy (до Фазы 4 не трогать!) ───────────────────────────────────
    path("", include("main_menu.urls")),
    path("user/", include("user.urls")),
    path("monitoring/", include("monitoring.urls")),
    path("control/", include("control.urls")),
    path("service/", include("service.urls")),
    path("zip/", include("zip.urls")),
    path("application/", include("application.urls")),
    path("departure/", include("departure.urls")),
    path("mail/", include("mail.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# OpenAPI (только в dev/staging)
if settings.ENABLE_API_DOCS:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularSwaggerView,
        SpectacularRedocView,
    )
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
