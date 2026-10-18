from datetime import timedelta
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

from celery.schedules import crontab
from corsheaders.defaults import default_headers
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")
BACKEND_URL = config("BACKEND_URL", default="http://localhost:8000")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
RUNTIME_REDIS_URL = config("RUNTIME_REDIS_URL", default=REDIS_URL)
EXECUTION_WORKERS = config("EXECUTION_WORKERS", default=1, cast=int)
CALCULATION_WORKERS = config("CALCULATION_WORKERS", default=1, cast=int)
EXECUTION_SHARDS = config("EXECUTION_SHARDS", default=64, cast=int)
EXECUTION_NODE_INDEX = config("EXECUTION_NODE_INDEX", default=0, cast=int)
EXECUTION_NODE_COUNT = config("EXECUTION_NODE_COUNT", default=1, cast=int)
EXECUTION_MAX_ACTORS = config("EXECUTION_MAX_ACTORS", default=8, cast=int)
EXECUTION_MAX_USER_ACTORS = config("EXECUTION_MAX_USER_ACTORS", default=4, cast=int)
EXECUTION_ENABLED_SCOPES = set(config("EXECUTION_ENABLED_SCOPES", default="paper", cast=Csv()))
if not EXECUTION_ENABLED_SCOPES or not EXECUTION_ENABLED_SCOPES <= {"paper", "live"}:
    raise ValueError("EXECUTION_ENABLED_SCOPES must contain paper, live or both")
EXECUTION_TASK_TIMEOUT = config("EXECUTION_TASK_TIMEOUT", default=10.0, cast=float)
EXECUTION_STARTUP_TASK_TIMEOUT = config("EXECUTION_STARTUP_TASK_TIMEOUT", default=60.0, cast=float)
EXECUTION_TICK_BATCH = config("EXECUTION_TICK_BATCH", default=128, cast=int)
TERMINAL_MATCH_BATCH = config("TERMINAL_MATCH_BATCH", default=64, cast=int)
CALCULATION_CACHE_MB = config("CALCULATION_CACHE_MB", default=32, cast=int)
EXECUTION_NOTIFY_PORT = config("EXECUTION_NOTIFY_PORT", default=19600, cast=int)
ORDER_PARTITIONS = config("ORDER_PARTITIONS", default=16, cast=int)
ORDER_WORKERS = config("ORDER_WORKERS", default=1, cast=int)
ORDER_CONCURRENCY = config("ORDER_CONCURRENCY", default=2, cast=int)
ORDER_TASK_TIMEOUT = config("ORDER_TASK_TIMEOUT", default=30.0, cast=float)
MARKET_DATA_PROVIDER = config("MARKET_DATA_PROVIDER", default="fyers")
RESEARCH_INPUT_TOKEN_BUDGET = config("RESEARCH_INPUT_TOKEN_BUDGET", default=40000, cast=int)
RESEARCH_OUTPUT_TOKEN_BUDGET = config("RESEARCH_OUTPUT_TOKEN_BUDGET", default=6000, cast=int)
RESEARCH_CACHE_URL = config("RESEARCH_CACHE_URL", default="redis://localhost:6379/3")
MARKET_CACHE_URL = config("MARKET_CACHE_URL", default="redis://localhost:6379/2")
EXECUTION_SCAN_INTERVAL = config("EXECUTION_SCAN_INTERVAL", default=0.005, cast=float)
EXECUTION_NOTIFY_BIND = config("EXECUTION_NOTIFY_BIND", default="127.0.0.1")
EXECUTION_NOTIFY_TARGETS = config("EXECUTION_NOTIFY_TARGETS", default="127.0.0.1", cast=Csv())
from ipaddress import IPv4Address
for notify_host in [EXECUTION_NOTIFY_BIND, *EXECUTION_NOTIFY_TARGETS]:
    IPv4Address(notify_host)  # Resolve configured literal addresses once, without tick-path DNS.

RESEARCH_SERVICE_URL = config("RESEARCH_SERVICE_URL", default="http://127.0.0.1:8001")
RESEARCH_SERVICE_TOKEN = config("RESEARCH_SERVICE_TOKEN", default="")


INSTALLED_APPS = [
    "backend.admin_config.QuantNestAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework.authtoken",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "channels",
    # Apps
    "trading",
    "marketdata",
    "common",
    "strategies",
    "instruments",
    "rules_engine",
    "risk_management",
    "backtesting",
    "paper_trading",
    "brokers",
    "live_trading",
    "analytics",
    "trade_journal",
    "notifications",
    "research",
    "audit",
    "strategy_engine",
    "commercial",
    "customer_support",
    "installations",
]

QUANTNEST_DEPLOYMENT_MODE = config("QUANTNEST_DEPLOYMENT_MODE", default="public")
if QUANTNEST_DEPLOYMENT_MODE not in {"development", "public", "private"}:
    raise ValueError("QUANTNEST_DEPLOYMENT_MODE must be development, public or private")
if QUANTNEST_DEPLOYMENT_MODE == "public" and "live" in EXECUTION_ENABLED_SCOPES:
    raise ValueError("Public deployment requires EXECUTION_ENABLED_SCOPES=paper")
QUANTNEST_LEGAL_NAME = config("QUANTNEST_LEGAL_NAME", default="QuantNest")
QUANTNEST_SUPPORT_EMAIL = config("QUANTNEST_SUPPORT_EMAIL", default="ayushkaneriya05@gmail.com")
QUANTNEST_SUPPORT_HOURS = config("QUANTNEST_SUPPORT_HOURS", default="Monday–Friday, 10:00–18:00 Asia/Kolkata; no response-time SLA")
PRIVACY_POLICY_REVISION = "2026-10-17"
BILLING_ENABLED = config("BILLING_ENABLED", default=False, cast=bool)
BILLING_TAX_BPS = config("BILLING_TAX_BPS", default=0, cast=int)
BILLING_TAX_ID = config("BILLING_TAX_ID", default="")
RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = config("RAZORPAY_WEBHOOK_SECRET", default="")
RAZORPAY_PREVIOUS_WEBHOOK_SECRET = config("RAZORPAY_PREVIOUS_WEBHOOK_SECRET", default="")
TURNSTILE_SECRET_KEY = config("TURNSTILE_SECRET_KEY", default="")
TURNSTILE_HOSTNAMES = config("TURNSTILE_HOSTNAMES", default=urlparse(FRONTEND_URL).hostname or "localhost", cast=Csv())
BREVO_API_KEY = config("BREVO_API_KEY", default="")
BREVO_WEBHOOK_TOKEN = config("BREVO_WEBHOOK_TOKEN", default="")
BREVO_NEWSLETTER_LIST_ID = config("BREVO_NEWSLETTER_LIST_ID", default=0, cast=int)
BREVO_DOI_TEMPLATE_ID = config("BREVO_DOI_TEMPLATE_ID", default=0, cast=int)
BREVO_INBOUND_DOMAIN = config("BREVO_INBOUND_DOMAIN", default="")
OCI_LICENSE_KEY_ID = config("OCI_LICENSE_KEY_ID", default="")
OCI_LICENSE_KEY_VERSION = config("OCI_LICENSE_KEY_VERSION", default="")
OCI_SIGNING_ENDPOINT = config("OCI_SIGNING_ENDPOINT", default="")
LICENSE_PUBLIC_KEYS_FILE = config("LICENSE_PUBLIC_KEYS_FILE", default="/etc/quantnest/license/public-keys.json")
LICENSE_INSTALLATION_ID = config("LICENSE_INSTALLATION_ID", default="")
LICENSE_ACTIVATION_TOKEN = config("LICENSE_ACTIVATION_TOKEN", default="")
LICENSE_SERVER_URL = config("LICENSE_SERVER_URL", default="")
QUANTNEST_PROXY_TOKEN = config("QUANTNEST_PROXY_TOKEN", default="")
QUANTNEST_RELEASE = config("QUANTNEST_RELEASE", default="development")
CREDENTIAL_ENCRYPTION_KEYS = config("CREDENTIAL_ENCRYPTION_KEYS", default="", cast=Csv())

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "backend.middleware.ingress.TrustedIngressMiddleware",
    "audit.middleware.AuditContextMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]
ASGI_APPLICATION = "backend.asgi.application"

# Fyers market-data config (used by marketdata views/processes)
FYERS_CLIENT_ID = config("FYERS_CLIENT_ID", default="")
FYERS_SECRET = config("FYERS_SECRET", default="")
FYERS_REDIRECT_URI = config("FYERS_REDIRECT_URI", default=f"{BACKEND_URL.rstrip('/')}/api/v1/market/fyers/callback/")

# Fyers broker-trading config (execution auth/session is isolated from market-data token storage)
BROKER_FYERS_CLIENT_ID = config("BROKER_FYERS_CLIENT_ID", default=FYERS_CLIENT_ID)
BROKER_FYERS_SECRET = config("BROKER_FYERS_SECRET", default=FYERS_SECRET)
BROKER_FYERS_REDIRECT_URI = config(
    "BROKER_FYERS_REDIRECT_URI",
    default=f"{BACKEND_URL.rstrip('/')}/api/v1/brokers/credentials/fyers/callback/",
)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL], "capacity": 1500, "expiry": 60},
    }
}


SITE_ID = 6
AUTH_USER_MODEL = "users.User"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    }
}

CORS_ALLOWED_ORIGINS = [
    FRONTEND_URL,
]
CORS_ALLOW_HEADERS = [*default_headers, "idempotency-key"]

CSRF_TRUSTED_ORIGINS = [
    FRONTEND_URL,
]

# Set these in production to redirect all traffic to HTTPS
SECURE_SSL_REDIRECT = not DEBUG
SECURE_REDIRECT_EXEMPT = [r"^api/v1/research/tools/$"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if QUANTNEST_PROXY_TOKEN else None
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = 2592000  # 30 days, increase after testing
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

REST_FRAMEWORK = {
    # TrustedIngress normalizes authenticated gateway addresses; ignore arbitrary XFF chains.
    "NUM_PROXIES": 0,
    "DEFAULT_RENDERER_CLASSES": (
        "backend.middleware.api_responses.APIJSONRenderer",
        "backend.middleware.api_responses.APIBrowsableRenderer",
    ),
    "EXCEPTION_HANDLER": "backend.middleware.api_responses.api_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "users.authentication.SafeJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "1000/hour",
        "user": "10000/hour",
    },
}

REST_AUTH = {
    "SESSION_LOGIN": False,
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": True,
    "JWT_AUTH_COOKIE": "quantnest-auth",
    "JWT_AUTH_REFRESH_COOKIE": "quantnest-refresh-session",
    "JWT_AUTH_SAMESITE": "Lax",
    "JWT_AUTH_SECURE": not DEBUG,
    "JWT_AUTH_REFRESH_COOKIE_PATH": "/api/v1/users/",
    "JWT_AUTH_COOKIE_USE_CSRF": True,
    "JWT_TOKEN_CLAIMS_SERIALIZER": "users.serializers.CustomTokenObtainPairSerializer",
    "OLD_PASSWORD_FIELD_ENABLED": True,
    "OTP_AUTH_ENABLED": True,
    "PASSWORD_RESET_CONFIRM_URL": "password/confirm/{uid}/{token}",
    "LOGIN_SERIALIZER": "dj_rest_auth.serializers.LoginSerializer",
    "TOKEN_SERIALIZER": "dj_rest_auth.serializers.TokenSerializer",
}

REST_AUTH_REGISTER_SERIALIZERS = {
    "REGISTER_SERIALIZER": "users.serializers.CustomRegisterSerializer",
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# allauth configuration
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = {
    "first_name": {"required": True},
    "last_name": {"required": True},
    "username": {"required": True},
    "email*": {"required": True},
    "password1": {"required": True},
    "password2": {"required": True},
}
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[QuantNest] "
ACCOUNT_EMAIL_BODY_HTML = True
LOGIN_URL = FRONTEND_URL + "/login"

EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp-relay.brevo.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="")

ACCOUNT_ADAPTER = "users.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "allauth.socialaccount.adapter.DefaultSocialAccountAdapter"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "CHECK_REVOKE_TOKEN": True,
    "TOKEN_OBTAIN_SERIALIZER": "users.serializers.CustomTokenObtainPairSerializer",
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("CACHE_URL", default=REDIS_URL),
        "TIMEOUT": 300,
        "OPTIONS": {"socket_connect_timeout": 5, "socket_timeout": 5, "retry_on_timeout": True},
    }
}

CACHES["marketdata"] = {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": MARKET_CACHE_URL, "TIMEOUT": 60,
}

CACHES["research"] = {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": RESEARCH_CACHE_URL, "TIMEOUT": 660,
    "OPTIONS": {"socket_connect_timeout": 3, "socket_timeout": 5},
}

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_TASK_TRACK_STARTED = True
CELERY_RESULT_EXPIRES = 3600
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 3600,
    "max_retries": 3,
}
# ── Use prefork (multi-process) pool to bypass Python GIL for CPU-bound
# historical computation. Live/Paper ticks run in quantnest_runtime, outside Celery.
# Compose separates the compute queue from background I/O and maintenance queues.
CELERY_WORKER_POOL = "prefork"
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Prevents long tasks monopolising workers
CELERY_TASK_ACKS_LATE = True           # Re-queue task if worker dies mid-execution
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 25
CELERY_TASK_TIME_LIMIT = 60 * 30
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "backtesting.*": {"queue": "compute"},
    "paper_trading.*": {"queue": "paper"},
    "marketdata.*": {"queue": "marketdata"},
    "instruments.*": {"queue": "marketdata"},
    "live_trading.*": {"queue": "live"},
    "notifications.*": {"queue": "notifications"},
    "research.start_research": {"queue": "compute"},
    "research.*": {"queue": "default"},
    "commercial.*": {"queue": "default"},
    "installations.*": {"queue": "default"},
    "common.*": {"queue": "default"},
    "users.*": {"queue": "default"},
}
CELERY_BEAT_SCHEDULE = {
    "customer-content-retention": {"task": "customer_support.retention", "schedule": 300.0},
    "commercial-reconcile": {"task": "commercial.reconcile", "schedule": 300.0},
    "private-licence-refresh": {"task": "installations.refresh", "schedule": 21600.0},
    "runtime-retention": {"task": "common.prune_runtime_records", "schedule": crontab(hour=2, minute=15)},
    "users-cleanup-expired-sessions": {
        "task": "users.cleanup_expired_sessions",
        "schedule": crontab(hour=3, minute=0),
    },
    "research-expire-abandoned-runs": {
        "task": "research.expire_runs",
        "schedule": 60.0,
    },
    "portfolio-daily-performance-nightly": {
        "task": "paper_trading.daily_performance_snapshot",
        "schedule": crontab(hour=0, minute=5),
    },
    "marketdata-refresh-live-subscriptions": {
        "task": "marketdata.refresh_live_market_subscriptions",
        "schedule": 30,
    },
    "instruments-sync-fyers-master-nightly": {
        "task": "instruments.sync_fyers_master",
        "schedule": crontab(hour=6, minute=0),
    },
    "live-trading-reconcile-oms": {
        "task": "live_trading.reconcile_all_active_accounts",
        "schedule": 60, # Every 1 minute
    },
    "portfolio-rebalance-allocations-nightly": {
        "task": "paper_trading.rebalance_all_portfolios",
        "schedule": crontab(hour=0, minute=15),
    },
    "risk-check-reenable-strategies": {
        "task": "risk_management.check_and_reenable_strategies",
        "schedule": 5 * 60,
    },
    "fetch-live-candles-every-1-min": {
        "task": "marketdata.fetch_live_candles_from_broker",
        "schedule": crontab(minute="*"),
    },
    "marketdata-reconcile-daily-market-data": {
        "task": "marketdata.reconcile_daily_market_data",
        "schedule": crontab(hour=23, minute=55),
    },
    "common-sync-market-holidays-daily": {
        "task": "common.sync_market_holidays",
        "schedule": crontab(hour=0, minute=5),
    },
}
if "live" not in EXECUTION_ENABLED_SCOPES:
    CELERY_BEAT_SCHEDULE.pop("live-trading-reconcile-oms")
if QUANTNEST_DEPLOYMENT_MODE != "private":
    CELERY_BEAT_SCHEDULE.pop("private-licence-refresh")


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "backend.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="127.0.0.1"),
        "PORT": config("DB_PORT", default="5432"),
        "OPTIONS": {"connect_timeout": 5},
    }
}

# Media Files Configuration
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CORS_ALLOW_CREDENTIALS = True

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# --- Logging ---
def _log_process_name():
    configured_name = os.environ.get("QUANTNEST_PROCESS_NAME")
    if configured_name:
        return configured_name

    arguments = [Path(argument).stem for argument in sys.argv]
    if "manage" in arguments:
        command_index = arguments.index("manage") + 1
        if command_index < len(arguments):
            return arguments[command_index]
    if "worker" in arguments:
        return "celery-worker"
    if "beat" in arguments:
        return "celery-beat"
    if "uvicorn" in arguments:
        return "uvicorn"

    return "django"


LOG_PROCESS_NAME = re.sub(r"[^A-Za-z0-9_.-]+", "_", _log_process_name())
PROCESS_LOG_FILE = BASE_DIR / "logs" / f"{LOG_PROCESS_NAME}-{os.getpid()}.log"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "process_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": PROCESS_LOG_FILE,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "process_file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "process_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "trading.management.commands": {
            "handlers": ["console", "process_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Containers use their supervisor's bounded console logs. Local development also
# keeps per-process files, with rotation so a long-running worker cannot fill disk.
if DEBUG and QUANTNEST_DEPLOYMENT_MODE == "development":
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    LOGGING["handlers"]["process_file"].update(
        {"class": "logging.handlers.RotatingFileHandler", "maxBytes": 10 * 1024 * 1024, "backupCount": 2}
    )
else:
    LOGGING["handlers"].pop("process_file")
    LOGGING["root"]["handlers"] = ["console"]
    for logger_config in LOGGING["loggers"].values():
        logger_config["handlers"] = ["console"]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
ROOT_URLCONF = "backend.urls"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
