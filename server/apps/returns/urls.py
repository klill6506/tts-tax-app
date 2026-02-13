from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("form-definitions", views.FormDefinitionViewSet, basename="formdefinition")
router.register("tax-returns", views.TaxReturnViewSet, basename="taxreturn")

urlpatterns = router.urls
