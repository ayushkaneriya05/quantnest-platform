import hashlib
import secrets
import string
import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models


class User(AbstractUser):
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True)
    username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        unique=True,
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        validators=[MinLengthValidator(10, "Bio must be at least 10 characters long.")],
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_2fa_enabled = models.BooleanField(default=False)
    REQUIRED_FIELDS = ["email"]

    def clean(self):
        super().clean()
        if self.bio and len(self.bio.strip()) < 10:
            raise ValidationError({"bio": "Bio must be at least 10 characters long."})

    def __str__(self):
        return self.username or self.email


class BackupCode(models.Model):
    """One-time-use backup codes for 2FA recovery."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="backup_codes")
    code_hash = models.CharField(max_length=128)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "used" if self.is_used else "active"
        return f"BackupCode({self.user.username}, {status})"

    @staticmethod
    def generate_codes(count=10):
        """Generate a set of backup codes. Returns list of (raw_code, code_hash)."""
        codes = []
        for _ in range(count):
            raw_code = "".join(secrets.choice(string.digits) for _ in range(8))
            # Format as XXXX-XXXX for readability
            formatted = f"{raw_code[:4]}-{raw_code[4:]}"
            code_hash = hashlib.sha256(formatted.encode()).hexdigest()
            codes.append((formatted, code_hash))
        return codes

    @staticmethod
    def verify_code(user, raw_code):
        """Verify a backup code. Returns True if valid and marks it as used."""
        from django.utils import timezone

        digits = raw_code.replace("-", "").replace(" ", "").strip()
        if len(digits) != 8 or not digits.isdigit():
            return False
        formatted = f"{digits[:4]}-{digits[4:]}"
        code_hash = hashlib.sha256(formatted.encode()).hexdigest()
        updated = BackupCode.objects.filter(
            user=user, code_hash=code_hash, is_used=False
        ).update(is_used=True, used_at=timezone.now())
        return bool(updated)


class UserSession(models.Model):
    """Tracks active JWT sessions for a user with metadata."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    session_id = models.UUIDField(unique=True, help_text="Constant Session Identifier", default=uuid.uuid4)
    device_id = models.UUIDField(default=uuid.uuid4, editable=False)
    refresh_jti = models.CharField(max_length=255, editable=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    device_type = models.CharField(max_length=50, default="Unknown")
    browser = models.CharField(max_length=50, default="Unknown")
    os = models.CharField(max_length=50, default="Unknown")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_activity"]
        constraints = [
            models.UniqueConstraint(fields=["user", "device_id"], name="unique_user_browser_session"),
        ]

    def __str__(self):
        return f"Session({self.user.username}, {self.ip_address})"
