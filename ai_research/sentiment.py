# sentiment.py
from transformers import pipeline
from utils import LOG
from typing import List

# Lazy model loaders
_sentiment_pipe = None
_summarizer_pipe = None

def get_sentiment_pipe():
    global _sentiment_pipe
    if _sentiment_pipe is None:
        LOG.info("Loading sentiment model (FinBERT)...")
        try:
            _sentiment_pipe = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        except Exception as e:
            LOG.exception("Failed to load FinBERT; falling back to 'distilbert-base-uncased-finetuned-sst-2-english'")
            _sentiment_pipe = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    return _sentiment_pipe

def get_summarizer():
    global _summarizer_pipe
    if _summarizer_pipe is None:
        LOG.info("Loading summarizer model (bart-large-cnn)...")
        try:
            _summarizer_pipe = pipeline("summarization", model="facebook/bart-large-cnn")
        except Exception as e:
            LOG.exception("Failed to load BART; falling back to t5-small")
            _summarizer_pipe = pipeline("summarization", model="t5-small")
    return _summarizer_pipe

_sentiment_cache = {}
_summary_cache = {}

def analyze_text_sentiment(text: str):
    if text in _sentiment_cache:
        return _sentiment_cache[text]
    pipe = get_sentiment_pipe()
    txt = text if len(text) < 4000 else text[:4000]
    res = pipe(txt)
    label = res[0]["label"].capitalize()
    score = float(res[0]["score"])
    result = {"label": label, "score": score}
    _sentiment_cache[text] = result
    return result

def summarize_text(text: str, max_length=120):
    if text in _summary_cache:
        return _summary_cache[text]
    pipe = get_summarizer()
    txt = text[:4000] if len(text) > 4000 else text
    out = pipe(txt, max_length=max_length, min_length=30, truncation=True)
    result = out[0]["summary_text"]
    _summary_cache[text] = result
    return result