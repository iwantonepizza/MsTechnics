from rest_framework.routers import DefaultRouter

from .views import ConnectorsViewSet, HubsViewSet, LamelsViewSet, PowerBlocksViewSet, WiresViewSet

router = DefaultRouter()
router.register("storage/wires", WiresViewSet, basename="wires")
router.register("storage/hubs", HubsViewSet, basename="hubs")
router.register("storage/lamels", LamelsViewSet, basename="lamels")
router.register("storage/power-blocks", PowerBlocksViewSet, basename="power-blocks")
router.register("storage/connectors", ConnectorsViewSet, basename="connectors")
urlpatterns = router.urls
