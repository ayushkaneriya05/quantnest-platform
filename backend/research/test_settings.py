"""Isolated SQLite settings for research verification, never the trading database."""
import os

os.environ["DEBUG"] = "False"
os.environ["USE_SQLITE"] = "True"
os.environ["SECRET_KEY"] = "research-tests-only"
from backend.settings import *  # noqa: E402,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
RESEARCH_SERVICE_TOKEN = "research-test-service-token"
CELERY_TASK_ALWAYS_EAGER = False
SECURE_SSL_REDIRECT = False
