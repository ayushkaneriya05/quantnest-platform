"""Isolated authentication checks never connect to the trading database."""
import os

os.environ["DEBUG"] = "False"
os.environ["USE_SQLITE"] = "True"
os.environ["SECRET_KEY"] = "auth-tests-only-key-at-least-32-characters"
from backend.settings import *  # noqa: E402,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
RESEARCH_SERVICE_TOKEN = "research-test-service-token"
SECURE_SSL_REDIRECT = False
ALLOWED_HOSTS = ["testserver", "localhost"]
