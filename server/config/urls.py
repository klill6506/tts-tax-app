import os
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, HttpResponseNotFound
from django.urls import include, path, re_path


def _serve_spa(request):
    """Serve the React SPA index.html for any non-API route (production only).

    Cache-Control: no-cache ensures browsers always check for updated index.html.
    The JS/CSS assets use content-hashed filenames (served by WhiteNoise with
    far-future expires), so only index.html itself needs freshness validation.
    """
    index = Path(getattr(settings, "SPA_DIR", "")) / "index.html"
    if index.exists():
        resp = FileResponse(open(index, "rb"), content_type="text/html")
        resp["Cache-Control"] = "no-cache"
        return resp
    return HttpResponseNotFound("SPA not built. Run: cd client && npm run build")


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

# In production, serve the SPA for any non-API route (HashRouter only needs /)
if os.getenv("DJANGO_SETTINGS_MODULE") == "config.settings.prod":
    urlpatterns.append(re_path(r"^$", _serve_spa))  # root /
    urlpatterns.append(re_path(r"^(?!api/|admin|static).*$", _serve_spa))  # fallback
