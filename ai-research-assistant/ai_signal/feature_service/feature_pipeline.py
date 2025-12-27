# ai-research-assistant/ai_signal/app/feature_pipeline.py
import json
from pathlib import Path
import pandas as pd
import numpy as np
from pymongo import MongoClient
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.trend import EMAIndicator, SMAIndicator, MACD, CCIIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
from loguru import logger

# === Config ===
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "quantnest_marketdata"
BATCH_SIZE = 5000

# === MongoDB ===
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# === Helper: candlestick patterns ===
def detect_candle_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add simple candlestick pattern encodings.
    1 = bullish, -1 = bearish, 0 = neutral
    """
    df["candle_body"] = df["close"] - df["open"]
    df["candle_range"] = df["high"] - df["low"]

    # Hammer: small body, long lower shadow
    df["hammer"] = (
        (df["candle_body"].abs() < 0.3 * df["candle_range"]) &
        ((df["open"] - df["low"]).abs() > 2 * df["candle_body"].abs())
    ).astype(int)

    # Engulfing: bullish/bearish reversal
    df["bullish_engulfing"] = (
        (df["candle_body"] > 0) &
        (df["candle_body"].shift(1) < 0) &
        (df["close"] > df["open"].shift(1)) &
        (df["open"] < df["close"].shift(1))
    ).astype(int)

    df["bearish_engulfing"] = (
        (df["candle_body"] < 0) &
        (df["candle_body"].shift(1) > 0) &
        (df["open"] > df["close"].shift(1)) &
        (df["close"] < df["open"].shift(1))
    ).astype(int)

    return df

# === Helper: resample ===
def resample_to_15m(df: pd.DataFrame) -> pd.DataFrame:
    df = df.resample("15min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()
    return df

# === Compute Features ===
def compute_features(df: pd.DataFrame, benchmark: pd.Series = None) -> pd.DataFrame:
    df["return"] = df["close"].pct_change()

    # Moving averages
    df["sma_5"] = SMAIndicator(df["close"], 5).sma_indicator()
    df["ema_10"] = EMAIndicator(df["close"], 10).ema_indicator()

    # RSI
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()

    # MACD
    macd = MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"] = macd.macd_diff()

    # Stochastic Oscillator
    stoch = StochasticOscillator(df["high"], df["low"], df["close"], window=14, smooth_window=3)
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()

    # OBV
    df["obv"] = OnBalanceVolumeIndicator(df["close"], df["volume"]).on_balance_volume()

    # ADX
    adx = ADXIndicator(df["high"], df["low"], df["close"], window=14)
    df["adx"] = adx.adx()

    # CCI
    df["cci"] = CCIIndicator(df["high"], df["low"], df["close"], window=20).cci()

    # Williams %R
    df["williams_r"] = WilliamsRIndicator(df["high"], df["low"], df["close"], lbp=14).williams_r()

    # Bollinger Bands
    bb = BollingerBands(df["close"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_percent"] = bb.bollinger_pband()

    # ATR (volatility scaling)
    df["atr"] = AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()

    # Rolling volatility
    df["volatility"] = df["return"].rolling(20).std()

    # Lagged returns
    df["lag_return_1"] = df["return"].shift(1)
    df["lag_return_2"] = df["return"].shift(2)
    df["lag_return_3"] = df["return"].shift(3)

    # Volume ratios
    df["vol_ratio_5"] = df["volume"] / df["volume"].rolling(5).mean()
    df["vol_ratio_20"] = df["volume"] / df["volume"].rolling(20).mean()
    df["vol_spike"] = (df["vol_ratio_5"] > 2).astype(int)

    # Candle patterns
    df = detect_candle_patterns(df)

    # Rolling correlation with benchmark (e.g., NIFTY index returns)
    if benchmark is not None:
        df["benchmark_corr"] = (
            df["return"].rolling(20).corr(benchmark.pct_change())
        )

    return df

# === Store ===
def process_and_store(df: pd.DataFrame, instrument: str):
    feature_docs = []
    for ts, row in df.iterrows():
        if pd.isna(row).any():
            continue
        doc = {"instrument": instrument, "timestamp": ts.to_pydatetime()}
        for col in df.columns:
            doc[col] = float(row[col]) if not isinstance(row[col], (int, np.integer)) else int(row[col])
        feature_docs.append(doc)

    if feature_docs:
        db.feature_snapshot.insert_many(feature_docs)
        logger.info(f"Inserted {len(feature_docs)} 15m features for {instrument}")

# === Pipeline Runner ===
def run_pipeline(instrument="NSE:ABB-EQ", benchmark_symbol="NSE:NIFTY-EQ"):
    query = {"instrument": instrument, "resolution": "1m"}
    logger.info(f"Fetching 1m candles for {instrument}")
    cursor = db.candles.find(query).sort("timestamp", 1)

    batch = []
    benchmark_series = None
    if benchmark_symbol:
        bq = {"instrument": benchmark_symbol, "resolution": "1m"}
        bdf = pd.DataFrame(list(db.candles.find(bq)))
        if not bdf.empty:
            bdf["timestamp"] = pd.to_datetime(bdf["timestamp"])
            bdf.set_index("timestamp", inplace=True)
            benchmark_series = resample_to_15m(bdf)["close"]

    df = pd.DataFrame(cursor)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    df = resample_to_15m(df)
    df = compute_features(df, benchmark_series)
    process_and_store(df, instrument)

    logger.success(f"✅ Finished feature pipeline for {instrument} (15m bars)")

# === Batch runner for NIFTY100 ===
BASE_DIR = Path(__file__).resolve().parent.parent
nifty100_path = BASE_DIR / "data" / "nifty100_symbols.json"
nifty100_data = json.loads(nifty100_path.read_text())

if __name__ == "__main__":
    for t in nifty100_data:
        symbol = t["symbol"]
        instrument = f"NSE:{symbol}-EQ"
        run_pipeline(instrument)
