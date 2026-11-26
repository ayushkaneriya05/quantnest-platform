import asyncio
import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from .providers import ResearchError, create_provider
from .schemas import ResearchRequest, WebResearchRequest
from .workflow import research_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    if not os.environ.get("RESEARCH_SERVICE_TOKEN"):
        raise RuntimeError("RESEARCH_SERVICE_TOKEN is required.")
    app.state.slots = asyncio.Semaphore(2)
    # Separate slots avoid deadlock when active conversations request web evidence.
    app.state.web_slots = asyncio.Semaphore(2)
    app.state.provider = create_provider()
    try:
        yield
    finally:
        await app.state.provider.close()


app = FastAPI(title="QuantNest Research Service", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/research")
async def research(
    payload: ResearchRequest,
    request: Request,
    x_research_service_token: str = Header(default=""),
):
    secret = os.environ.get("RESEARCH_SERVICE_TOKEN", "")
    if not secret or not hmac.compare_digest(secret, x_research_service_token):
        raise HTTPException(403, "Invalid research service credentials.")
    if len(json.dumps(payload.model_dump()).encode()) > 1000000:
        raise HTTPException(413, "Research context is too large.")

    async def stream():
        queue = asyncio.Queue()

        async def produce():
            started = time.monotonic()
            try:
                remaining = payload.deadline - time.time()
                if remaining <= 0:
                    raise TimeoutError
                async with asyncio.timeout(remaining), request.app.state.slots:
                    logger.info(
                        "Research admitted model=%s wait_ms=%d tools=%d context_chars=%d",
                        request.app.state.provider.model,
                        (time.monotonic() - started) * 1000,
                        len(payload.tools),
                        len(json.dumps(payload.context)),
                    )
                    async for event in research_events(payload, request.app.state.provider):
                        await queue.put(event)
            except TimeoutError:
                await queue.put(
                    {
                        "type": "error",
                        "message": "Research exceeded its deadline. Narrow your request and retry.",
                    }
                )
            except ResearchError as exc:
                await queue.put({"type": "error", "message": str(exc)})
            except Exception as exc:
                logger.error("Research service failed category=%s", type(exc).__name__)
                await queue.put(
                    {
                        "type": "error",
                        "message": "The research service could not finish. Check the provider credentials and service logs.",
                    }
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(produce())
        try:
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    event = {"type": "heartbeat"}
                if event is None:
                    break
                yield json.dumps(event, allow_nan=False) + "\n"
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )


@app.post('/web-research')
async def web_research(payload: WebResearchRequest, request: Request, x_research_service_token: str = Header(default='')):
    secret = os.environ.get('RESEARCH_SERVICE_TOKEN', '')
    if not secret or not hmac.compare_digest(secret, x_research_service_token):
        raise HTTPException(403, 'Invalid research service credentials.')
    if len(json.dumps(payload.model_dump()).encode()) > 1000000:
        raise HTTPException(413, 'Web research request is too large.')
    try:
        async with asyncio.timeout(120), request.app.state.web_slots:
            return await request.app.state.provider.web_research(payload.query, payload.urls)
    except Exception as exc:
        logger.warning('Web research failed category=%s', type(exc).__name__)
        detail = str(exc) if isinstance(exc, ResearchError) else 'The configured provider could not retrieve grounded web evidence.'
        raise HTTPException(502, detail) from exc
