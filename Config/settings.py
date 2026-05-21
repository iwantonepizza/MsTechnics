"""
Django settings for MsTechnics project.

T-1-007: секреты вынесены в .env через django-environ
T-1-004: structlog настроен
T-3-001: DRF + JWT + CORS
T-3-002: drf-spectacular (OpenAPI)
"""
import os
import logging
from pathlib import Path
from datetime import timedelta

import environ
import structlog

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, None),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    REDIS_HOST=(str, "redis"),
    REDIS_PORT=(int, 6379),
    CORS_ALLOWED_ORIGINS=(
        list,
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
    ),
    CSRF_TRUSTED_ORIGINS=(
        list,
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
    ),
    ENABLE_API_DOCS=(bool, True),
    SENTRY_DSN=(str, ""),
    SENTRY_ENV=(str, "production"),
    SENTRY_TRACES_SAMPLE_RATE=(float, 0.1),
)

_dotenv_path = BASE_DIR / ".env"
if not _dotenv_path.exists():
    _dotenv_path = BASE_DIR / "Config" / ".env"
if _dotenv_path.exists():
    environ.Env.read_env(_dotenv_path)

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", default="dev-insecure-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

GOOGLE_CREDENTIALS_FILE = env(
    "GOOGLE_CLIENT_SECRET_PATH",
    default=str(BASE_DIR / "Config" / "client_secret.json"),
)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
    except ImportError as exc:
        raise RuntimeError("SENTRY_DSN is set, but sentry-sdk is not installed") from exc

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            RedisIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE"),
        send_default_pii=False,
        environment=env("SENTRY_ENV"),
        release=env("RELEASE_VERSION", default=None),
    )

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # DRF & API
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",

    # ── New apps (Фаза 2) ─────────────────────────────────────────────────
    "apps.core.references",
    "apps.core.users",
    "apps.directory.displays",
    "apps.directory.panels",
    "apps.directory.storage",
    "apps.workflow.applications",
    "apps.workflow.departures",
    "apps.workflow.daily_tasks",
    "apps.activity",
    "apps.notifications",
    "apps.interface",
    "apps.integrations.gmail_alarms",

    # ── Legacy (compat shims) ─────────────────────────────────────────────
    "main",
    "main_menu",
    "zip",
    "departure",
    "application",
    "mail",
]

if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",          # CORS первым!
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "shared.middleware.RequestContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = "Config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME", default="mstechnics"),
        "USER": env("DATABASE_USER", default="mstechnics"),
        "PASSWORD": env("DATABASE_PASSWORD", default=""),
        "HOST": env("DATABASE_HOST", default="db"),
        "PORT": env("DATABASE_PORT", default="5432"),
    }
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "user.MsUser"
LOGIN_URL = "/user/login/"
LOGIN_REDIRECT_URL = "/"

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_HOST = env("REDIS_HOST")
REDIS_PORT = env.int("REDIS_PORT")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_PROXY_URL = env("TELEGRAM_PROXY_URL", default=None)
TELEGRAM_TIMEOUT_SEC = env.int("TELEGRAM_TIMEOUT_SEC", default=30)

MAX_BOT_TOKEN = env("MAX_BOT_TOKEN", default="")
MAX_API_BASE = env("MAX_API_BASE", default="https://platform-api.max.ru")
MAX_WEBHOOK_SECRET = env("MAX_WEBHOOK_SECRET", default="")
MAX_TIMEOUT_SEC = env.int("MAX_TIMEOUT_SEC", default=30)
VNNOX_ALARM_NOTIFY_THRESHOLD_MINUTES = env.int("VNNOX_ALARM_NOTIFY_THRESHOLD_MINUTES", default=15)

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@mstechnics.local")

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Yekaterinburg"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = (BASE_DIR / "static",)
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)

# ---------------------------------------------------------------------------
# T-3-001: Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",  # для Django admin
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "shared.pagination.CursorPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "shared.throttling.BurstRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon":       "100/hour",
        "user":       "2000/hour",
        "burst":      "60/min",
        "sustained":  "5000/day",
        "login":      "10/min",
        "transition": "120/min",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "shared.exceptions.custom_exception_handler",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
}

# ---------------------------------------------------------------------------
# T-3-001: SimpleJWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_OBTAIN_SERIALIZER": "apps.interface.api.v1.auth.serializers.TokenObtainPairSerializer",
}

# ---------------------------------------------------------------------------
# T-3-002: drf-spectacular (OpenAPI)
# ---------------------------------------------------------------------------
ENABLE_API_DOCS = env.bool("ENABLE_API_DOCS", default=DEBUG)

SPECTACULAR_SETTINGS = {
    "TITLE": "Суперсимметрия API",
    "DESCRIPTION": "REST API для системы управления LED-экранами Суперсимметрия.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    "SORT_OPERATIONS": False,
    "AUTHENTICATION_WHITELIST": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "TAGS": [
        {"name": "auth",         "description": "Аутентификация"},
        {"name": "me",           "description": "Текущий пользователь"},
        {"name": "refs",         "description": "Справочники"},
        {"name": "displays",     "description": "Экраны"},
        {"name": "panels",       "description": "Панели"},
        {"name": "cells",        "description": "Ячейки"},
        {"name": "storage",      "description": "ЗИП-расходники"},
        {"name": "applications", "description": "Заявки"},
        {"name": "departures",   "description": "Выезды"},
        {"name": "activity",     "description": "Журнал активности"},
        {"name": "events",       "description": "Real-time события (SSE)"},
        {"name": "health",       "description": "Health checks"},
    ],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "displayOperationId": False,
        "docExpansion": "none",
        "persistAuthorization": True,
    },
}

# ---------------------------------------------------------------------------
# Debug Toolbar
# ---------------------------------------------------------------------------
if DEBUG:
    INTERNAL_IPS = ["127.0.0.1"]

# ---------------------------------------------------------------------------
# Legacy domain permissions (пока не переехали в DB)
# ---------------------------------------------------------------------------
ALLOWED_DEPARTMENT = {
    "to_monitoring": ["monitoring", "all", "admin"],
    "to_control": ["control", "all", "admin"],
    "to_service": ["service", "all", "admin"],
    "to_zip": ["service", "all", "admin"],
}

# ---------------------------------------------------------------------------
# T-1-004: Structlog
# ---------------------------------------------------------------------------
_log_renderer = (
    structlog.dev.ConsoleRenderer(colors=True)
    if DEBUG
    else structlog.processors.JSONRenderer()
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structlog": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": _log_renderer,
            "foreign_pre_chain": [
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
            ],
        },
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "structlog",
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "django": {"handlers": ["default"], "level": "WARNING", "propagate": False},
        "django.request": {"handlers": ["default"], "level": "ERROR", "propagate": False},
    },
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
