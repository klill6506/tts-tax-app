"""
Production settings for Render deployment.
Django serves the React SPA via WhiteNoise — single deployment, same origin.
"""

import os
from pathlib import Path

from .base import *  # noqa: F401, F403

DEBUG = False

# Render sets RENDER_EXTERNAL_HOSTNAME automatically
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
ALLOWED_HOSTS = []
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
CUSTOM_DOMAIN = os.getenv("CUSTOM_DOMAIN")
if CUSTOM_DOMAIN:
    ALLOWED_HOSTS.append(CUSTOM_DOMAIN)

# ---------------------------------------------------------------------------
# WhiteNoise — serves static files + the SPA build
# ---------------------------------------------------------------------------
MIDDLEWARE.insert(  # noqa: F405
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,  # noqa: F405
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

# Ensure the CSRF cookie is set on every response (SPA needs it before first POST)
MIDDLEWARE.append("apps.core.middleware.EnsureCsrfCookieMiddleware")  # noqa: F405

STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STATICFILES_DIRS = []

# The SPA build output — WhiteNoise serves static assets (JS/CSS), Django
# catch-all view serves index.html for the root and any non-API routes.
SPA_DIR = Path(BASE_DIR).parent / "client" / "dist-web"  # noqa: F405
if SPA_DIR.exists():
    WHITENOISE_ROOT = str(SPA_DIR)

# Override staticfiles for WhiteNoise; keep Supabase default backend from base.py
if "STORAGES" not in dir():
    STORAGES = {}  # noqa: F841
STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}

# ---------------------------------------------------------------------------
# Security — Render handles SSL termination
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_AGE = 28800  # 8 hours — re-login once per workday
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = False  # Render's load balancer handles this
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Same-origin deployment — no CORS needed
CORS_ALLOWED_ORIGINS = []
