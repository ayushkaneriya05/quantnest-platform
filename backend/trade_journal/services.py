from collections import Counter
from decimal import Decimal
from django.db.models import Avg
from analytics.services import SOURCES, trade_queryset
from .models import JournalEntry


SUGGESTED_TAGS = ["Early entry", "Late entry", "Early exit", "Late exit", "Oversized position",
                  "Ignored stop", "Chased price", "Unplanned trade", "Execution issue"]


def journal_summary(user, filters):
    trades = trade_queryset(user, {**filters, "reviewed": "all"})
    relation = SOURCES[filters["source"]]["review"]
    entries = JournalEntry.objects.filter(user=user, source=filters["source"], **{f"{relation}_id__in": trades.values("id")})
    reviewed = entries.count()
    total = trades.count()
    tags = Counter()
    tag_pnl = Counter()
    pnl_field = SOURCES[filters["source"]]["pnl"]
    for values, pnl in entries.values_list("mistake_tags", f"{relation}__{pnl_field}").iterator():
        tags.update(set(values))
        for tag in set(values):
            tag_pnl[tag] += pnl or Decimal("0")
    return {"source": filters["source"], "closes": total, "reviewed": reviewed, "unreviewed": total - reviewed,
            "average_rating": entries.aggregate(value=Avg("execution_quality"))["value"],
            "mistake_tags": [{"tag": tag, "reviews": count, "realized_pnl": tag_pnl[tag]} for tag, count in tags.most_common(12)],
            "suggested_tags": SUGGESTED_TAGS,
            "assessment_label": "Ratings and mistake tags are user assessments."}
