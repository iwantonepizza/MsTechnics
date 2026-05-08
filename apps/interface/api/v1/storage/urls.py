from rest_framework.routers import DefaultRouter
from .views import WiresViewSet, HubsViewSet, LamelsViewSet

router = DefaultRouter()
router.register("storage/wires",  WiresViewSet,  basename="wires")
router.register("storage/hubs",   HubsViewSet,   basename="hubs")
router.register("storage/lamels", LamelsViewSet, basename="lamels")
urlpatterns = router.urls
