"""
Base Django settings for TTS Tax App.
Shared across all environments. Do NOT put secrets here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# D:\dev\tts-tax-app\server
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["SECRET_KEY"]

# ---------------------------------------------------------------------------
# App version — single source of truth is the root VERSION file
# ---------------------------------------------------------------------------
_version_file = BASE_DIR.parent / "VERSION"
APP_VERSION = _version_file.read_text().strip() if _version_file.exists() else "0.0.0"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.core",
    "apps.firms",
    "apps.accounts",
    "apps.clients",
    "apps.audit",
    "apps.imports",
    "apps.mappings",
    "apps.diagnostics",
    "apps.returns",
    "apps.tts_forms",
    "apps.ai_help",
    "storages",
    "apps.documents",
]

# ---------------------------------------------------------------------------
# AI Help (Google Gemini)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.firms.middleware.FirmMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database — always Postgres
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "tts_tax"),
        "USER": os.getenv("DB_USER", "tts"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "TEST": {
            "NAME": "test_postgres",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# IRS PDF templates directory (repo root / resources / irs_forms)
IRS_FORMS_DIR = BASE_DIR.parent / "resources" / "irs_forms"

# ---------------------------------------------------------------------------
# Supabase Storage (S3-compatible) for document management
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "tax-documents")

_PROJECT_REF = SUPABASE_URL.replace("https://", "").split(".")[0] if SUPABASE_URL else ""

# Only configure S3 backend if credentials exist; otherwise use local filesystem
if os.getenv("SUPABASE_S3_ACCESS_KEY"):
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": SUPABASE_STORAGE_BUCKET,
                "endpoint_url": f"https://{_PROJECT_REF}.supabase.co/storage/v1/s3" if _PROJECT_REF else "",
                "access_key": os.getenv("SUPABASE_S3_ACCESS_KEY", ""),
                "secret_key": os.getenv("SUPABASE_S3_SECRET_KEY", ""),
                "region_name": "us-east-1",
                "default_acl": "private",
                "addressing_style": "path",
                "signature_version": "s3v4",
                "querystring_auth": True,
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# Max upload size: 25 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF defaults
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}
