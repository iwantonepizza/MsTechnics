"""apps/interface/api/v1/urls.py — корневой URL conf API v1."""
from django.urls import include, path

urlpatterns = [
    # 3.0 Auth
    path("auth/",  include("apps.interface.api.v1.auth.urls")),
    path("me",     include("apps.interface.api.v1.me.urls")),

    # 3.1 Справочники
    path("", include("apps.interface.api.v1.refs.urls")),

    # 3.2 Основные ресурсы
    path("", include("apps.interface.api.v1.displays.urls")),
    path("", include("apps.interface.api.v1.panels.urls")),
    path("", include("apps.interface.api.v1.cells.urls")),
    path("", include("apps.interface.api.v1.storage.urls")),

    # 3.3 Workflow
    path("", include("apps.interface.api.v1.applications.urls")),
    path("", include("apps.interface.api.v1.departures.urls")),

    # 3.4 Лог и реалтайм
    path("", include("apps.interface.api.v1.activity.urls")),
    path("", include("apps.interface.api.v1.events.urls")),

    # 3.5 Health
    path("", include("apps.interface.api.v1.health.urls")),
    path("", include("apps.interface.api.v1.dashboard.urls")),

    # 3.6 Integrations
    path("integrations/max/", include("apps.integrations.max.urls")),
]
