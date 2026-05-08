from rest_framework.routers import DefaultRouter
from .views import DisplayViewSet

router = DefaultRouter()
router.register("displays", DisplayViewSet, basename="displays")
urlpatterns = router.urls
