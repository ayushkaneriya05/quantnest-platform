from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")
BACKEND_URL = config("BACKEND_URL", default="http://localhost:8000")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CHANNEL_REDIS_URL = config("CHANNEL_REDIS_URL", default=REDIS_URL)
USE_IN_MEMORY_CHANNEL_LAYER = config("USE_IN_MEMORY_CHANNEL_LAYER", default=DEBUG, cast=bool)


INSTALLED_APPS = [
    "django.contrib.admin",
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
    "ai_engine",
    "marketplace",
    "audit",
    "platform_events",
    "community",
    "gamification",
    "learning",
    "reputation",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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
FYERS_REDIRECT_URI = config("FYERS_REDIRECT_URI", default="http://localhost:8000/api/v1/market/fyers/callback/")
FYERS_PIN = config("FYERS_PIN", default="")

# Fyers broker-trading config (execution auth/session is isolated from market-data token storage)
BROKER_FYERS_CLIENT_ID = config("BROKER_FYERS_CLIENT_ID", default=FYERS_CLIENT_ID)
BROKER_FYERS_SECRET = config("BROKER_FYERS_SECRET", default=FYERS_SECRET)
BROKER_FYERS_REDIRECT_URI = config(
    "BROKER_FYERS_REDIRECT_URI",
    default=f"{BACKEND_URL.rstrip('/')}/api/v1/brokers/credentials/fyers/callback/",
)
BROKER_FYERS_PIN = config("BROKER_FYERS_PIN", default=FYERS_PIN)

if USE_IN_MEMORY_CHANNEL_LAYER:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [CHANNEL_REDIS_URL],
                "capacity": 1500,
                "expiry": 60,
            },
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
        "VERIFIED_EMAIL": True,
    }
}

CORS_ALLOWED_ORIGINS = [
    FRONTEND_URL,
]

CSRF_TRUSTED_ORIGINS = [
    FRONTEND_URL,
]

# Set these in production to redirect all traffic to HTTPS
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = 2592000  # 30 days, increase after testing
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

REST_FRAMEWORK = {
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
    "JWT_AUTH_REFRESH_COOKIE": "quantnest-refresh",
    "JWT_AUTH_COOKIE_SAMESITE": "Lax",
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

EMAIL_BACKEND = config("EMAIL_BACKEND")
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")

ACCOUNT_ADAPTER = "users.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "allauth.socialaccount.adapter.DefaultSocialAccountAdapter"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "TOKEN_OBTAIN_SERIALIZER": "users.serializers.CustomTokenObtainPairSerializer",
}

if config("USE_LOCMEM_CACHE", default=False, cast=bool):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "quantnest-local-cache",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": config("CACHE_URL", default=REDIS_URL),
            "TIMEOUT": 300,
            "OPTIONS": {
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
            },
        }
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
# indicator computation. Each live/paper/backtest queue gets its own
# dedicated worker process via --queues CLI flag when launching Celery.
# Example launch commands:
#   celery -A backend worker -Q live      --pool=prefork -c 4 --loglevel=info
#   celery -A backend worker -Q paper     --pool=prefork -c 4 --loglevel=info
#   celery -A backend worker -Q backtest  --pool=prefork -c 2 --loglevel=info
#   celery -A backend worker -Q default,analytics,notifications --pool=prefork -c 2
CELERY_WORKER_POOL = "prefork"
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Prevents long tasks monopolising workers
CELERY_TASK_ACKS_LATE = True           # Re-queue task if worker dies mid-execution
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 25
CELERY_TASK_TIME_LIMIT = 60 * 30
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "backtesting.*": {"queue": "backtesting"},
    "paper_trading.*": {"queue": "paper"},
    "marketdata.*": {"queue": "marketdata"},
    "instruments.*": {"queue": "marketdata"},
    "live_trading.*": {"queue": "live"},
    "analytics.*": {"queue": "analytics"},
    "notifications.*": {"queue": "notifications"},
    "ai_engine.*": {"queue": "ai"},
    "platform_events.*": {"queue": "analytics"},
    "community.*": {"queue": "notifications"},
    "gamification.*": {"queue": "analytics"},
    "learning.*": {"queue": "analytics"},
    "reputation.*": {"queue": "analytics"},
}
CELERY_BEAT_SCHEDULE = {
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
    "analytics-refresh-daily-reports": {
        "task": "analytics.refresh_daily_reports",
        "schedule": 15 * 60,
    },
    "notifications-dispatch-daily-summaries": {
        "task": "notifications.dispatch_daily_summaries",
        "schedule": 60 * 60,
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
}


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


if config("USE_SQLITE", default=False, cast=bool):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST"),
            "PORT": config("DB_PORT"),
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
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs/django_warnings.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "trading.management.commands": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Ensure the logs directory exists
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

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
