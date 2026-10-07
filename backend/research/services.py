import logging
from types import SimpleNamespace
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from instruments.models import WatchlistInstrument, ExecutionRoute
from rules_engine.models import RuleGroup, Rule
from risk_management.models import StrategyAutoDisable
from strategies.serializers import StrategyCreateSerializer
from strategies.services import StrategySnapshotService
from .models import ResearchRun
from .validation import validate_draft, CONFIG_SERIALIZERS

logger = logging.getLogger(__name__)
ACTIVE = [ResearchRun.Status.PENDING, ResearchRun.Status.RUNNING]


def publish_run(run):
    # Progress contains no accumulated artifacts. Clients fetch the new revision once complete.
    data = {key: getattr(run, key) for key in ("id", "session_id", "revision", "status", "progress_message", "error_message")}
    data["session"] = data.pop("session_id")
    user_id = run.user_id
    def send():
        try:
            async_to_sync(get_channel_layer().group_send)(
                f"research_{user_id}", {"type": "research.update", "data": {"type": "research.update", "run": data}})
        except Exception:
            logger.exception("Could not broadcast research run %s", run.pk)
    transaction.on_commit(send)


def update_active_run(run_id, *, expected_status=None, **changes):
    with transaction.atomic():
        run = ResearchRun.objects.select_for_update().filter(pk=run_id).first()
        if not run or run.status not in ACTIVE:
            return None
        if expected_status is not None and run.status != expected_status:
            return None
        for key, value in changes.items():
            setattr(run, key, value)
        run.revision += 1
        run.save(update_fields=[*changes, "revision", "updated_at"])
        publish_run(run)
        return run


@transaction.atomic
def create_strategy_draft(run_id, user, draft):
    run = ResearchRun.objects.select_for_update().get(pk=run_id, user=user)
    if run.created_strategy_id:
        return run.created_strategy
    if run.status != ResearchRun.Status.COMPLETED:
        from rest_framework.exceptions import ValidationError
        raise ValidationError("Complete the research before creating its strategy draft.")
    from .context import research_instrument_ids
    draft = validate_draft(draft, research_instrument_ids(run))
    base_keys = {"name", "description", "strategy_type", "market_type", "exchange", "instrument_type"}
    serializer = StrategyCreateSerializer(data={key: draft[key] for key in base_keys if key in draft},
                                          context={"request": SimpleNamespace(user=user)})
    serializer.is_valid(raise_exception=True)
    strategy = serializer.save(paper_trading_enabled=True, live_trading_enabled=False, auto_version_enabled=False)
    for name, config_serializer in CONFIG_SERIALIZERS.items():
        config = config_serializer(getattr(strategy, name), data=draft[name], partial=True)
        config.is_valid(raise_exception=True)
        config.save()
    for group in draft["rule_groups"]:
        rules = group.pop("rules")
        created = RuleGroup.objects.create(strategy=strategy, **group)
        for rule in rules:
            Rule.objects.create(rule_group=created, **rule)
    for item in draft["watchlist_instruments"]:
        watchlist = WatchlistInstrument.objects.create(strategy=strategy, instrument_id=item["instrument_id"])
        ExecutionRoute.objects.create(watchlist_instrument=watchlist, route_type="DIRECT")
    for item in draft["auto_disable_rules"]:
        StrategyAutoDisable.objects.create(strategy=strategy, **item)
    StrategySnapshotService.create_snapshot(strategy, user=user, change_notes=f"Reviewed research draft from run {run.pk}")
    run.created_strategy = strategy
    run.revision += 1
    run.save(update_fields=["created_strategy", "revision", "updated_at"])
    publish_run(run)
    return strategy
