# trading_signal_pipeline_15min_multi_stock.py
# Robust 15min swing signals pipeline (XGBoost) with adaptive thresholds and safe class handling

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pymongo import MongoClient
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import SMOTE, RandomOverSampler
import xgboost as xgb
import math
import warnings
warnings.filterwarnings("ignore")

# indicators
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands, AverageTrueRange

# --------------------
# CONFIG / HYPERPARAMS
# --------------------
instruments = ["NSE:INFY-EQ", "NSE:AXISBANK-EQ", "NSE:RELIANCE-EQ"]
mongo_uri = "mongodb://localhost:27017/"
db_name = "quantnest_marketdata"
collection_name = "candles"

resample_rule = "15min"
horizon = 5
threshold = 0.003          # default absolute threshold
use_adaptive_threshold = True
atr_mult = 0.5
use_class_weight = True
use_smote = False
smote_k = 1
prob_threshold = 0.6
trend_filter = True
transaction_cost = 0.0005
slippage = 0.0005
binary_mode = False        # collapse to UP/DOWN if True

xgb_params = dict(
    n_estimators=400,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    gamma=1,
    reg_alpha=0.5,
    reg_lambda=1.0,
    eval_metric='mlogloss',
)

# --------------------
# HELPERS
# --------------------
def engineer_features(df):
    df = df.copy()
    df['return'] = df['close'].pct_change()
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    df['hl_spread'] = df['high'] - df['low']
    df['oc_diff'] = df['close'] - df['open']

    df['rsi_14'] = RSIIndicator(df['close'], window=14).rsi()
    df['rsi_30'] = RSIIndicator(df['close'], window=30).rsi()

    macd = MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    df['ema_20'] = EMAIndicator(df['close'], window=20).ema_indicator()
    df['ema_50'] = EMAIndicator(df['close'], window=50).ema_indicator()
    df['ema_200'] = EMAIndicator(df['close'], window=200).ema_indicator()

    bb = BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_high'] = bb.bollinger_hband()
    df['bb_low'] = bb.bollinger_lband()

    atr = AverageTrueRange(df['high'], df['low'], df['close'], window=14)
    df['atr'] = atr.average_true_range()

    df['roll_vol_20'] = df['return'].rolling(20).std()
    df['roll_vol_60'] = df['return'].rolling(60).std()

    df['vol_ma_20'] = df['volume'].rolling(20).mean()
    df['vol_ma_60'] = df['volume'].rolling(60).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma_20']

    for lag in [1,2,3,5,10]:
        df[f'ret_lag_{lag}'] = df['return'].shift(lag)

    df = df.dropna()
    return df

def create_labels(df, horizon, threshold, adaptive=False, atr_mult=0.5, binary=False):
    df = df.copy()
    if adaptive:
        mean_atr = df['atr'].rolling(50).mean().iloc[-1]
        if np.isnan(mean_atr):
            mean_atr = df['atr'].mean()
        thr = atr_mult * mean_atr
    else:
        thr = threshold

    df['future_return'] = df['close'].shift(-horizon) / df['close'] - 1

    if binary:
        df['signal'] = (df['future_return'] > thr).astype(int)
    else:
        df['signal'] = 0
        df.loc[df['future_return'] > thr, 'signal'] = 1
        df.loc[df['future_return'] < -thr, 'signal'] = -1

    df = df.dropna()
    return df, thr

def compute_metrics_from_equity(eq_series, periods_per_year):
    returns = eq_series.pct_change().fillna(0)
    mu = returns.mean() * periods_per_year
    sigma = returns.std() * math.sqrt(periods_per_year)
    sharpe = mu / sigma if sigma != 0 else np.nan
    cagr = eq_series.iloc[-1]**(periods_per_year/len(eq_series)) - 1
    dd = eq_series / eq_series.cummax() - 1
    maxdd = dd.min()
    return sharpe, cagr, maxdd

def trade_backtest(df, pred_signal_col='pred_signal', cost=0.0005, slip=0.0005):
    df = df.copy()
    df['position'] = df[pred_signal_col].replace(0, np.nan).ffill().fillna(0)
    df['strategy_return'] = df['position'].shift(1) * df['return']
    df['trade'] = df['position'].diff().fillna(0).abs() > 0
    df.loc[df['trade'], 'strategy_return'] -= (cost + slip)
    eq = (1 + df['strategy_return']).cumprod()
    return df, eq

# --------------------
# MAIN LOOP
# --------------------
client = MongoClient(mongo_uri)
db = client[db_name]
collection = db[collection_name]

summary_rows = []

if resample_rule.endswith("min"):
    minutes = int(resample_rule.replace("min",""))
    bars_per_day = int(6.5*60 / minutes)
    periods_per_year = 252 * bars_per_day
else:
    periods_per_year = 252

for inst in instruments:
    print("\n--- Running:", inst)
    raw = pd.DataFrame(list(collection.find({"instrument": inst})))
    if raw.empty:
        print("No data for", inst)
        continue

    raw['timestamp'] = pd.to_datetime(raw['timestamp'])
    raw.set_index('timestamp', inplace=True)
    raw.sort_index(inplace=True)

    ohlc = raw.resample(resample_rule).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()

    if len(ohlc) < 300:
        print("Not enough bars for", inst)
        continue

    df_feat = engineer_features(ohlc)
    df_lab, used_threshold = create_labels(df_feat, horizon, threshold,
                                          adaptive=use_adaptive_threshold,
                                          atr_mult=atr_mult,
                                          binary=binary_mode)
    print("Used threshold:", used_threshold)

    # check for class diversity
    y_raw = df_lab['signal']
    if y_raw.nunique() < 2:
        print(f"Skipping {inst} — only one class present ({y_raw.unique()})")
        continue

    # prepare X, y
    if binary_mode:
        y = y_raw.astype(int)
    else:
        label_mapping = {-1:0, 0:1, 1:2}
        reverse_mapping = {0:-1,1:0,2:1}
        y = y_raw.map(label_mapping)

    X = df_lab.drop(columns=['future_return','signal'])
    non_numeric = X.select_dtypes(include=['object']).columns.tolist()
    X = X.drop(columns=non_numeric)

    split_idx = int(len(X) * 0.7)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    test_df = df_lab.iloc[split_idx:].copy()

    print("Class distribution before resampling:", y_train.value_counts())

    # handle imbalance
    if use_class_weight and not binary_mode:
        class_counts = y_train.value_counts().to_dict()
        total = len(y_train)
        class_weights = {cls: total/count for cls,count in class_counts.items()}
        sample_weight = y_train.map(class_weights)
        X_train_res, y_train_res = X_train, y_train
        sample_weight_used = sample_weight
        resampled = False
        print("Using class weights (no resampling).")
    else:
        try:
            if use_smote:
                sm = SMOTE(random_state=42, k_neighbors=smote_k)
                X_train_res, y_train_res = sm.fit_resample(X_train, y_train)
                sample_weight_used = None
                resampled = True
                print("Resampled with SMOTE")
            else:
                raise ValueError("SMOTE disabled")
        except:
            ros = RandomOverSampler(random_state=42)
            X_train_res, y_train_res = ros.fit_resample(X_train, y_train)
            sample_weight_used = None
            resampled = True
            print("Resampled with RandomOverSampler")

    print("Class distribution after resampling:", pd.Series(y_train_res).value_counts())

    model = xgb.XGBClassifier(**xgb_params)
    if sample_weight_used is not None:
        model.fit(X_train_res, y_train_res, sample_weight=sample_weight_used)
    else:
        model.fit(X_train_res, y_train_res)

    y_proba = model.predict_proba(X_test)
    y_pred = model.predict(X_test)

    if binary_mode:
        pred_signal = y_pred
        max_proba = y_proba.max(axis=1)
        pred_signal = np.where(max_proba >= prob_threshold, pred_signal, 0)
        test_df['pred_signal'] = pred_signal
    else:
        pred_signal_raw = pd.Series(y_pred).map(reverse_mapping).values
        max_proba = y_proba.max(axis=1)
        pred_signal = np.where(max_proba >= prob_threshold, pred_signal_raw, 0)
        test_df['pred_signal'] = pred_signal

    if trend_filter:
        test_df['pred_signal'] = np.where(
            (test_df['close'] > test_df['ema_200']) & (test_df['pred_signal']==1),
            1,
            np.where((test_df['close'] < test_df['ema_200']) & (test_df['pred_signal']==-1), -1, 0)
        )

    bt_df, equity = trade_backtest(test_df, pred_signal_col='pred_signal',
                                   cost=transaction_cost, slip=slippage)

    sharpe, cagr, maxdd = compute_metrics_from_equity(equity, periods_per_year)
    cumret_strategy = equity.iloc[-1]-1
    buy_hold = (1 + test_df['return']).cumprod().iloc[-1]-1

    if not binary_mode:
        y_test_orig = y_test.map({0:-1, 1:0, 2:1})
        y_pred_orig = pd.Series(y_pred).map({0:-1,1:0,2:1})
    else:
        y_test_orig = y_test
        y_pred_orig = pd.Series(y_pred)

    print(classification_report(y_test_orig, y_pred_orig))
    print(f"Sharpe: {sharpe:.2f}, CAGR: {cagr:.2%}, MaxDD: {maxdd:.2%}")
    print(f"Cumulative Return (strategy): {cumret_strategy:.2%}, Buy&Hold: {buy_hold:.2%}")

    summary_rows.append({
        "instrument": inst,
        "n_bars": len(df_lab),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "resampled": resampled if 'resampled' in locals() else False,
        "class_counts_train": y_train.value_counts().to_dict(),
        "sharpe": sharpe,
        "cagr": cagr,
        "maxdd": maxdd,
        "cumret_strategy": cumret_strategy,
        "cumret_buyhold": buy_hold
    })

summary = pd.DataFrame(summary_rows)
print("\n=== Summary ===")
print(summary)
summary.to_csv("strategy_summary.csv", index=False)
