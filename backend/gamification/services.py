from django.db import IntegrityError, transaction

from .models import UserXPBalance, XPEvent, XPGrantLimit


class GamificationService:
    @staticmethod
    def grant_xp(user, source_type, points, source=None, metadata=None, quality_score=1):
        source_model = source.__class__.__name__ if source is not None else ""
        source_id = str(getattr(source, "id", "")) if source is not None else ""
        key = f"{user.id}:{source_type}:{source_model}:{source_id}"
        limit = XPGrantLimit.objects.filter(source_type=source_type, is_active=True).first()
        if limit and quality_score < limit.min_quality_score:
            return None
        try:
            with transaction.atomic():
                event = XPEvent.objects.create(
                    user=user,
                    source_type=source_type,
                    source_model=source_model,
                    source_id=source_id,
                    points=points,
                    quality_score=quality_score,
                    metadata=metadata or {},
                    idempotency_key=key,
                )
                balance, _ = UserXPBalance.objects.select_for_update().get_or_create(user=user)
                balance.total_xp += points
                balance.weekly_xp += points
                balance.monthly_xp += points
                balance.level = max(1, int(balance.total_xp / 500) + 1)
                balance.save(update_fields=["total_xp", "weekly_xp", "monthly_xp", "level", "updated_at"])
                return event
        except IntegrityError:
            return XPEvent.objects.filter(idempotency_key=key).first()

