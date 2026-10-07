"""Validate previews and execute only explicit, idempotent confirmations."""
import logging
from types import SimpleNamespace
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError
from backtesting.models import BacktestRun
from backtesting.serializers import BacktestRunSerializer
from backtesting.services import create_backtest, start_backtest, backtest_configuration
from brokers.models import BrokerChargeProfile
from strategies.models import Strategy
from .models import ResearchAction, ResearchRun
from .context import active_stocks, research_instrument_ids
from .validation import json_data, validate_draft
from .services import create_strategy_draft, publish_run

logger = logging.getLogger(__name__)


def action_payload(run, action_type, payload):
    if run.status != ResearchRun.Status.COMPLETED:
        raise ValidationError("Complete research before proposing a persistent action.")
    if not isinstance(payload, dict):
        raise ValidationError("Action payload must be an object.")
    if action_type == ResearchAction.Type.CREATE_DRAFT:
        if set(payload) - {"evidence_id"}:
            raise ValidationError("Choose a validated draft artifact.")
        evidence_id = payload.get("evidence_id") or run.result.get("draft_evidence_id")
        evidence = next((item for item in run.evidence if item["evidence_id"] == evidence_id and item["tool"] == "validate_strategy_draft"), None)
        if not evidence:
            raise ValidationError("The draft must pass backend validation first.")
        return {"draft": validate_draft(evidence["data"]["draft"], research_instrument_ids(run)), "evidence_id": evidence_id}
    if action_type == ResearchAction.Type.ADD_TO_WATCHLIST:
        if set(payload) - {"instrument_ids"}:
            raise ValidationError("Provide selected instrument IDs.")
        ids = payload.get("instrument_ids", [])
        if not isinstance(ids, list) or not ids or len(ids) > 50 or any(type(value) is not int for value in ids) or set(ids) - set(research_instrument_ids(run)):
            raise ValidationError("Select instruments from this research evidence.")
        return {"instrument_ids": list(dict.fromkeys(ids)), "instruments": active_stocks(ids)}
    if action_type != ResearchAction.Type.START_BACKTEST:
        raise ValidationError("Unsupported research action.")
    allowed = {"strategy_id", "source_backtest_id", "name", "start_date", "end_date", "initial_capital", "slippage_pct", "include_charges", "charge_profile"}
    if set(payload) - allowed:
        raise ValidationError("Unsupported backtest settings.")
    settings = dict(payload)
    source_id = settings.pop("source_backtest_id", None)
    strategy_id = settings.pop("strategy_id", None) or run.created_strategy_id or run.request.get("strategy_id")
    if source_id:
        if source_id not in run.request.get("backtest_ids", []):
            raise ValidationError("Attach the backtest before proposing a rerun.")
        source = get_object_or_404(BacktestRun, pk=source_id, user_id=run.user_id, status="COMPLETED")
        strategy_id, snapshot = source.strategy_id, backtest_configuration(source)
        settings = {**{key: getattr(source, key) for key in ("name", "start_date", "end_date", "initial_capital", "slippage_pct", "include_charges")},
                    "charge_profile": source.charge_profile_id, **settings}
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
    serializer = BacktestRunSerializer(data={**settings, "strategy": strategy.pk}, context={"request": SimpleNamespace(user=run.user)})
    serializer.is_valid(raise_exception=True)
    if serializer.validated_data["end_date"] > timezone.localdate():
        raise ValidationError("Backtest end date cannot be in the future.")
    validated = serializer.validated_data
    profile = validated.get("charge_profile")
    return json_data({**{key: validated[key] for key in ("name", "start_date", "end_date", "initial_capital", "slippage_pct", "include_charges")},
                      "strategy": strategy.pk, "snapshot": snapshot, "charge_profile": profile.pk if profile else None,
                      "charge_profile_name": profile.name if profile else None})


@transaction.atomic
def propose_action(run_id, user, action_type, payload):
    run = get_object_or_404(ResearchRun.objects.select_for_update(), pk=run_id, user=user)
    resolved = action_payload(run, action_type, payload)
    # Reopening the same preview does not create another proposed action.
    previous = run.actions.filter(action_type=action_type, status=ResearchAction.Status.PROPOSED, payload=resolved).first()
    if previous:
        return previous
    action = ResearchAction.objects.create(run=run, action_type=action_type, payload=resolved)
    run.revision += 1
    run.save(update_fields=["revision", "updated_at"])
    publish_run(run)
    return action


@transaction.atomic
def confirm_action(action_id, user):
    action = get_object_or_404(ResearchAction.objects.select_for_update().select_related("run"), pk=action_id, run__user=user)
    if action.status != ResearchAction.Status.PROPOSED:
        return action
    run, payload = action.run, action.payload
    try:
        with transaction.atomic():
            if action.action_type == ResearchAction.Type.CREATE_DRAFT:
                strategy = create_strategy_draft(run.pk, user, payload["draft"])
                resources = {"strategy_id": strategy.pk}
            elif action.action_type == ResearchAction.Type.ADD_TO_WATCHLIST:
                from trading.services import TradingWatchlistService
                active_stocks(payload["instrument_ids"])
                watchlist = TradingWatchlistService.get_watchlist(user)
                watchlist.instruments.add(*payload["instrument_ids"])
                resources = {"watchlist_id": watchlist.pk, "instrument_ids": payload["instrument_ids"]}
            else:
                settings = {key: value for key, value in payload.items() if key not in {"snapshot", "charge_profile_name"}}
                get_object_or_404(Strategy, pk=settings["strategy"], user=user)
                serializer = BacktestRunSerializer(data=settings, context={"request": SimpleNamespace(user=user)})
                serializer.is_valid(raise_exception=True)
                backtest = create_backtest(serializer, user, approved_snapshot=payload["snapshot"])
                resources = {"backtest_id": backtest.pk}
                def dispatched(error):
                    if error:
                        ResearchAction.objects.filter(pk=action.pk).update(status=ResearchAction.Status.FAILED, error_message=error)
                        run.refresh_from_db()
                        run.revision += 1
                        run.save(update_fields=["revision", "updated_at"])
                        publish_run(run)
                start_backtest(backtest, on_dispatch=dispatched)
            action.status, action.resource_ids, action.error_message = ResearchAction.Status.COMPLETED, resources, ""
    except (APIException, ValueError) as exc:
        action.status, action.error_message = ResearchAction.Status.FAILED, str(exc)[:2000]
    except Exception:
        logger.exception("Research action %s failed", action.pk)
        action.status = ResearchAction.Status.FAILED
        action.error_message = "Could not complete the action. No changes were saved. Review the settings and retry with a new preview."
    action.save(update_fields=["status", "resource_ids", "error_message", "updated_at"])
    run.refresh_from_db()
    run.revision += 1
    run.save(update_fields=["revision", "updated_at"])
    publish_run(run)
    logger.info("Research action %s type=%s status=%s", action.pk, action.action_type, action.status)
    return action
