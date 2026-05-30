from rest_framework.routers import DefaultRouter

from .views import DailyTaskViewSet

router = DefaultRouter()
router.register("daily-tasks", DailyTaskViewSet, basename="daily-tasks")
urlpatterns = router.urls
