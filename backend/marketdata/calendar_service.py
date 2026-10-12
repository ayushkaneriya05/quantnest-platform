"""Market event queries for the calendar API; execution preloads event_context."""
from .models import MarketEvent


class EventCalendarService:
    @staticmethod
    def get_events(date_from, date_to, event_types=None):
        queryset = MarketEvent.objects.filter(event_date__gte=date_from, event_date__lte=date_to)
        if event_types:
            queryset = queryset.filter(event_type__in=event_types)
        return queryset.select_related("instrument")
