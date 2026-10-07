import asyncio
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from google import genai
from .provider import research_events, ResearchError
from .schemas import ResearchRequest

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    if not os.environ.get("GEMINI_API_KEY") or not os.environ.get("RESEARCH_SERVICE_TOKEN"):
        raise RuntimeError("GEMINI_API_KEY and RESEARCH_SERVICE_TOKEN are required.")
    app.state.slots = asyncio.Semaphore(2)
    app.state.gemini = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    try:
        yield
    finally:
        await app.state.gemini.aio.aclose()
        app.state.gemini.close()


app = FastAPI(title="QuantNest Research Service", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/research")
async def research(payload: ResearchRequest, request: Request, x_research_service_token: str = Header(default="")):
    secret = os.environ.get("RESEARCH_SERVICE_TOKEN", "")
    if not secret or not hmac.compare_digest(secret, x_research_service_token):
        raise HTTPException(403, "Invalid research service credentials.")
    if len(json.dumps(payload.model_dump())) > 200000:
        raise HTTPException(413, "Research context is too large.")

    async def stream():
        queue = asyncio.Queue()
        async def produce():
            try:
                async with asyncio.timeout(570), request.app.state.slots:
                    async for event in research_events(payload, request.app.state.gemini):
                        await queue.put(event)
            except TimeoutError:
                await queue.put({"type": "error", "message": "Research exceeded its deadline. Narrow your request and retry."})
            except ResearchError as exc:
                await queue.put({"type": "error", "message": str(exc)})
            except Exception:
                logger.exception("Research service failed")
                await queue.put({"type": "error", "message": "The research service could not finish. Check the Gemini credentials, quota, and service logs."})
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
    return StreamingResponse(stream(), media_type="application/x-ndjson", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})
