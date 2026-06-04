"""Tracked Django settings package for Linux-safe deployments."""

import logging
from datetime import timedelta
from pathlib import Path

import environ
import structlog

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, None),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    AUTH_COOKIE_SECURE=(bool, True),
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

for dotenv_path in (BASE_DIR / ".env", BASE_DIR / "Config" / ".env"):
    if dotenv_path.exists():
        environ.Env.read_env(dotenv_path)
        break

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_SECURE = AUTH_COOKIE_SECURE
CSRF_COOKIE_SECURE = AUTH_COOKIE_SECURE

GOOGLE_CREDENTIALS_FILE = env(
    "GOOGLE_CLIENT_SECRET_PATH",
    default=str(BASE_DIR / "Config" / "client_secret.json"),
)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

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

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_prometheus",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
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
    "main",
    "main_menu",
    "zip",
    "departure",
    "application",
    "mail",
]

if DEBUG:
    INSTALLED_APPS.append("debug_toolbar")

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "shared.middleware.RequestContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

if DEBUG:
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = "project_config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "user" / "templates",
            BASE_DIR / "monitoring" / "templates",
            BASE_DIR / "control" / "templates",
            BASE_DIR / "service" / "templates",
        ],
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

WSGI_APPLICATION = "project_config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DATABASE_NAME", default=env("POSTGRES_DB", default="mstechnics")),
        "USER": env("DATABASE_USER", default=env("POSTGRES_USER", default="mstechnics")),
        "PASSWORD": env("DATABASE_PASSWORD", default=env("POSTGRES_PASSWORD", default="")),
        "HOST": env("DATABASE_HOST", default=env("POSTGRES_HOST", default="db")),
        "PORT": env("DATABASE_PORT", default=env("POSTGRES_PORT", default="5432")),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "user.MsUser"
LOGIN_URL = "/user/login/"
LOGIN_REDIRECT_URL = "/"

REDIS_HOST = env("REDIS_HOST")
REDIS_PORT = env.int("REDIS_PORT")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_PROXY_URL = env("TELEGRAM_PROXY_URL", default=None)
TELEGRAM_TIMEOUT_SEC = env.int("TELEGRAM_TIMEOUT_SEC", default=30)

MAX_BOT_TOKEN = env("MAX_BOT_TOKEN", default="")
MAX_API_BASE = env("MAX_API_BASE", default="https://platform-api.max.ru")
MAX_WEBHOOK_SECRET = env("MAX_WEBHOOK_SECRET", default="")
MAX_TIMEOUT_SEC = env.int("MAX_TIMEOUT_SEC", default=30)
VNNOX_ALARM_NOTIFY_THRESHOLD_MINUTES = env.int("VNNOX_ALARM_NOTIFY_THRESHOLD_MINUTES", default=15)

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@mstechnics.local")

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Yekaterinburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = (BASE_DIR / "static",)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
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
        "anon": "100/hour",
        "user": "2000/hour",
        "burst": "60/min",
        "sustained": "5000/day",
        "login": "10/min",
        "transition": "120/min",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "shared.exceptions.custom_exception_handler",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
}

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

ENABLE_API_DOCS = env.bool("ENABLE_API_DOCS", default=DEBUG)

SPECTACULAR_SETTINGS = {
    "TITLE": "MsTechnics API",
    "DESCRIPTION": "REST API for MS Technics.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    "SORT_OPERATIONS": False,
    "AUTHENTICATION_WHITELIST": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "TAGS": [
        {"name": "auth", "description": "Authentication"},
        {"name": "me", "description": "Current user"},
        {"name": "refs", "description": "Reference data"},
        {"name": "displays", "description": "Displays"},
        {"name": "panels", "description": "Panels"},
        {"name": "cells", "description": "Cells"},
        {"name": "storage", "description": "Storage"},
        {"name": "search", "description": "Global search"},
        {"name": "applications", "description": "Applications"},
        {"name": "departures", "description": "Departures"},
        {"name": "activity", "description": "Activity log"},
        {"name": "events", "description": "Server-sent events"},
        {"name": "health", "description": "Health checks"},
    ],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "displayOperationId": False,
        "docExpansion": "none",
        "persistAuthorization": True,
    },
}

if DEBUG:
    INTERNAL_IPS = ["127.0.0.1"]

ALLOWED_DEPARTMENT = {
    "to_monitoring": ["monitoring", "all", "admin"],
    "to_control": ["control", "all", "admin"],
    "to_service": ["service", "all", "admin"],
    "to_zip": ["service", "all", "admin"],
}

_log_renderer = (
    structlog.dev.ConsoleRenderer(colors=True) if DEBUG else structlog.processors.JSONRenderer()
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
