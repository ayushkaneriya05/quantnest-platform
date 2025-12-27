# ai-research-assistant/ai_signal/app/api.py

from fastapi import APIRouter, HTTPException, Query
import pandas as pd
from pydantic import BaseModel
from loguru import logger
from pymongo import MongoClient

from .predict_signal import predict_signal


router = APIRouter()

# --------------------------
# Request Models
# --------------------------
class SignalRequest(BaseModel):
    instrument: str

client = MongoClient("mongodb://localhost:27017")
db = client["quantnest_marketdata"]
collection = db["candles"]

# -----------------------------
# Request/Response Models
# -----------------------------
class SignalResponse(BaseModel):
    stock: str
    signal: str
    confidence: float

# -----------------------------
# Endpoint
# -----------------------------
@router.get("/predict", response_model=SignalResponse)
def get_signal(stock: str = Query(..., description="Stock symbol, e.g., RELIANCE"),):
    """
    Predict real-time Buy/Sell/Hold signal for given stock
    """

    df = pd.DataFrame(list(collection.find({"instrument": f"NSE:{stock}-EQ"}).sort("timestamp", -1).limit(100)))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    df = df.sort_index()

    signal, confidence = predict_signal(f"NSE:{stock}-EQ", df)
    print(f"Signal: {signal}, Confidence: {confidence:.3f}")
