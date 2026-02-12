from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("diagnostic-rules", views.DiagnosticRuleViewSet, basename="diagnosticrule")
router.register("diagnostic-runs", views.DiagnosticRunViewSet, basename="diagnosticrun")

urlpatterns = router.urls
