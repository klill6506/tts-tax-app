"""
Development-only settings. Loaded by default via manage.py / .env.
"""

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# In dev, also render browsable API for convenience
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += [  # noqa: F405
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# CORS — allow Electron dev app to reach the Django API
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
]
CORS_ALLOW_CREDENTIALS = True

# Let session cookies travel in cross-origin requests from Electron
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
]
