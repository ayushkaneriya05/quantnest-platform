# predict_signal.py
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import os
from tensorflow.keras.models import load_model
from trainer import add_features  # reuse your TA feature function

# -----------------------------
# Config
# -----------------------------
SEQ_LEN = 30
BUY_THRESHOLD = 0.6
SELL_THRESHOLD = 0.4
BASE_DIR = Path(__file__).resolve().parent.parent
# -----------------------------
# Load Models
# -----------------------------
def load_models(stock_symbol: str):
    """
    Load XGBoost, LSTM (.keras), and Ensemble models for a specific stock.
    """
    stock_id = stock_symbol.replace(":", "_")  # e.g., NSE:ABB-EQ -> NSE_ABB_EQ

    try:
        xgb_model = joblib.load(f"{BASE_DIR}/models/{stock_id}_xgb.pkl")

        # Handle keras model (.keras or .h5)
        keras_path = f"{BASE_DIR}/models/{stock_id}_lstm.keras"
        h5_path = f"{BASE_DIR}/models/{stock_id}_lstm.h5"
        if os.path.exists(keras_path):
            lstm_model = load_model(keras_path)
        elif os.path.exists(h5_path):
            lstm_model = load_model(h5_path)
        else:
            raise FileNotFoundError(f"No LSTM model found for {stock_symbol}")

        ensemble_model = joblib.load(f"{BASE_DIR}/models/{stock_id}_ensemble.pkl")

    except Exception as e:
        raise FileNotFoundError(f"❌ Model files missing for {stock_symbol}: {e}")

    return xgb_model, lstm_model, ensemble_model

# -----------------------------
# Feature Preparation
# -----------------------------
def prepare_features(df: pd.DataFrame, seq_len: int = SEQ_LEN):
    """
    Create features for XGBoost and LSTM from the input OHLCV dataframe.
    """
    df = add_features(df.copy())

    # --- XGBoost features (last row TA indicators) ---
    xgb_features = (
        df.drop(columns=["target", "future_return"], errors="ignore")
        .iloc[-1]
        .values.reshape(1, -1)
    )

    # --- LSTM sequence (OHLCV only) ---
    if len(df) < seq_len:
        raise ValueError(f"❌ Not enough data: need at least {seq_len} rows, got {len(df)}")

    X_seq = df[["open", "high", "low", "close", "volume"]].iloc[-seq_len:].values
    X_seq = np.expand_dims(X_seq, axis=0)  # shape -> (1, seq_len, 5)

    return xgb_features, X_seq

# -----------------------------
# Predict Signal
# -----------------------------
def predict_signal(stock_symbol: str, df: pd.DataFrame):
    """
    Run inference pipeline for a stock:
    - XGBoost -> Prob
    - LSTM -> Prob
    - Ensemble (stacking) -> Final Prob
    """
    # Load models
    xgb_model, lstm_model, ensemble_model = load_models(stock_symbol)

    # Prepare features
    xgb_features, lstm_input = prepare_features(df)

    # --- XGB prediction (probability of Buy) ---
    xgb_prob = float(xgb_model.predict_proba(xgb_features)[0, 1])

    # --- LSTM prediction (probability of Buy) ---
    lstm_prob = float(lstm_model.predict(lstm_input)[0, 0])

    # --- Ensemble (combining both) ---
    ensemble_input = np.array([[xgb_prob, lstm_prob]])
    final_prob = float(ensemble_model.predict_proba(ensemble_input)[0, 1])

    # --- Trading decision ---
    if final_prob > BUY_THRESHOLD:
        return {"signal": "BUY", "probability": final_prob, "xgb": xgb_prob, "lstm": lstm_prob}
    elif final_prob < SELL_THRESHOLD:
        return {"signal": "SELL", "probability": final_prob, "xgb": xgb_prob, "lstm": lstm_prob}
    else:
        return {"signal": "HOLD", "probability": final_prob, "xgb": xgb_prob, "lstm": lstm_prob}
