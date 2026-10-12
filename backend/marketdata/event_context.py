"""Load event data once before a historical job or during worker context refresh."""
from collections import defaultdict
from django.db.models import Q


def load_events(instrument_id, start, end):
    from marketdata.models import MarketEvent
    result = defaultdict(set)
    rows = MarketEvent.objects.filter(
        Q(instrument_id=instrument_id) | Q(instrument_id__isnull=True),
        event_date__gte=start, event_date__lte=end,
    ).values_list("event_date", "event_type")
    for day, event_type in rows:
        result[day].add(event_type)
    return dict(result)
