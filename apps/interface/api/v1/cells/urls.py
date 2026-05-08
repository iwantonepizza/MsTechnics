from rest_framework.routers import DefaultRouter
from .views import CellViewSet

router = DefaultRouter()
router.register("cells", CellViewSet, basename="cells")
urlpatterns = router.urls
