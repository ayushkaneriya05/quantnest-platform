"""On-demand reports over execution records. No duplicate financial ledger."""
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, DecimalField, DurationField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce, NullIf, TruncDate
from django.utils import timezone
from rest_framework import serializers

from live_trading.models import LiveTrade
from paper_trading.models import PaperTrade
from trading.models import ClosedPositionLog


SOURCES = {
    "TERMINAL": {"model": ClosedPositionLog, "owner": "account__user", "pnl": "realized_pnl",
                 "account": "account_id", "review": "terminal_trade", "basis": "Before fees · manual simulation"},
    "PAPER": {"model": PaperTrade, "owner": "account__user", "pnl": "net_pnl",
              "account": "account_id", "review": "paper_trade", "basis": "Net of recorded simulated charges"},
    "LIVE": {"model": LiveTrade, "owner": "user", "pnl": "realized_pnl",
             "account": "broker_credential_id", "review": "live_trade", "basis": "Before fees · recorded live closes"},
}


class TradeFiltersSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=tuple(SOURCES), default="TERMINAL")
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    account_id = serializers.IntegerField(required=False, min_value=1)
    strategy_id = serializers.IntegerField(required=False, min_value=1)
    instrument_id = serializers.IntegerField(required=False, min_value=1)
    search = serializers.CharField(required=False, allow_blank=True, max_length=100)
    reviewed = serializers.ChoiceField(choices=["all", "reviewed", "unreviewed"], default="all")

    def validate(self, values):
        today = timezone.localdate()
        values.setdefault("date_to", today)
        values.setdefault("date_from", values["date_to"] - timedelta(days=29))
        if values["date_from"] > values["date_to"]:
            raise serializers.ValidationError("The start date must be before the end date.")
        if (values["date_to"] - values["date_from"]).days > 3660:
            raise serializers.ValidationError("Select a date range of at most ten years.")
        if values["source"] == "TERMINAL" and "strategy_id" in values:
            raise serializers.ValidationError("Terminal trades do not have a strategy.")
        return values


def trade_queryset(user, filters):
    source = SOURCES[filters["source"]]
    qs = source["model"].objects.filter(**{source["owner"]: user})
    zone = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(filters["date_from"], time.min), zone)
    end = timezone.make_aware(datetime.combine(filters["date_to"] + timedelta(days=1), time.min), zone)
    qs = qs.filter(exit_time__gte=start, exit_time__lt=end)
    for key in ("account_id", "strategy_id", "instrument_id"):
        if key in filters:
            qs = qs.filter(**{source["account"] if key == "account_id" else key: filters[key]})
    if filters.get("search"):
        qs = qs.filter(Q(instrument__symbol__icontains=filters["search"]) |
                       Q(instrument__name__icontains=filters["search"]))
    if filters.get("reviewed", "all") != "all":
        qs = qs.filter(journal_entry__isnull=filters["reviewed"] == "unreviewed")
    money = DecimalField(max_digits=20, decimal_places=2)
    annotations = {"pnl": F(source["pnl"]), "symbol": F("instrument__symbol"),
                   "account_key": F(source["account"]),
                   "duration": ExpressionWrapper(F("exit_time") - F("entry_time"), output_field=DurationField())}
    if filters["source"] == "TERMINAL":
        from django.db.models import IntegerField
        annotations.update(strategy_key=Value(None, output_field=IntegerField()), strategy_name=Value("Manual terminal"),
                           account_name=Value("Terminal account"), charges=Value(None, output_field=money),
                           exit_reason=Value(""))
    else:
        annotations.update(strategy_key=F("strategy_id"), strategy_name=F("strategy__name"))
        if filters["source"] == "PAPER":
            annotations.update(account_name=F("account__name"),
                               charges=ExpressionWrapper(F("brokerage") + F("taxes"), output_field=money))
        else:
            annotations.update(account_name=Coalesce(NullIf("broker_credential__label", Value("")), "broker_credential__broker_name", Value("Deleted broker account")),
                               charges=Value(None, output_field=money))
    return qs.annotate(**annotations)


def trade_rows(queryset, source, user):
    """Serialize only a page of closes; fetch its saved reviews in one query."""
    from trade_journal.models import JournalEntry
    from trade_journal.serializers import JournalEntrySerializer
    fields = ("id", "instrument_id", "symbol", "side", "quantity", "entry_price", "exit_price",
              "entry_time", "exit_time", "exit_reason", "pnl", "charges", "duration",
              "account_key", "account_name", "strategy_key", "strategy_name")
    rows = list(queryset.values(*fields))
    relation = SOURCES[source]["review"]
    reviews = JournalEntry.objects.filter(user=user, **{f"{relation}_id__in": [r["id"] for r in rows]})
    by_trade = {getattr(review, f"{relation}_id"): JournalEntrySerializer(review).data for review in reviews}
    for row in rows:
        row["duration_seconds"] = max(0, int(row.pop("duration").total_seconds()))
        row["source"] = source
        row["review"] = by_trade.get(row["id"])
    return rows


def execution_report(user, filters):
    qs = trade_queryset(user, filters).order_by()
    source = filters["source"]
    charges = {"recorded_charges": Sum("charges")} if source == "PAPER" else {}
    totals = qs.aggregate(closes=Count("id"), realized_pnl=Sum("pnl"),
                          wins=Count("id", filter=Q(pnl__gt=0)), losses=Count("id", filter=Q(pnl__lt=0)),
                          breakeven=Count("id", filter=Q(pnl=0)), average_pnl=Avg("pnl"),
                          profit=Sum("pnl", filter=Q(pnl__gt=0)), loss=Sum("pnl", filter=Q(pnl__lt=0)),
                          average_duration=Avg("duration"), **charges)
    count = totals["closes"]
    total_loss = abs(totals.pop("loss") or Decimal("0"))
    profit = totals.pop("profit") or Decimal("0")
    duration = totals.pop("average_duration")
    totals.update(realized_pnl=totals["realized_pnl"] or Decimal("0"),
                  recorded_charges=(totals.get("recorded_charges") or Decimal("0")) if source == "PAPER" else None,
                  average_pnl=totals["average_pnl"] if count else None,
                  win_rate=Decimal(totals["wins"]) / count * 100 if count else None,
                  profit_factor=profit / total_loss if total_loss else None,
                  average_duration_seconds=int(duration.total_seconds()) if duration else None)

    def breakdown(fields):
        rows = list(qs.values(*fields).annotate(closes=Count("id"), realized_pnl=Sum("pnl"),
                    wins=Count("id", filter=Q(pnl__gt=0))).order_by("-realized_pnl"))
        for row in rows:
            row["win_rate"] = Decimal(row["wins"]) / row["closes"] * 100
        return rows

    daily = list(qs.annotate(date=TruncDate("exit_time")).values("date")
                 .annotate(closes=Count("id"), realized_pnl=Sum("pnl")).order_by("date"))
    cumulative = Decimal("0")
    for row in daily:
        cumulative += row["realized_pnl"]
        row["cumulative_pnl"] = cumulative
    from trade_journal.services import SUGGESTED_TAGS
    return {"source": source, "filters": filters, "observed_at": timezone.now(), "pnl_basis": SOURCES[source]["basis"],
            "counting_unit": "Recorded closes; partial exits count separately.", "summary": totals,
            "daily": daily, "instruments": breakdown(("instrument_id", "symbol")),
            "strategies": breakdown(("strategy_key", "strategy_name")) if source != "TERMINAL" else [],
            "suggested_tags": SUGGESTED_TAGS,
            "current_positions": current_position_marks(user, filters),
            "limitations": ["Closed P&L excludes current open positions and cash transfers.",
                            "Account equity returns, Sharpe and equity drawdown require a verified historical equity series."]}


def current_position_marks(user, filters):
    """Read cached quotes on demand, never request broker prices or update positions."""
    from live_trading.models import LivePosition
    from paper_trading.models import PaperPosition
    from trading.models import Position
    from marketdata.quote_store import QuoteStore
    from redis.exceptions import RedisError

    source = filters["source"]
    model = {"TERMINAL": Position, "PAPER": PaperPosition, "LIVE": LivePosition}[source]
    qs = model.objects.filter(**{SOURCES[source]["owner"]: user}).exclude(quantity=0)
    for key in ("account_id", "strategy_id", "instrument_id"):
        if key in filters:
            qs = qs.filter(**{SOURCES[source]["account"] if key == "account_id" else key: filters[key]})
    if filters.get("search"):
        qs = qs.filter(Q(instrument__symbol__icontains=filters["search"]) | Q(instrument__name__icontains=filters["search"]))
    qs = qs.select_related("instrument")
    total, quotes, times, count, missing = Decimal("0"), {}, [], 0, 0
    for position in qs:
        count += 1
        symbol = position.instrument.sym_ticker
        if symbol not in quotes:
            try:
                quotes[symbol] = QuoteStore.get_latest(symbol, max_age_seconds=60)
            except (RedisError, OSError):
                return {"positions": len(qs), "unrealized_pnl": None, "unpriced_positions": len(qs),
                        "oldest_quote_at": None, "basis": "Current marks unavailable because the quote cache could not be reached. Historical closes are unaffected."}
        quote = quotes[symbol]
        raw_price = quote.get("price", quote.get("ltp")) if quote else None
        try:
            price = Decimal(str(raw_price))
        except (InvalidOperation, TypeError, ValueError):
            missing += 1
            continue
        if not price.is_finite() or price <= 0:
            missing += 1
            continue
        quantity = position.quantity
        average = position.average_price if source == "TERMINAL" else position.avg_price
        if source != "TERMINAL" and position.side == "SELL":
            quantity = -quantity
        total += (price - average) * quantity
        times.append(quote["updated_at"])
    return {"positions": count, "unrealized_pnl": None if missing else total, "unpriced_positions": missing,
            "oldest_quote_at": min(times) if times else None,
            "basis": "Current open positions · before exit costs · cached quotes up to 60 seconds old. Date and review-status filters apply only to closed records."}


class ExecutionReviewSerializer(serializers.Serializer):
    filters = TradeFiltersSerializer()
    trade_id = serializers.IntegerField(required=False, min_value=1)
    include_notes = serializers.BooleanField(default=False)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError("Unsupported execution review settings.")
        return super().to_internal_value(data)


def execution_review_context(user, settings):
    """Freeze owned, calculated evidence; saved notes require explicit consent."""
    from django.shortcuts import get_object_or_404
    from research.validation import json_data
    from trade_journal.models import JournalEntry

    serializer = ExecutionReviewSerializer(data=settings)
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    filters = values["filters"]
    source = filters["source"]
    qs = trade_queryset(user, filters)
    report = execution_report(user, filters)
    if values.get("trade_id"):
        trade = get_object_or_404(qs, pk=values["trade_id"])
        qs = qs.filter(pk=trade.pk)
        closes = trade_rows(qs, source, user)
        report["scope"] = "Selected close; period summary is separate context."
    else:
        # Actual extremes, not an arbitrary latest page presented as a full ledger.
        ids = list(qs.order_by("pnl", "id").values_list("id", flat=True)[:5])
        ids += list(qs.order_by("-pnl", "id").values_list("id", flat=True)[:5])
        closes = trade_rows(qs.filter(pk__in=ids).order_by("pnl", "id"), source, user)
        report["scope"] = "Period summary with at most five strongest and five weakest recorded closes."
    for close in closes:
        close.pop("review", None)
    relation = SOURCES[source]["review"]
    notes = []
    if values["include_notes"]:
        entries = JournalEntry.objects.filter(user=user, source=source, **{f"{relation}_id__in": qs.values("id")})
        notes = [{"trade_id": getattr(entry, f"{relation}_id"), "title": entry.title,
                  "notes": entry.notes[:1500], "lessons_learned": entry.lessons_learned[:1500],
                  "mistake_tags": entry.mistake_tags, "execution_quality": entry.execution_quality}
                 for entry in entries.order_by("-updated_at", "-id")[:20]]
    report.update(as_of=report.pop("observed_at"), closes=closes, user_assessments=notes,
                  notes_included=values["include_notes"])
    report.pop("suggested_tags")
    report["daily"] = report["daily"][-365:]
    report["instruments"] = report["instruments"][:50]
    report["strategies"] = report["strategies"][:50]
    report["limitations"].append("Charts show at most the latest 365 closing dates; breakdowns show the top 50 groups. Totals cover the full selected period.")
    if notes:
        report["limitations"].append("Up to 20 saved reviews, with text excerpts, are user assessments and cannot prove a trading cause.")
    return json_data(values), json_data(report)
