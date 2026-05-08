from rest_framework.routers import DefaultRouter
from .views import DepartureViewSet, ExecutorViewSet

router = DefaultRouter()
router.register("departures", DepartureViewSet, basename="departures")
router.register("executors", ExecutorViewSet, basename="executors")
urlpatterns = router.urls
