import json
import logging
import time

import httpx
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from notifications.services import NotificationService

from .context import service_payload
from .models import ACTIVE_RUN_STATUSES, ResearchRun
from .services import complete_run, update_active_run
from .tool_registry import execute_tool

logger = logging.getLogger(__name__)


@shared_task(name="research.expire_runs")
def expire_runs():
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(seconds=settings.RESEARCH_TIMEOUT_SECONDS + 60)
    # Queued work can legitimately wait behind a backtest on the compute worker.
    stale = ResearchRun.objects.filter(status=ResearchRun.Status.RUNNING, started_at__lt=cutoff).values_list(
        "pk", flat=True
    )
    for run_id in list(stale[:100]):
        failed = update_active_run(
            run_id,
            status=ResearchRun.Status.FAILED,
            progress_message="Research deadline exceeded",
            error_message="The research worker did not finish within its deadline. Retry the request.",
            completed_at=timezone.now(),
        )
        if failed:
            NotificationService.notify(
                user_id=failed.user_id,
                title="Research interrupted",
                type="WARNING",
                message=failed.error_message,
                data={"module": "research", "research_session_id": failed.session_id},
                dedupe_key=f"research:{failed.pk}:failed",
            )


@shared_task(
    name="research.start_research",
    soft_time_limit=settings.RESEARCH_TIMEOUT_SECONDS + 10,
    time_limit=settings.RESEARCH_TIMEOUT_SECONDS + 30,
)
def start_research(run_id):
    # Duplicate delivery must not issue another paid request. Beat expires interrupted jobs.
    current = ResearchRun.objects.filter(pk=run_id).first()
    if not current or current.status != ResearchRun.Status.PENDING:
        return
    run = update_active_run(
        run_id,
        expected_status=ResearchRun.Status.PENDING,
        status=ResearchRun.Status.RUNNING,
        started_at=timezone.now(),
        progress_message="Preparing research context",
    )
    if not run:
        return
    try:
        if run.mode == "SCREEN":
            evidence = execute_tool(run, "screen_instruments", run.request["screen"])
            result = {
                "answer": f"{evidence['data']['matched']} instruments matched; {len(evidence['data']['excluded'])} were excluded.",
                "evidence_ids": [evidence["evidence_id"]],
                "next_steps": [],
                "limitations": [],
                "draft_evidence_id": None,
            }
            usage = {}
        else:
            if not settings.RESEARCH_SERVICE_TOKEN:
                raise ValueError("Configure the private research service before using the AI assistant.")
            previous_screen = ResearchRun.objects.filter(
                pk=run.request.get("source_run_id"), user_id=run.user_id, status="COMPLETED"
            ).first()
            previous_screen = (
                previous_screen
                or run.session.runs.filter(mode="SCREEN", status=ResearchRun.Status.COMPLETED).order_by("-id").first()
            )
            if run.request.get("refresh"):
                previous_screen = None
            if previous_screen and set(run.request["instrument_ids"]) <= set(previous_screen.request["instrument_ids"]):
                source = next((item for item in previous_screen.evidence if item["tool"] == "screen_instruments"), None)
                if source:
                    run = update_active_run(
                        run_id,
                        evidence=[
                            {
                                **{key: value for key, value in source.items() if key != "cache_key"},
                                "evidence_id": "E1",
                                "source_run_id": source.get("source_run_id", previous_screen.pk),
                                "source_as_of": source.get("source_as_of", previous_screen.as_of.isoformat()),
                            }
                        ],
                    )
                    if not run:
                        return run_id
            if run.request.get("execution_evidence"):
                execute_tool(run, "get_execution_review", {})
                run.refresh_from_db()
            payload = service_payload(run)
            deadline = time.monotonic() + max(0, payload["deadline"] - time.time())
            result, usage = None, {}
            with httpx.Client(timeout=httpx.Timeout(settings.RESEARCH_TIMEOUT_SECONDS, connect=10)) as client:
                with client.stream(
                    "POST",
                    f"{settings.RESEARCH_SERVICE_URL.rstrip('/')}/research",
                    json=payload,
                    headers={"X-Research-Service-Token": settings.RESEARCH_SERVICE_TOKEN},
                ) as response:
                    if response.status_code != 200:
                        response.read()
                        if response.status_code == 422:
                            # Report field errors without exposing the prompt or signed run token.
                            details = "; ".join(
                                f"{'.'.join(map(str, error['loc']))}: {error['msg']}"
                                for error in response.json()["detail"]
                            )
                            raise ValueError(f"Research service rejected its request (HTTP 422): {details}")
                        raise ValueError(
                            f"Research service could not start (HTTP {response.status_code}). Check its configuration."
                        )
                    for line in response.iter_lines():
                        if time.monotonic() > deadline:
                            raise TimeoutError("Research exceeded its ten-minute deadline.")
                        if not ResearchRun.objects.filter(pk=run_id, status__in=ACTIVE_RUN_STATUSES).exists():
                            return run_id
                        if not line:
                            continue
                        event = json.loads(line)
                        if event["type"] == "progress":
                            update_active_run(run_id, progress_message=str(event["message"])[:255])
                        elif event["type"] == "usage":
                            usage = event.get("usage", {})
                            update_active_run(run_id, usage=usage)
                        elif event["type"] == "result":
                            result, usage = event["result"], event.get("usage", {})
                        elif event["type"] == "error":
                            raise ValueError(event["message"])
        completed = complete_run(run_id, result, usage)
        if completed:
            logger.info("Research completed run=%s tools=%s usage=%s", run.pk, completed.tool_attempts, usage)
            NotificationService.notify(
                user_id=run.user_id,
                title="Research complete",
                message=run.session.title,
                data={"module": "research", "research_session_id": run.session_id, "research_run_id": run.pk},
                dedupe_key=f"research:{run.pk}:completed",
            )
    except Exception as exc:
        logger.exception("Research run %s failed", run_id)
        failed = update_active_run(
            run_id,
            status=ResearchRun.Status.FAILED,
            progress_message="Research failed",
            error_message=str(exc)[:2000],
            completed_at=timezone.now(),
        )
        if failed:
            NotificationService.notify(
                user_id=run.user_id,
                title="Research failed",
                message=failed.error_message,
                type="WARNING",
                data={"module": "research", "research_session_id": run.session_id},
                dedupe_key=f"research:{run.pk}:failed",
            )
    return run_id
