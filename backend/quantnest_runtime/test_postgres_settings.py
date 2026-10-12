"""Disposable PostgreSQL tests with local caches and no trading services.

The Django test runner creates and drops a uniquely named test database.
Never use these settings to run an API, Celery worker or execution runtime.
"""
import os
import uuid
from copy import deepcopy
os.environ["DEBUG"] = "False"
os.environ["USE_SQLITE"] = "False"
from backend.settings import *

DATABASES = deepcopy(DATABASES)
DATABASES["default"]["TEST"] = {"NAME": "test_quantnest_audit_" + uuid.uuid4().hex[:10]}
CACHES = {name: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": name}
          for name in ("default", "research", "marketdata")}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
SECURE_SSL_REDIRECT = False
CELERY_TASK_ALWAYS_EAGER = False
RESEARCH_SERVICE_TOKEN = "research-test-service-token"
