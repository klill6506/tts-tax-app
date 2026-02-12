from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("tb-uploads", views.TrialBalanceUploadViewSet, basename="tbupload")
router.register("tb-rows", views.TrialBalanceRowViewSet, basename="tbrow")

urlpatterns = router.urls
