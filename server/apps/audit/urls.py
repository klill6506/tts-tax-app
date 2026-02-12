from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("audit-log", views.AuditEntryViewSet, basename="auditentry")

urlpatterns = router.urls
