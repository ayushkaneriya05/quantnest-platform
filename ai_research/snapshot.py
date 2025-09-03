# snapshot.py
from datetime import datetime, timezone, timedelta

import pandas as pd
from utils import get_db, LOG
from indicators import fetch_ohlc_df, resample_df, compute_indicators
from sentiment import analyze_text_sentiment, summarize_text
import yfinance as yf

db = get_db()
snap_col = db.analysis_snapshots
news_col = db.news_articles
fund_col = db.fundamentals 

CACHE_EXPIRY_HOURS = 12  # refresh fundamentals every 12 hours


def fetch_fundamentals(ticker: str):
    try:
        # ---- Check cache ----
        cached = fund_col.find_one({"ticker": ticker})
        if cached and (datetime.now(timezone.utc) - cached["fetched_at"]) < timedelta(hours=CACHE_EXPIRY_HOURS):
            return cached["data"]

        t = yf.Ticker(ticker)

        # --- Fast Info (quick metadata) ---
        fast_info = t.fast_info

        # --- Financial Statements ---
        financials = t.financials
        balance = t.balance_sheet
        cashflow = t.cashflow

        # Extract safe values
        data = {
            "ticker": ticker,
            "marketCap": getattr(fast_info, "market_cap", None),
            "previousClose": getattr(fast_info, "previous_close", None),
            "sector": t.info.get("sector"),  # still fallback here
            "industry": t.info.get("industry"),

            # Profitability
            "trailingPE": t.info.get("trailingPE"),
            "forwardPE": t.info.get("forwardPE"),
            "trailingEPS": t.info.get("trailingEps"),
            "ebitda": t.info.get("ebitda"),

            # Balance Sheet
            "totalDebt": safe_extract(balance, "Total Debt"),
            "debtToEquity": t.info.get("debtToEquity"),

            # Cash Flow
            "operatingCashflow": safe_extract(cashflow, "Total Cash From Operating Activities"),

            # Company Summary
            "longBusinessSummary": t.info.get("longBusinessSummary"),
        }

        # ---- Persist in Mongo ----
        fund_col.replace_one(
            {"ticker": ticker},
            {"ticker": ticker, "data": data, "fetched_at": datetime.now(timezone.utc)},
            upsert=True
        )
        return data

    except Exception as e:
        LOG.exception("Error fetching fundamentals for %s: %s", ticker, e)
        return {}


def safe_extract(df: pd.DataFrame, field: str):
    """Extract latest available field safely from Yahoo dataframe"""
    try:
        return df.loc[field].iloc[0] if field in df.index else None
    except Exception:
        return None

def analyze_sentiment_window(ticker, window_days=30):
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    cur = news_col.find({"ticker.symbol": ticker, "ts": {"$gte": since}}).sort("ts", -1)
    docs = list(cur)

    if not docs:  # fallback: broader search
        cur = news_col.find({"ts": {"$gte": since}}).sort("ts", -1)
        docs = list(cur)

    pos = neg = neu = 0
    themes = {}
    summaries = []

    for d in docs:
        text = " ".join([d.get("title") or "", d.get("description") or ""]).strip()
        if not text:
            continue

        s = analyze_text_sentiment(text)  # huggingface pipeline
        lbl = s["label"]
        if lbl == "Positive":
            pos += 1
        elif lbl == "Negative":
            neg += 1
        else:
            neu += 1

        # Heuristic theme extraction
        lower = text.lower()
        for theme, keys in {
            "earnings": ["earnings", "profit", "revenue", "q1", "q2", "q3", "q4"],
            "merger": ["acquisition", "merger", "buyout"],
            "regulatory": ["regulator", "probe", "fine", "investigation", "penalty"],
            "product": ["launch", "product", "platform", "service"]
        }.items():
            if any(key in lower for key in keys):
                themes[theme] = themes.get(theme, 0) + 1

        # Summarize top few
        if len(summaries) < 5:
            try:
                summary = summarize_text(text, max_length=100)
                summaries.append({
                    "title": d.get("title"),
                    "summary": summary,
                    "url": d.get("url")
                })
            except Exception:
                pass

    total = max(1, pos + neg + neu)
    sentiment = {"pos": pos/total, "neg": neg/total, "neu": neu/total, "count": total}
    top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "sentiment": sentiment,
        "themes": [t for t, _ in top_themes],
        "summaries": summaries
    }

def make_recommendation(tech, sent, fundamentals):
    score = 0.0
    reasons = []

    # ---------------- Sentiment Weight ----------------
    pos = sent.get("sentiment", {}).get("pos", 0.0)
    neg = sent.get("sentiment", {}).get("neg", 0.0)
    sent_score = pos - neg
    score += 0.3 * sent_score
    if sent_score > 0: 
        reasons.append("Positive news sentiment")
    elif sent_score < 0: 
        reasons.append("Negative news sentiment")

    # ---------------- Technical Weight ----------------
    signals = tech.get("signals", [])

    if "MACD_BULLISH" in signals:
        score += 0.15; reasons.append("MACD bullish crossover")
    if "MACD_BEARISH" in signals:
        score -= 0.15; reasons.append("MACD bearish crossover")

    if "GOLDEN_CROSS" in signals:
        score += 0.15; reasons.append("Golden Cross (SMA50>SMA200)")
    if "DEATH_CROSS" in signals:
        score -= 0.15; reasons.append("Death Cross (SMA50<SMA200)")

    if "RSI_OVERBOUGHT" in signals:
        score -= 0.1; reasons.append("RSI overbought")
    if "RSI_OVERSOLD" in signals:
        score += 0.1; reasons.append("RSI oversold")

    if "PRICE_NEAR_BB_UPPER" in signals:
        score -= 0.05; reasons.append("Price near Bollinger upper band")
    if "PRICE_NEAR_BB_LOWER" in signals:
        score += 0.05; reasons.append("Price near Bollinger lower band")

    if "HIGH_VOLATILITY" in signals:
        reasons.append("High volatility (ATR high)")
    elif "LOW_VOLATILITY" in signals:
        reasons.append("Stable / low volatility")

    # ---------------- Fundamentals Weight ----------------
    pe = fundamentals.get("trailingPE") or fundamentals.get("forwardPE") or None
    if pe:
        try:
            pe_val = float(pe)
            if pe_val < 15:
                score += 0.1; reasons.append(f"Attractive P/E ratio ({pe_val:.1f})")
            elif pe_val > 40:
                score -= 0.1; reasons.append(f"Expensive P/E ratio ({pe_val:.1f})")
        except Exception:
            pass
     # Debt-to-Equity
    dte = fundamentals.get("debtToEquity")
    if dte:
        try:
            dte_val = float(dte)
            if dte_val < 1:
                score += 0.05
                reasons.append("Low debt-to-equity")
            elif dte_val > 2:
                score -= 0.05
                reasons.append("High debt-to-equity")
        except Exception:
            pass

    # EBITDA
    ebitda = fundamentals.get("ebitda")
    if ebitda is not None:
        if ebitda > 0:
            score += 0.05
            reasons.append("Positive EBITDA")
        else:
            score -= 0.05
            reasons.append("Negative EBITDA")

    # Operating Cashflow
    ocf = fundamentals.get("operatingCashflow")
    if ocf is not None:
        if ocf > 0:
            score += 0.05
            reasons.append("Positive operating cashflow")
        else:
            score -= 0.05
            reasons.append("Negative operating cashflow")

    # EPS
    eps = fundamentals.get("trailingEPS")
    if eps:
        try:
            eps_val = float(eps)
            if eps_val > 0:
                score += 0.05
                reasons.append("Profitable EPS")
            else:
                score -= 0.05
                reasons.append("Negative EPS")
        except Exception:
            pass
    # ---------------- Normalize Score ----------------
    score = max(-1.0, min(1.0, score))
    conf = round(abs(score), 2)

    # ---------------- Final Recommendation ----------------
    if score > 0.2:
        rec = "Bullish"
    elif score < -0.2:
        rec = "Bearish"
    else:
        rec = "Neutral"

    return {
        "label": rec,
        "confidence": conf,
        "score": round(score, 3),
        "reasons": reasons,
    }


def build_snapshot(ticker: str, window="30d", interval="1d"):
    """
    Build a complete research snapshot for a stock:
    - OHLCV data + technical indicators
    - Fundamentals (yfinance)
    - Sentiment & news summaries
    - Recommendation (explainable)
    """
    # --- Parse window days like '30d' -> 30 ---
    days = int(window.rstrip("d")) if isinstance(window, str) and window.endswith("d") else 30
    LOG.info("Building snapshot for %s window %s", ticker, window)

    # --- 1) OHLC and indicators ---
    df = fetch_ohlc_df(ticker, window_days=days)
    if df.empty:
        LOG.warning("No OHLC data for %s", ticker)
        tech = {}
    else:
        df_res = resample_df(df, to_interval=interval)
        tech = compute_indicators(df_res) if not df_res.empty else {}

    # --- 2) Fundamentals ---
    fundamentals = fetch_fundamentals(ticker + ".NS")  # append NSE suffix for yfinance

    # --- 3) Sentiment & summaries ---
    sentiment_meta = analyze_sentiment_window(ticker, window_days=days)

    # --- 4) Recommendation ---
    recommendation = make_recommendation(tech, sentiment_meta, fundamentals)

    # --- 5) Human-readable summary ---
    tech_signals = ", ".join(tech.get("signals", [])) if tech else "N/A"
    sentiment_pos = sentiment_meta.get("sentiment", {}).get("pos", 0.0)
    sentiment_neg = sentiment_meta.get("sentiment", {}).get("neg", 0.0)

    summary_text = (
        f"{ticker}: "
        f"Technical signals: {tech_signals}. "
        f"Sentiment → pos={sentiment_pos:.2f}, neg={sentiment_neg:.2f}. "
        f"Recommendation → {recommendation['label']} "
        f"(confidence={recommendation['confidence']})."
    )

    # --- Snapshot object ---
    snapshot = {
        "ticker": ticker,
        "window": window,
        "asof": datetime.now(timezone.utc),
        "tech": tech,
        "fundamentals": fundamentals,
        "sentiment": sentiment_meta,
        "recommendation": recommendation,
        "summary": summary_text
    }

    # --- Persist ---
    snap_col.replace_one(
        {"ticker": ticker, "window": window},
        snapshot,
        upsert=True
    )

    LOG.info("Snapshot built for %s", ticker)
    return snapshot

