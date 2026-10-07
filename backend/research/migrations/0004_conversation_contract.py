"""Convert saved attachments and artifact provenance once, preserving research history."""
from django.db import migrations
from copy import deepcopy


def saved_backtest_configuration(run):
    snapshot = run.strategy_version.config_snapshot if run.strategy_version_id else run.config_snapshot
    config = deepcopy(snapshot or {})
    def merge(base, updates):
        for key, value in (updates or {}).items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                merge(base[key], value)
            else:
                base[key] = deepcopy(value)
    merge(config, run.parameters)
    return config


def convert_history(apps, schema_editor):
    Run = apps.get_model("research", "ResearchRun")
    Session = apps.get_model("research", "ResearchSession")
    Action = apps.get_model("research", "ResearchAction")
    Backtest = apps.get_model("backtesting", "BacktestRun")
    context_keys = {"strategy_id", "instrument_ids", "instruments", "backtest_ids", "timeframe", "screen"}
    for session in Session.objects.iterator():
        latest, draft_context = None, None
        for run in Run.objects.filter(session_id=session.pk).order_by("created_at", "id").iterator():
            context = dict(run.request)
            old_id = context.pop("backtest_id", None)
            context["backtest_ids"] = [old_id] if old_id else context.get("backtest_ids", [])
            context["backtests"] = [{"id": item.pk, "name": item.name, "snapshot": saved_backtest_configuration(item)}
                                    for item in Backtest.objects.filter(pk__in=context["backtest_ids"], user_id=run.user_id)]
            context.setdefault("timeframe", context.get("screen", {}).get("timeframe") or
                (context.get("strategy_snapshot") or {}).get("time_rule", {}).get("candle_timeframe") or "1D")
            evidence = [{**item, "source_run_id": item.get("source_run_id", run.pk),
                         "source_as_of": item.get("source_as_of", run.as_of.isoformat())} for item in run.evidence]
            result = {**run.result, "artifact_refs": run.result.get("evidence_ids", []),
                      "clarification_questions": [], "proposed_actions": []} if run.result else {}
            if draft_context:
                context["draft_context"] = draft_context
            Run.objects.filter(pk=run.pk).update(request=context, evidence=evidence, result=result, tool_attempts=len(evidence))
            if run.created_strategy_id:
                Action.objects.create(run_id=run.pk, action_type="CREATE_DRAFT", status="COMPLETED",
                    payload={"draft": result.get("draft", {})}, resource_ids={"strategy_id": run.created_strategy_id})
            latest = context
            if run.status == "COMPLETED" and result.get("draft"):
                draft_context = {"run_id": run.pk, "evidence_id": result.get("draft_evidence_id"), "draft": result["draft"]}
        if latest:
            kind = "CHAT" if Run.objects.filter(session_id=session.pk).exclude(mode="SCREEN").exists() else "SCREEN"
            Session.objects.filter(pk=session.pk).update(context={key: value for key, value in latest.items() if key in context_keys}, kind=kind)


class Migration(migrations.Migration):
    dependencies = [("research", "0003_researchrun_revision_researchrun_tool_attempts_and_more"),
                    ("backtesting", "0018_backtestrun_diagnostics")]
    operations = [migrations.RunPython(convert_history, migrations.RunPython.noop)]
