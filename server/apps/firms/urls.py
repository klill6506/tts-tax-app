from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PreparerViewSet, PrintPackageViewSet

router = DefaultRouter()
router.register("preparers", PreparerViewSet, basename="preparer")
router.register("print-packages", PrintPackageViewSet, basename="print-package")

urlpatterns = [
    path("", include(router.urls)),
]
