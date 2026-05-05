from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("documents", views.ClientDocumentViewSet, basename="document")

urlpatterns = router.urls
