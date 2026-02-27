from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("clients", views.ClientViewSet, basename="client")
router.register("entities", views.EntityViewSet, basename="entity")
router.register("entity-links", views.ClientEntityLinkViewSet, basename="entitylink")
router.register("tax-years", views.TaxYearViewSet, basename="taxyear")

urlpatterns = router.urls
