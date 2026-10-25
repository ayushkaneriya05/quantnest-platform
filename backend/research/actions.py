"""Validate previews and execute only explicit, idempotent confirmations."""

import logging
from types import SimpleNamespace

from backtesting.models import BacktestRun
from backtesting.serializers import BacktestRunSerializer
from backtesting.services import backtest_configuration, create_backtest, start_backtest
from brokers.models import BrokerChargeProfile
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from instruments.models import ExecutionRoute, WatchlistInstrument
from rest_framework.exceptions import APIException, ValidationError
from rules_engine.models import Rule, RuleGroup
from strategies.models import Strategy
from strategies.serializers import StrategyCreateSerializer
from strategies.services import StrategySnapshotService

from .context import active_stocks, research_instrument_ids
from .models import ResearchAction, ResearchRun
from .services import publish_run
from .validation import CONFIG_SERIALIZERS, json_data, validate_draft

logger = logging.getLogger(__name__)


# Create a strategy draft.


def preview_strategy_draft(run, payload):
    if set(payload) - {"evidence_id"}:
        raise ValidationError("Choose a validated draft artifact.")
    evidence_id = payload.get("evidence_id") or run.result.get("draft_evidence_id")
    evidence = next(
        (
            item
            for item in run.evidence
            if item["evidence_id"] == evidence_id and item["tool"] == "validate_strategy_draft"
        ),
        None,
    )
    if not evidence:
        raise ValidationError("The draft must pass backend validation first.")
    return {
        "draft": validate_draft(evidence["data"]["draft"], research_instrument_ids(run)),
        "evidence_id": evidence_id,
    }


def execute_strategy_draft(run, payload):
    """Called only inside confirm_action's locked transaction."""
    user = run.user
    draft = payload["draft"]
    if run.created_strategy_id:
        return {"strategy_id": run.created_strategy_id}
    draft = validate_draft(draft, research_instrument_ids(run))
    base_keys = {"name", "description", "strategy_type", "market_type", "exchange", "instrument_type"}
    serializer = StrategyCreateSerializer(
        data={key: draft[key] for key in base_keys if key in draft}, context={"request": SimpleNamespace(user=user)}
    )
    serializer.is_valid(raise_exception=True)
    strategy = serializer.save(paper_trading_enabled=True, live_trading_enabled=False, auto_version_enabled=False)
    for name, config_serializer in CONFIG_SERIALIZERS.items():
        config = config_serializer(getattr(strategy, name), data=draft[name], partial=True)
        config.is_valid(raise_exception=True)
        config.save()
    for group in draft["rule_groups"]:
        rules = group["rules"]
        created = RuleGroup.objects.create(
            strategy=strategy, **{key: value for key, value in group.items() if key != "rules"}
        )
        for rule in rules:
            Rule.objects.create(rule_group=created, **rule)
    for item in draft["watchlist_instruments"]:
        watchlist = WatchlistInstrument.objects.create(strategy=strategy, instrument_id=item["instrument_id"])
        ExecutionRoute.objects.create(watchlist_instrument=watchlist, route_type="DIRECT")
    StrategySnapshotService.create_snapshot(
        strategy, user=user, change_notes=f"Reviewed research draft from run {run.pk}"
    )
    run.created_strategy = strategy
    run.save(update_fields=["created_strategy", "updated_at"])
    return {"strategy_id": strategy.pk}


# Add selected stocks to the watchlist.


def preview_watchlist(run, payload):
    if set(payload) - {"instrument_ids", "watchlist_id"}:
        raise ValidationError("Provide selected instrument IDs and a terminal watchlist.")
    ids = payload.get("instrument_ids", [])
    if (
        not isinstance(ids, list)
        or not ids
        or any(type(value) is not int for value in ids)
        or set(ids) - set(research_instrument_ids(run))
    ):
        raise ValidationError("Select instruments from this research evidence.")
    resolved = {"instrument_ids": list(dict.fromkeys(ids)), "instruments": active_stocks(ids)}
    if payload.get("watchlist_id") is not None:
        from trading.models import Watchlist

        identity = payload["watchlist_id"]
        if type(identity) is not int or identity < 1:
            raise ValidationError("Select a terminal watchlist.")
        watchlist = get_object_or_404(Watchlist, pk=identity, user=run.user)
        resolved.update(watchlist_id=watchlist.pk, watchlist_name=watchlist.name)
    return resolved


def execute_watchlist(run, payload):
    from trading.models import Watchlist

    if not payload.get("watchlist_id"):
        raise ValidationError("Select a terminal watchlist and preview the additions before confirming.")
    active_stocks(payload["instrument_ids"])
    watchlist = get_object_or_404(Watchlist, pk=payload["watchlist_id"], user=run.user)
    watchlist.instruments.add(*payload["instrument_ids"])
    return {"watchlist_id": watchlist.pk, "instrument_ids": payload["instrument_ids"]}


# Start a reviewed backtest.


def preview_backtest(run, payload):
    allowed = {
        "strategy_id",
        "source_backtest_id",
        "name",
        "start_date",
        "end_date",
        "initial_capital",
        "slippage_pct",
        "include_charges",
        "charge_profile",
    }
    if set(payload) - allowed:
        raise ValidationError("Unsupported backtest settings.")
    settings = dict(payload)
    source_id = settings.pop("source_backtest_id", None)
    strategy_id = settings.pop("strategy_id", None) or run.created_strategy_id or run.request.get("strategy_id")
    saved_costs = None
    if source_id:
        if source_id not in run.request.get("backtest_ids", []):
            raise ValidationError("Attach the backtest before proposing a rerun.")
        source = get_object_or_404(BacktestRun, pk=source_id, user_id=run.user_id, status="COMPLETED")
        strategy_id, snapshot = source.strategy_id, backtest_configuration(source)
        if "charge_profile" not in payload:
            saved_costs = source.charge_profile_snapshot
        settings = {
            **{
                key: getattr(source, key)
                for key in ("name", "start_date", "end_date", "initial_capital", "slippage_pct", "include_charges")
            },
            "charge_profile": source.charge_profile_id,
            **settings,
        }
    elif strategy_id == run.created_strategy_id and strategy_id:
        snapshot = run.created_strategy.versions.order_by("-version_number").first().config_snapshot
    elif strategy_id == run.request.get("strategy_id") and strategy_id:
        snapshot = run.request["strategy_snapshot"]
    else:
        raise ValidationError("Attach a strategy or create the reviewed draft before testing it.")
    strategy = get_object_or_404(Strategy, pk=strategy_id, user_id=run.user_id)
    default_profile = BrokerChargeProfile.objects.filter(user_id=run.user_id, is_default=True).first()
    settings.setdefault("charge_profile", default_profile.pk if default_profile else None)
    settings.setdefault("include_charges", True)
    settings.setdefault("initial_capital", 100000)
    settings.setdefault("slippage_pct", "0.05")
    settings.setdefault("name", f"{strategy.name} research experiment")
    serializer = BacktestRunSerializer(
        data={**settings, "strategy": strategy.pk},
        context={"request": SimpleNamespace(user=run.user, headers={}), "charge_profile_snapshot": saved_costs or {}},
    )
    serializer.is_valid(raise_exception=True)
    validated = serializer.validated_data
    profile = validated.get("charge_profile")
    from common.costs import snapshot_charge_profile

    saved_costs = saved_costs if saved_costs is not None else snapshot_charge_profile(profile)
    from commercial.usage import estimate_backtest_workload

    estimate = estimate_backtest_workload(run.user, snapshot, validated["start_date"], validated["end_date"])
    return json_data(
        {
            **{
                key: validated[key]
                for key in ("name", "start_date", "end_date", "initial_capital", "slippage_pct", "include_charges")
            },
            "strategy": strategy.pk,
            "snapshot": snapshot,
            "charge_profile": profile.pk if profile else None,
            "charge_profile_name": saved_costs.get("name"),
            "charge_profile_snapshot": saved_costs,
            "estimate_token": estimate["token"],
            "workload_estimate": estimate,
        }
    )


def execute_backtest(run, payload):
    settings = {
        key: value
        for key, value in payload.items()
        if key not in {"snapshot", "charge_profile_name", "charge_profile_snapshot", "workload_estimate"}
    }
    get_object_or_404(Strategy, pk=settings["strategy"], user=run.user)
    serializer = BacktestRunSerializer(
        data=settings,
        context={
            "request": SimpleNamespace(user=run.user, headers={}),
            "charge_profile_snapshot": payload.get("charge_profile_snapshot", {}),
        },
    )
    serializer.is_valid(raise_exception=True)
    backtest = create_backtest(
        serializer,
        run.user,
        approved_snapshot=payload["snapshot"],
        charge_profile_snapshot=payload.get("charge_profile_snapshot"),
    )
    start_backtest(backtest)
    return {"backtest_id": backtest.pk}


# Persistent capabilities require BOTH a validated preview and explicit confirmation.
# Adding one action does not change the shared confirmation/rollback workflow.
ACTION_HANDLERS = {
    ResearchAction.Type.CREATE_DRAFT: (preview_strategy_draft, execute_strategy_draft),
    ResearchAction.Type.ADD_TO_WATCHLIST: (preview_watchlist, execute_watchlist),
    ResearchAction.Type.START_BACKTEST: (preview_backtest, execute_backtest),
}


def action_payload(run, action_type, payload):
    """One preview path for both model proposals and the user's action dialog."""
    if run.status != ResearchRun.Status.COMPLETED:
        raise ValidationError("Complete research before proposing a persistent action.")
    if not isinstance(payload, dict):
        raise ValidationError("Action payload must be an object.")
    if action_type not in ACTION_HANDLERS:
        raise ValidationError("Unsupported research action.")
    preview, _ = ACTION_HANDLERS[action_type]
    return preview(run, payload)


def prepare_proposed_actions(run, result):
    """Validate previews independently; a bad optional action does not discard an answer."""
    proposed = result.get("proposed_actions", [])
    if not isinstance(proposed, list) or len(proposed) > 3:
        proposed = []
        result["limitations"].append("An invalid optional action was omitted; the research answer remains available.")
    from copy import copy

    ready = copy(run)
    ready.status = ResearchRun.Status.COMPLETED
    ready.result = result
    resolved = []
    for item in proposed:
        try:
            if not isinstance(item, dict) or set(item) != {"action_type", "payload"}:
                raise ValueError("Invalid proposed action.")
            resolved.append(
                {
                    "action_type": item["action_type"],
                    "payload": action_payload(ready, item["action_type"], item["payload"]),
                }
            )
        except (APIException, Http404, ValueError, TypeError, KeyError):
            logger.warning("Omitted invalid optional research action run=%s", run.pk)
            result["limitations"].append(
                "An optional action could not be validated. Review its settings before proposing it again."
            )
    result["proposed_actions"] = resolved
    return resolved


@transaction.atomic
def propose_action(run_id, user, action_type, payload):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    run = get_object_or_404(ResearchRun.objects.select_for_update(), pk=run_id, user=user)
    resolved = action_payload(run, action_type, payload)
    # Reopening the same preview does not create another proposed action.
    previous = run.actions.filter(
        action_type=action_type, status=ResearchAction.Status.PROPOSED, payload=resolved
    ).first()
    if previous:
        return previous
    action = ResearchAction.objects.create(run=run, action_type=action_type, payload=resolved)
    run.revision += 1
    run.save(update_fields=["revision", "updated_at"])
    publish_run(run)
    return action


@transaction.atomic
def confirm_action(action_id, user):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    run_id = get_object_or_404(ResearchAction, pk=action_id, run__user=user).run_id
    run = ResearchRun.objects.select_for_update().get(pk=run_id)
    action = ResearchAction.objects.select_for_update().get(pk=action_id)
    if action.status != ResearchAction.Status.PROPOSED:
        return action
    if run.status != ResearchRun.Status.COMPLETED:
        raise ValidationError("Complete research before confirming an action.")
    payload = action.payload
    try:
        with transaction.atomic():
            if action.action_type not in ACTION_HANDLERS:
                raise ValidationError("Unsupported research action.")
            _, execute = ACTION_HANDLERS[action.action_type]
            resources = execute(run, payload)
            action.status, action.resource_ids, action.error_message = ResearchAction.Status.COMPLETED, resources, ""
    except (APIException, ValueError) as exc:
        action.status, action.error_message = ResearchAction.Status.FAILED, str(exc)[:2000]
    except Exception:
        logger.exception("Research action %s failed", action.pk)
        action.status = ResearchAction.Status.FAILED
        action.error_message = (
            "Could not complete the action. No changes were saved. Review the settings and retry with a new preview."
        )
    action.save(update_fields=["status", "resource_ids", "error_message", "updated_at"])
    run.refresh_from_db()
    run.revision += 1
    run.save(update_fields=["revision", "updated_at"])
    publish_run(run)
    logger.info("Research action %s type=%s status=%s", action.pk, action.action_type, action.status)
    return action
