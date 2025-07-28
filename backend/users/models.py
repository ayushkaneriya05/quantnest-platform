from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError


class User(AbstractUser):
    email = models.EmailField(
        unique=True,
    )
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
    REQUIRED_FIELDS = ["email"]

    def clean(self):
        super().clean()
        if self.bio and len(self.bio.strip()) < 10:
            raise ValidationError({"bio": "Bio must be at least 10 characters long."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
