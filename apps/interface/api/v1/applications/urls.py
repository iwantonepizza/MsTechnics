from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet

router = DefaultRouter(trailing_slash="/?")
router.register("applications", ApplicationViewSet, basename="applications")
urlpatterns = [
    path(
        "applications/<int:pk>/events",
        ApplicationViewSet.as_view({"get": "events"}),
        name="applications-events-noslash",
    ),
    *router.urls,
]
