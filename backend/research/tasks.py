import json
import logging
import time
import re
import httpx
from celery import shared_task
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from notifications.services import NotificationService
from common.enums_view import get_enum_metadata
from .models import ResearchRun, ResearchAction
from .services import update_active_run, ACTIVE
from .tools import execute_tool

logger = logging.getLogger(__name__)


def normalize_citations(text, evidence, references):
    """Canonicalize written references using the backend evidence, not model bookkeeping."""
    def replace(match):
        group = match.group(1).strip()
        if not re.fullmatch(r"E\d+(?:\s*[,;]\s*E\d+)*", group):
            raise ValueError("Use individual evidence citations such as [E1] and [E2].")
        ids = re.findall(r"E\d+", group)
        missing = set(ids) - evidence.keys()
        if missing:
            raise ValueError(f"Written citations reference evidence unavailable in this run: {', '.join(sorted(missing))}.")
        references.extend(ids)
        return " ".join(f"[{value}]" for value in dict.fromkeys(ids))

    # Ordinary bracketed words, such as [EMA], are not evidence references.
    # Evidence links always open our recorded artifact, never a model-supplied URL.
    return re.sub(r"\[(E\d+\b[^\[\]\n]*)\](?:\([^\)\n]*\))?", replace, text)


def enqueue_research(run_id):
    try:
        start_research.delay(run_id)
    except Exception:
        logger.exception("Could not enqueue research %s", run_id)
        update_active_run(run_id, status=ResearchRun.Status.FAILED, progress_message="Could not queue research",
                          error_message="The research queue is unavailable. Check Redis and the research worker, then retry.",
                          completed_at=timezone.now())


@shared_task(name="research.expire_runs")
def expire_runs():
    from datetime import timedelta
    from django.db.models import Q
    cutoff = timezone.now() - timedelta(minutes=11)
    stale = ResearchRun.objects.filter(
        Q(status=ResearchRun.Status.PENDING, created_at__lt=cutoff) |
        Q(status=ResearchRun.Status.RUNNING, started_at__lt=cutoff)).values_list("pk", flat=True)
    for run_id in list(stale[:100]):
        failed = update_active_run(run_id, status=ResearchRun.Status.FAILED, progress_message="Research deadline exceeded",
                                   error_message="The research worker did not finish within its deadline. Retry the request.", completed_at=timezone.now())
        if failed:
            NotificationService.notify(user_id=failed.user_id, title="Research interrupted", type="WARNING",
                                       message=failed.error_message, data={"module": "research", "research_session_id": failed.session_id},
                                       dedupe_key=f"research:{failed.pk}:failed")


def finalize_result(run, result):
    fields = {"answer", "evidence_ids", "draft_evidence_id", "next_steps", "limitations", "clarification_questions", "artifact_refs", "proposed_actions"}
    if not isinstance(result, dict) or set(result) - fields or not isinstance(result.get("answer"), str) or not result["answer"].strip():
        raise ValueError("The research service returned an invalid result.")
    evidence = {item["evidence_id"]: item for item in run.evidence}
    references = result.get("evidence_ids", [])
    if not isinstance(references, list) or any(not isinstance(value, str) or value not in evidence for value in references):
        raise ValueError("The response cited evidence that was not calculated by this run.")
    references = list(references)
    result["answer"] = normalize_citations(result["answer"], evidence, references)
    for field in ("next_steps", "limitations", "clarification_questions"):
        values = result.get(field, [])
        if not isinstance(values, list) or len(values) > 8 or any(not isinstance(value, str) or len(value) > 2000 for value in values):
            raise ValueError(f"Invalid {field} in research response.")
        result[field] = [normalize_citations(value, evidence, references) for value in values]
    # An omitted declaration must not discard a valid, calculated inline citation.
    result["evidence_ids"] = references = list(dict.fromkeys(references))
    artifacts = result.get("artifact_refs", [])
    if not isinstance(artifacts, list) or any(not isinstance(value, str) or value not in evidence for value in artifacts):
        raise ValueError("An artifact reference was not recorded for this run.")
    result["artifact_refs"] = list(dict.fromkeys(artifacts or references))
    draft_id = result.get("draft_evidence_id")
    if draft_id:
        if not isinstance(draft_id, str):
            raise ValueError("The proposed strategy draft has an invalid evidence reference.")
        item = evidence.get(draft_id)
        if not item or item["tool"] != "validate_strategy_draft":
            raise ValueError("The proposed strategy draft has not passed backend validation.")
        result["draft"] = item["data"]["draft"]
    proposed = result.get("proposed_actions", [])
    if not isinstance(proposed, list) or len(proposed) > 3:
        raise ValueError("Propose at most three actions per reply.")
    from copy import copy
    from .actions import action_payload
    ready = copy(run)
    ready.status = ResearchRun.Status.COMPLETED
    ready.result = result
    resolved = []
    for item in proposed:
        if not isinstance(item, dict) or set(item) != {"action_type", "payload"}:
            raise ValueError("Invalid proposed action.")
        resolved.append({"action_type": item["action_type"], "payload": action_payload(ready, item["action_type"], item["payload"])})
    result["_actions"] = resolved
    return result


@shared_task(name="research.start_research", soft_time_limit=610, time_limit=630)
def start_research(run_id):
    # Duplicate delivery must not issue another paid request. Beat expires interrupted jobs.
    current = ResearchRun.objects.filter(pk=run_id).first()
    if not current or current.status != ResearchRun.Status.PENDING:
        return
    run = update_active_run(run_id, expected_status=ResearchRun.Status.PENDING, status=ResearchRun.Status.RUNNING,
                            started_at=timezone.now(), progress_message="Preparing research context")
    if not run:
        return
    try:
        if run.mode == "SCREEN":
            evidence = execute_tool(run, "screen_instruments", run.request["screen"])
            result = {"answer": f"{evidence['data']['matched']} instruments matched; {len(evidence['data']['excluded'])} were excluded.",
                      "evidence_ids": [evidence["evidence_id"]], "next_steps": [], "limitations": [], "draft_evidence_id": None}
            usage = {}
        else:
            if not settings.RESEARCH_SERVICE_TOKEN:
                raise ValueError("Configure the private research service before using the AI assistant.")
            previous_screen = ResearchRun.objects.filter(pk=run.request.get("source_run_id"), user_id=run.user_id, status="COMPLETED").first()
            previous_screen = previous_screen or run.session.runs.filter(mode="SCREEN", status=ResearchRun.Status.COMPLETED).order_by("-id").first()
            if run.request.get("refresh"):
                previous_screen = None
            if previous_screen and set(run.request["instrument_ids"]) <= set(previous_screen.request["instrument_ids"]):
                source = next((item for item in previous_screen.evidence if item["tool"] == "screen_instruments"), None)
                if source:
                    run = update_active_run(run_id, evidence=[{**{key: value for key, value in source.items() if key != "cache_key"}, "evidence_id": "E1", "source_run_id": source.get("source_run_id", previous_screen.pk),
                                                             "source_as_of": source.get("source_as_of", previous_screen.as_of.isoformat())}])
                    if not run:
                        return
            if run.request.get("execution_evidence"):
                execute_tool(run, "get_execution_review", {})
                run.refresh_from_db()
            token = signing.dumps({"run_id": run.pk, "user_id": run.user_id}, salt="research-run")
            history = list(run.session.runs.filter(status=ResearchRun.Status.COMPLETED).exclude(pk=run.pk).order_by("-id")[:6])
            payload = {"prompt": run.prompt, "run_token": token, "as_of": run.as_of.isoformat(),
                       "context": {**{key: value for key, value in run.request.items() if key not in {"strategy_snapshot", "backtests", "execution_evidence"}},
                                   "backtests": [{"id": item["id"], "name": item["name"]} for item in run.request.get("backtests", [])],
                                   "has_strategy_snapshot": bool(run.request.get("strategy_snapshot")),
                                   "recorded_evidence": run.evidence, "tool_budget": 8 - run.tool_attempts},
                       "builder_schema": get_enum_metadata(),
                       "history": [{"run_id": item.pk, "prompt": item.prompt or "Market screen", "answer": item.result.get("answer", ""),
                                    "as_of": item.as_of.isoformat(), "draft_evidence_id": item.result.get("draft_evidence_id"),
                                    "evidence": [{"evidence_id": value["evidence_id"], "tool": value["tool"],
                                                  "source_run_id": value.get("source_run_id", item.pk)} for value in item.evidence]}
                                   for item in reversed(history)]}
            deadline = time.monotonic() + 600
            result, usage = None, {}
            with httpx.Client(timeout=httpx.Timeout(600, connect=10)) as client:
                with client.stream("POST", f"{settings.RESEARCH_SERVICE_URL.rstrip('/')}/research", json=payload,
                                   headers={"X-Research-Service-Token": settings.RESEARCH_SERVICE_TOKEN}) as response:
                    if response.status_code != 200:
                        response.read()
                        raise ValueError(f"Research service could not start (HTTP {response.status_code}). Check its configuration.")
                    for line in response.iter_lines():
                        if time.monotonic() > deadline:
                            raise TimeoutError("Research exceeded its ten-minute deadline.")
                        if not ResearchRun.objects.filter(pk=run_id, status__in=ACTIVE).exists():
                            return
                        if not line:
                            continue
                        event = json.loads(line)
                        if event["type"] == "progress":
                            update_active_run(run_id, progress_message=str(event["message"])[:255])
                        elif event["type"] == "result":
                            result, usage = event["result"], event.get("usage", {})
                        elif event["type"] == "error":
                            raise ValueError(event["message"])
            run.refresh_from_db()
            result = finalize_result(run, result)
        proposed = result.pop("_actions", [])
        with transaction.atomic():
            completed = update_active_run(run_id, status=ResearchRun.Status.COMPLETED, progress_message="Research complete",
                                          result=result, usage=usage, completed_at=timezone.now())
            if completed:
                ResearchAction.objects.bulk_create([ResearchAction(run=completed, **item) for item in proposed])
        if completed:
            logger.info("Research completed run=%s tools=%s usage=%s", run.pk, completed.tool_attempts, usage)
            NotificationService.notify(user_id=run.user_id, title="Research complete", message=run.session.title,
                                       data={"module": "research", "research_session_id": run.session_id, "research_run_id": run.pk},
                                       dedupe_key=f"research:{run.pk}:completed")
    except Exception as exc:
        logger.exception("Research run %s failed", run_id)
        failed = update_active_run(run_id, status=ResearchRun.Status.FAILED, progress_message="Research failed",
                                   error_message=str(exc)[:2000], completed_at=timezone.now())
        if failed:
            NotificationService.notify(user_id=run.user_id, title="Research failed", message=failed.error_message,
                                       type="WARNING", data={"module": "research", "research_session_id": run.session_id},
                                       dedupe_key=f"research:{run.pk}:failed")
