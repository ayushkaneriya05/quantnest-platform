# indicators.py
from datetime import datetime, timedelta, timezone
import pandas as pd
import pandas_ta as ta
from utils import get_db, LOG
from pymongo import ASCENDING

db = get_db()
ohlc_col = db.candles

def fetch_ohlc_df(ticker: str, window_days: int = 60, interval="1m"):
    # datetime cutoff (not just date)
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    
    # query Mongo
    cur = ohlc_col.find(
        {
            "instrument": f"NSE:{ticker}-EQ",
            "resolution": interval,
            "timestamp": {"$gte": since}
        }
    ).sort("timestamp", ASCENDING)
    
    rows = list(cur)
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    
    # Keep only required OHLCV columns
    df = df[["open", "high", "low", "close", "volume"]]
    
    return df


def resample_df(df: pd.DataFrame, to_interval: str = "1d"):
    if df.empty:
        return df
    rule_map = {"1d": "D", "1h":"H", "15m":"15T", "5m":"5T"}
    rule = rule_map.get(to_interval, "D")
    ohlc = df.resample(rule).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()
    return ohlc

def compute_indicators(df: pd.DataFrame):
    if df.empty or len(df) < 20:
        return {"error": "not_enough_data"}

    result = {}
    close = df["close"]

    # RSI 14
    result["rsi14"] = float(ta.rsi(close, length=14).iloc[-1])

    # MACD
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    result["macd"] = {
        "macd": float(macd_df.iloc[-1]["MACD_12_26_9"]),
        "signal": float(macd_df.iloc[-1]["MACDs_12_26_9"]),
        "hist": float(macd_df.iloc[-1]["MACDh_12_26_9"])
    }

    # SMA
    result["sma20"] = float(ta.sma(close, length=20).iloc[-1])
    result["sma50"] = float(ta.sma(close, length=50).iloc[-1]) if len(close) >= 50 else None
    result["sma200"] = float(ta.sma(close, length=200).iloc[-1]) if len(close) >= 200 else None

    # Bollinger Bands
    bb = ta.bbands(close, length=20)
    result["bb"] = {
        "lower": float(bb.iloc[-1]["BBL_20_2.0"]),
        "upper": float(bb.iloc[-1]["BBU_20_2.0"]),
        "mid": float(bb.iloc[-1]["BBM_20_2.0"]),
        "bandwidth": float(bb.iloc[-1]["BBB_20_2.0"]),
        "percent_b": float(bb.iloc[-1]["BBP_20_2.0"])
    }

    # ATR (Average True Range)
    atr = ta.atr(df["high"], df["low"], df["close"], length=14)
    result["atr14"] = float(atr.iloc[-1])

    # Signals heuristics
    signals = []

    # MACD bullish
    if result["macd"]["macd"] > result["macd"]["signal"]:
        signals.append("MACD_BULLISH")
    else:
        signals.append("MACD_BEARISH")

    # Golden Cross
    if result["sma50"] and result["sma200"]:
        if result["sma50"] > result["sma200"]:
            signals.append("GOLDEN_CROSS")
        else:
            signals.append("DEATH_CROSS")

    # RSI
    if result["rsi14"] >= 70:
        signals.append("RSI_OVERBOUGHT")
    elif result["rsi14"] <= 30:
        signals.append("RSI_OVERSOLD")

    # Bollinger Bands
    last_price = close.iloc[-1]
    if last_price >= result["bb"]["upper"]:
        signals.append("PRICE_NEAR_BB_UPPER")
    elif last_price <= result["bb"]["lower"]:
        signals.append("PRICE_NEAR_BB_LOWER")

    # ATR for volatility
    if result["atr14"] > (close.mean() * 0.02):  # heuristic: ATR > 2% of avg price = high volatility
        signals.append("HIGH_VOLATILITY")
    else:
        signals.append("LOW_VOLATILITY")

    result["signals"] = signals
    return result
