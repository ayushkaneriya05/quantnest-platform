import json
from pathlib import Path
import pandas as pd
import numpy as np
from pymongo import MongoClient
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator, ROCIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, f1_score, precision_recall_curve
import xgboost as xgb
import joblib
from loguru import logger
from sklearn.preprocessing import StandardScaler


import tensorflow as tf
from tensorflow.keras import Sequential, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.utils.class_weight import compute_class_weight

# -------------------------
# Config
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "quantnest_marketdata"
COLLECTION_NAME = "candles"
RESAMPLE_RULE = "15min"   # resample 1-min → 15-min
SEQ_LEN = 30              # sequence length for LSTM

client = MongoClient(MONGO_URI)
col = client[DB_NAME][COLLECTION_NAME]

# -------------------------
# Feature Engineering
# -------------------------
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # Price-based
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["high_low_ratio"] = df["high"] / df["low"]
    df["close_open_ratio"] = df["close"] / df["open"]

    # Trend
    for win in [5, 10, 20, 50]:
        df[f"sma_{win}"] = SMAIndicator(df["close"], win).sma_indicator()
    df["ema_20"] = EMAIndicator(df["close"], 20).ema_indicator()
    macd = MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_diff"] = macd.macd_diff()

    # Momentum
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()
    stoch = StochasticOscillator(df["high"], df["low"], df["close"], 14, 3)
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()
    df["williams_r"] = WilliamsRIndicator(df["high"], df["low"], df["close"], lbp=14).williams_r()
    df["roc"] = ROCIndicator(df["close"], 12).roc()

    # Volatility
    bb = BollingerBands(df["close"], 20, 2)
    df["bb_percent"] = bb.bollinger_pband()
    df["bb_width"] = bb.bollinger_wband()
    df["atr"] = AverageTrueRange(df["high"], df["low"], df["close"], 14).average_true_range()
    df["volatility_20"] = df["log_return"].rolling(20).std()

    # Volume
    df["obv"] = OnBalanceVolumeIndicator(df["close"], df["volume"]).on_balance_volume()
    df["cmf"] = ChaikinMoneyFlowIndicator(df["high"], df["low"], df["close"], df["volume"], 20).chaikin_money_flow()
    df["vol_sma20"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_sma20"]

    # Candlestick
    df["candle_body"] = df["close"] - df["open"]
    df["candle_range"] = df["high"] - df["low"]
    df["upper_wick"] = df["high"] - df[["close", "open"]].max(axis=1)
    df["lower_wick"] = df[["close", "open"]].min(axis=1) - df["low"]

    return df.dropna()

# -------------------------
# LSTM Preparation
# -------------------------
def create_sequences(df, seq_len=SEQ_LEN):
    df = df.copy()

    # Add TA features (sequential)
    df["rsi"] = RSIIndicator(df["close"], window=14).rsi()
    macd = MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["atr"] = AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()

    df = df.dropna().reset_index(drop=True)

    # Select sequence features
    seq_features = ["open", "high", "low", "close", "volume", "rsi", "macd", "macd_signal", "atr"]
    X = df[seq_features].values
    y = df["target"].values

    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Create sequences
    X_seq, y_seq = [], []
    for i in range(len(X_scaled) - seq_len):
        X_seq.append(X_scaled[i:i+seq_len])
        y_seq.append(y[i+seq_len])

    X_seq = np.array(X_seq)  # (samples, seq_len, features)
    y_seq = np.array(y_seq)

    return X_seq, y_seq, scaler


def build_lstm_model(input_shape):
    model = Sequential([
        Input(shape=input_shape),   # <-- define input properly
        LSTM(64, return_sequences=True),
        Dropout(0.3),
        LSTM(32),
        Dropout(0.3),
        Dense(1, activation="sigmoid")
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model

# -------------------------
# Training Hybrid Model
# -------------------------
def train_per_stock(instrument: str):
    logger.info(f"Training hybrid model for {instrument}")

    # Load 1-min data
    cursor = col.find({"instrument": instrument, "resolution": "1m"})
    df = pd.DataFrame(list(cursor))

    if df.empty:
        logger.warning(f"No data for {instrument}")
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    df = df.sort_index()

    # Resample
    df_resampled = df.resample(RESAMPLE_RULE).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()

    # Features
    df_feat = add_features(df_resampled)

    # Target
    df_feat["future_return"] = df_feat["close"].shift(-1) / df_feat["close"] - 1
    df_feat["target"] = (df_feat["future_return"] > 0).astype(int)
    df_feat = df_feat.dropna()

    # -----------------
    # XGBoost
    # -----------------
    X = df_feat.drop(columns=["target", "future_return"])
    y = df_feat["target"]

    tscv = TimeSeriesSplit(n_splits=3)
    best_model, best_f1 = None, -1
    xgb_oof_preds = np.zeros(len(X))

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            tree_method="hist"
        )
        model.fit(X_train, y_train)

        y_prob = model.predict_proba(X_test)[:, 1]
        precision, recall, thresholds = precision_recall_curve(y_test, y_prob)
        f1_scores = 2 * (precision * recall) / (precision + recall + 1e-9)
        best_idx = np.argmax(f1_scores)
        best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5
        y_pred = (y_prob >= best_threshold).astype(int)
        f1 = f1_score(y_test, y_pred)
        xgb_oof_preds[test_idx] = y_prob
        logger.info(classification_report(y_test, y_pred))
        logger.info(f"{instrument} Fold {fold}: XGB F1={f1:.4f}")

        if f1 > best_f1:
            best_f1, best_model = f1, model

    # Save best XGBoost
    joblib.dump(best_model, f"{BASE_DIR}/models/{instrument.replace(':','_')}_xgb.pkl")

    # -----------------
    # LSTM
    # -----------------
    X_seq, y_seq,scaler  = create_sequences(df_feat, SEQ_LEN)
    split = int(0.8 * len(X_seq))
    X_train, X_test = X_seq[:split], X_seq[split:]
    y_train, y_test = y_seq[:split], y_seq[split:]

    # Balance classes
    class_weights = compute_class_weight(
        class_weight="balanced",
        classes=np.unique(y_train),
        y=y_train
    )
    class_weights = dict(enumerate(class_weights))
    callbacks = [
        EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5)
    ]
    lstm_model = build_lstm_model((SEQ_LEN, 5))
    lstm_model.fit(
        X_train, y_train,
        epochs=100,
        batch_size=64,
        callbacks=callbacks,
        validation_split=0.1,
        class_weight=class_weights,
        verbose=1
    )

    lstm_preds = lstm_model.predict(X_test).flatten()
    lstm_model.save(f"{BASE_DIR}/models/{instrument.replace(':','_')}_lstm.keras")  # ✅ modern format

    # -----------------
    # Stacking Ensemble
    # -----------------
    min_len = min(len(xgb_oof_preds), len(lstm_preds))
    ensemble_X = np.vstack([xgb_oof_preds[-min_len:], lstm_preds[-min_len:]]).T
    ensemble_y = y.iloc[-min_len:]

    meta_model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        random_state=42
    )
    meta_model.fit(ensemble_X, ensemble_y)

    joblib.dump(meta_model, f"{BASE_DIR}/models/{instrument.replace(':','_')}_ensemble.pkl")
    logger.success(f"✅ Saved hybrid ensemble model for {instrument}")

# -------------------------
# Main Loop
# -------------------------
nifty100_path = BASE_DIR / "data" / "nifty100_symbols.json"
nifty100_data = json.loads(nifty100_path.read_text())

if __name__ == "__main__":
    for stock in nifty100_data:
        train_per_stock(f"NSE:{stock['symbol']}-EQ")
