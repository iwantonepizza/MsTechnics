from rest_framework.routers import DefaultRouter
from .views import (
    CityViewSet, ColorViewSet, ConditionViewSet, SmileViewSet,
    DepartmentViewSet, ApplicationStatusViewSet, DepartureStatusViewSet,
)

router = DefaultRouter()
router.register("cities",               CityViewSet,              basename="cities")
router.register("colors",               ColorViewSet,             basename="colors")
router.register("conditions",           ConditionViewSet,         basename="conditions")
router.register("smiles",               SmileViewSet,             basename="smiles")
router.register("departments",          DepartmentViewSet,        basename="departments")
router.register("application-statuses", ApplicationStatusViewSet, basename="application-statuses")
router.register("departure-statuses",   DepartureStatusViewSet,   basename="departure-statuses")

urlpatterns = router.urls
