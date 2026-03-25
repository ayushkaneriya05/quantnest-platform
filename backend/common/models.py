"""
Common app - base models for QuantNest Algo Trading Platform.
"""
from django.db import models


class BaseTimestampModel(models.Model):
    """Abstract base model with timestamp fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

