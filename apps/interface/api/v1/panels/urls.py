from rest_framework.routers import DefaultRouter
from .views import PanelViewSet

router = DefaultRouter()
router.register("panels", PanelViewSet, basename="panels")
urlpatterns = router.urls
