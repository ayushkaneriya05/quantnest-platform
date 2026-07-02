from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import ActivityEvent, DomainEvent


class DomainEventService:
    @staticmethod
    def emit(event_type, user=None, source=None, payload=None, idempotency_key=None, source_app=""):
        source_model = source.__class__.__name__ if source is not None else ""
        source_id = str(getattr(source, "id", "")) if source is not None else ""
        key = idempotency_key or f"{event_type}:{source_app}:{source_model}:{source_id}:{getattr(user, 'id', 'system')}"
        try:
            with transaction.atomic():
                return DomainEvent.objects.create(
                    event_type=event_type,
                    user=user,
                    source_app=source_app,
                    source_model=source_model,
                    source_id=source_id,
                    idempotency_key=key,
                    payload=payload or {},
                )
        except IntegrityError:
            return DomainEvent.objects.get(idempotency_key=key)

    @staticmethod
    def mark_processed(event):
        event.status = "PROCESSED"
        event.processed_at = timezone.now()
        event.error_message = ""
        event.save(update_fields=["status", "processed_at", "error_message", "updated_at"])
        return event


class ActivityService:
    @staticmethod
    def create(user, activity_type, title, summary="", target=None, metadata=None, domain_event=None, topic_slug="", strategy=None, visibility="PUBLIC"):
        target_type = target.__class__.__name__ if target is not None else ""
        target_id = str(getattr(target, "id", "")) if target is not None else ""
        return ActivityEvent.objects.create(
            user=user,
            activity_type=activity_type,
            title=title,
            summary=summary,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata or {},
            domain_event=domain_event,
            topic_slug=topic_slug,
            strategy=strategy,
            visibility=visibility,
        )

