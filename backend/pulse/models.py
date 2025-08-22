from django.db import models
from django.utils import timezone
from django.conf import settings

class PulseCache(models.Model):
    key = models.CharField(max_length=255, unique=True, db_index=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @classmethod
    def get(cls, key: str):
        try:
            obj = cls.objects.get(key=key)
            if obj.expires_at > timezone.now():
                return obj.payload
        except cls.DoesNotExist:
            return None
        return None

    @classmethod
    def put(cls, key: str, payload: dict, ttl_sec: int):
        exp = timezone.now() + timezone.timedelta(seconds=ttl_sec)
        obj, _ = cls.objects.update_or_create(
            key=key,
            defaults={'payload': payload, 'expires_at': exp}
        )
        return obj

class PulseHistory(models.Model):
    """Optional: store daily sentiment aggregates for trend chart."""
    as_of_date = models.DateField(db_index=True)
    n_headlines = models.IntegerField(default=0)
    pos = models.FloatField(default=0)
    neu = models.FloatField(default=0)
    neg = models.FloatField(default=0)
    summary = models.TextField(blank=True)

    class Meta:
        unique_together = (('as_of_date',),)