"""Root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

# T-8-072: русификация заголовков админки.
admin.site.site_header = "Суперсимметрия — администрирование"
admin.site.site_title = "Суперсимметрия"
admin.site.index_title = "Управление данными"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("django_prometheus.urls")),
    path("api/v1/", include("apps.interface.api.v1.urls")),
    path("", include("main_menu.urls")),
    path("", include(("main.urls", "main"), namespace="main")),
    path("user/", include("user.urls")),
    path("monitoring/", include("monitoring.urls")),
    path("control/", include("control.urls")),
    path("service/", include("service.urls")),
    path("zip/", include("zip.urls")),
    path("application/", include("application.urls")),
    path("departure/", include("departure.urls")),
    path("mail/", include("mail.urls")),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

if settings.ENABLE_API_DOCS:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls)), *urlpatterns]
