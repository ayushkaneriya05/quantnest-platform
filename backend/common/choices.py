"""Small, permission-scoped option lists for searchable dropdowns."""
from django.db.models import Case, F, IntegerField, Q, Value, When
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from backtesting.models import BacktestRun
from brokers.models import BrokerChargeProfile, BrokerCredential
from brokers.services import BROKER_CATALOG
from live_trading.models import LiveStrategyAllocation
from paper_trading.models import CapitalAllocation, PaperAccount
from research.models import ResearchSession
from strategies.models import Strategy, StrategyTag, StrategyVersion


PAGE_SIZE = 20

# Only these fields are exposed; full configurations and credentials are never loaded.
SOURCES = {
    "strategies": {
        "model": Strategy, "owner": "user", "fields": ("name",),
        "annotations": {"timeframe": F("time_rule__candle_timeframe")},
        "search": ("name",), "filters": ("status", "paper_trading_enabled", "live_trading_enabled"),
        "label": lambda row: row["name"],
    },
    "strategy-versions": {
        "model": StrategyVersion, "owner": "strategy__user",
        "fields": ("version_number", "created_at", "change_notes"),
        "search": ("version_number", "change_notes"), "filters": ("strategy_id",),
        "required": "strategy_id",
        "label": lambda row: f"Version {row['version_number']} · {row['created_at'].date().isoformat()}",
    },
    "charge-profiles": {
        "model": BrokerChargeProfile, "owner": "user", "fields": ("name", "is_default"),
        "search": ("name",), "filters": (),
        "label": lambda row: row["name"] + (" (Default)" if row["is_default"] else ""),
    },
    "broker-accounts": {
        "model": BrokerCredential, "owner": "user", "fields": ("broker_name", "label", "client_id"),
        "search": ("broker_name", "label", "client_id"), "filters": ("is_active", "is_verified"),
        "scope": {"broker_name__in": [name for name, config in BROKER_CATALOG.items() if config["enabled"]]},
        "label": lambda row: f"{row['broker_name']} · {row['label'] or row['client_id']}",
    },
    "paper-accounts": {
        "model": PaperAccount, "owner": "user", "fields": ("name", "current_balance"),
        "search": ("name", "allocation__strategy__name"), "filters": (),
        "label": lambda row: f"{row['name']} · ₹{row['current_balance']:,.2f}",
    },
    "paper-allocations": {
        "model": CapitalAllocation, "owner": "portfolio__user",
        "fields": ("strategy__name", "allocated_amount"), "search": ("strategy__name",),
        "filters": ("strategy_id", "strategy__status", "strategy__paper_trading_enabled", "paper_account__isnull"),
        "label": lambda row: f"{row['strategy__name']} · Allocation #{row['id']} · ₹{row['allocated_amount']:,.2f}",
    },
    "live-allocations": {
        "model": LiveStrategyAllocation, "owner": "user",
        "fields": ("strategy__name", "broker_credential__broker_name", "broker_credential__label", "broker_credential__client_id"),
        "search": ("strategy__name", "broker_credential__label", "broker_credential__broker_name"),
        "filters": ("strategy_id",),
        "label": lambda row: f"{row['strategy__name']} · {row['broker_credential__broker_name']} · "
            f"{row['broker_credential__label'] or row['broker_credential__client_id']}",
    },
    "backtests": {
        "model": BacktestRun, "owner": "user", "fields": ("name", "status"),
        "search": ("name", "strategy__name"), "filters": ("status",),
        "label": lambda row: row["name"],
    },
    "screens": {
        "model": ResearchSession, "owner": "user", "fields": ("title",),
        "search": ("title",), "filters": (), "scope": {"kind": "SCREEN"},
        "ordering": ("-updated_at", "-id"), "label": lambda row: row["title"],
    },
    "strategy-tags": {
        "model": StrategyTag, "owner": None, "fields": ("name",),
        "search": ("name",), "filters": (), "ordering": ("-id",),
        "label": lambda row: row["name"],
    },
}


class ChoiceQuerySerializer(serializers.Serializer):
    resource = serializers.ChoiceField(choices=tuple(SOURCES))
    search = serializers.CharField(required=False, allow_blank=True, max_length=160)
    page = serializers.IntegerField(default=1, min_value=1)
    id = serializers.IntegerField(required=False, min_value=1)
    strategy_id = serializers.IntegerField(required=False, min_value=1)
    status = serializers.CharField(required=False, max_length=20)
    paper_trading_enabled = serializers.BooleanField(required=False)
    live_trading_enabled = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)

    is_verified = serializers.BooleanField(required=False)
    strategy__status = serializers.CharField(required=False, max_length=20)
    strategy__paper_trading_enabled = serializers.BooleanField(required=False)
    paper_account__isnull = serializers.BooleanField(required=False)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def choices(request):
    # Query filters are optional values, not HTML checkboxes: omitted booleans
    # must stay absent instead of being interpreted as False by DRF.
    params = ChoiceQuerySerializer(data=request.query_params.dict())
    params.is_valid(raise_exception=True)
    values = params.validated_data
    source = SOURCES[values["resource"]]
    required = source.get("required")
    if required and required not in values:
        raise serializers.ValidationError({required: "This filter is required."})
    queryset = source["model"].objects.all()
    if source["owner"]:
        queryset = queryset.filter(**{source["owner"]: request.user})
    queryset = queryset.filter(**source.get("scope", {}))
    queryset = queryset.filter(**{key: values[key] for key in source["filters"] if key in values})
    ordering = source.get("ordering", ("-created_at", "-id"))
    if "id" in values:
        queryset = queryset.filter(pk=values["id"])
    elif values.get("search"):
        search = Q()
        exact = Q()
        for field in source["search"]:
            search |= Q(**{f"{field}__icontains": values["search"]})
            exact |= Q(**{f"{field}__iexact": values["search"]})
        queryset = queryset.filter(search).annotate(choice_match_rank=Case(
            When(exact, then=Value(0)), default=Value(1), output_field=IntegerField(),
        ))
        ordering = ("choice_match_rank", *ordering)
    annotations = source.get("annotations", {})
    queryset = queryset.annotate(**annotations)
    offset = (values["page"] - 1) * PAGE_SIZE
    rows = list(queryset.order_by(*ordering)
                .values("id", *source["fields"], *annotations)[offset:offset + PAGE_SIZE + 1])
    return Response({
        "results": [{**row, "value": str(row["id"]), "label": source["label"](row)} for row in rows[:PAGE_SIZE]],
        "has_more": len(rows) > PAGE_SIZE,
        "page": values["page"],
    })
