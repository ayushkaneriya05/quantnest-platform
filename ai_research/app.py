# app.py
from fastapi import FastAPI , HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from utils import get_db, SNAPSHOT_FRESHNESS_MINUTES, LOG
from snapshot import build_snapshot
# from scheduler import start_scheduler
from contextlib import asynccontextmanager
from scraper import crawl_groww 

@asynccontextmanager
async def lifespan(app: FastAPI):
    LOG.info("Starting app lifespan...")

    # 1) Clear news collection
    db = get_db()
    news_col = db.news_articles
    LOG.info("Clearing old news articles...")
    deleted = news_col.delete_many({})
    LOG.info("Deleted %d old articles", deleted.deleted_count)

    # 2) Run scraper immediately
    try:
        LOG.info("Running initial news scraper...")
        crawl_groww()
        LOG.info("Initial scrape completed")
    except Exception as e:
        LOG.error("Initial scrape failed: %s", e)

    # 3) Start scheduler
    LOG.info("Starting scheduler...")
    # start_scheduler()

    yield
   

app = FastAPI(title="QuantNest AI Research Assistant",lifespan=lifespan)


db = get_db()
snap_col = db.analysis_snapshots
history_col = db.user_research_history

class ResearchRequest(BaseModel):
    ticker: str
    window: Optional[str] = "30d"
    interval: Optional[str] = "1d"
    user_id: Optional[str] = None
    force_recompute: Optional[bool] = False

    class Config:
        schema_extra = {
            "example": {
                "ticker": "RELIANCE",
                "window": "90d",
                "interval": "1d",
                "user_id": "user123",
                "force_recompute": False
            }
        }

def find_fresh_snapshot(ticker: str, window: str, freshness_minutes: int = SNAPSHOT_FRESHNESS_MINUTES):
    doc = snap_col.find_one({"ticker": ticker, "window": window})
    if not doc:
        return None
    asof = doc.get("asof")
    if not isinstance(asof, datetime):
        try:
            asof = datetime.fromisoformat(str(asof).replace("Z", "+00:00"))
        except Exception:
            return None
    return doc if (datetime.now(timezone.utc) - asof) <= timedelta(minutes=freshness_minutes) else None

@app.post("/ai/research")
def ai_research(req: ResearchRequest):
    ticker = req.ticker.upper()
    window = req.window
    interval = req.interval

    if not req.force_recompute:
        snap = find_fresh_snapshot(ticker, window)
    else:
        snap = None
    if not snap:
        snap = build_snapshot(ticker, window=window, interval=interval)
   
    response = {
        "ticker": ticker,
        "asof": snap["asof"],
        "window": window,
        "tech": snap.get("tech"),
        "fundamentals": snap.get("fundamentals"),
        "sentiment": snap.get("sentiment"),
        "summary": snap.get("summary"),
        "recommendation": snap.get("recommendation"),
    }
    # Store user history if provided
    if req.user_id:
        history_col.insert_one({
            "user_id": req.user_id,
            "ticker": ticker,
            "created_at": datetime.now(timezone.utc),
            "request": req.dict(),
            "response": response
        })
    return response

from bson import ObjectId

def serialize_doc(doc):
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    if "asof" in doc and isinstance(doc["asof"], datetime):
        doc["asof"] = doc["asof"].isoformat()
    return doc

@app.get("/ai/history")
def get_history(user_id: str, limit: int = 50):
    docs = list(history_col.find({"user_id": user_id}).sort("created_at", -1).limit(limit))
    docs = [serialize_doc(doc) for doc in docs]
    return {"count": len(docs), "history": docs}


from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    LOG.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/health")
def health():
    try:
        db = get_db()
        # ping Mongo
        db.command("ping")
        return {"status": "ok"}
    except Exception as e:
        LOG.exception("Health check failed")
        raise HTTPException(status_code=503, detail="db unreachable")