"""Field encryption with explicit key rotation; no plaintext read fallback."""
import base64
import hashlib
from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


def cipher():
    keys = settings.CREDENTIAL_ENCRYPTION_KEYS
    if not keys:
        if settings.QUANTNEST_DEPLOYMENT_MODE != "development":
            raise ImproperlyConfigured("Configure separate credential encryption keys before storing broker/source credentials")
        keys = [base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest()).decode()]
    return MultiFernet([Fernet(key.encode()) for key in keys])


class EncryptedTextField(models.TextField):
    def from_db_value(self, value, expression, connection):
        return cipher().decrypt(value.encode()).decode() if value else value
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return cipher().encrypt(value.encode()).decode() if value else value
