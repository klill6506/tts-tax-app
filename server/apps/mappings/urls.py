from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("mapping-templates", views.MappingTemplateViewSet, basename="mappingtemplate")
router.register("mapping-rules", views.MappingRuleViewSet, basename="mappingrule")

urlpatterns = router.urls
