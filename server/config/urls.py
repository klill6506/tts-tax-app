from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.clients.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.imports.urls")),
    path("api/v1/", include("apps.mappings.urls")),
    path("api/v1/", include("apps.diagnostics.urls")),
    path("api/v1/", include("apps.returns.urls")),
    path("api/v1/", include("apps.firms.urls")),
    path("api/v1/", include("apps.ai_help.urls")),
]
