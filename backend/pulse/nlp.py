from typing import List, Dict
from django.conf import settings
from transformers import pipeline

CFG = getattr(settings, 'PULSE_CFG', {})

# Lazy singletons
_sentiment_pipe = None
_summarizer = None


def get_sentiment_pipe():
    global _sentiment_pipe
    if _sentiment_pipe is None:
        _sentiment_pipe = pipeline('sentiment-analysis', model=CFG.get('SENTIMENT_MODEL', 'ProsusAI/finbert'))
    return _sentiment_pipe


def get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = pipeline('summarization', model=CFG.get('SUMMARY_MODEL', 'facebook/bart-large-cnn'))
    return _summarizer


def score_headlines(headlines: List[str]) -> List[Dict[str, float]]:
    pipe = get_sentiment_pipe()
    raw = pipe(headlines)
    # FinBERT returns labels: Positive/Negative/Neutral (or lowercase depending on model)
    norm = []
    for r in raw:
        label = (r['label'] or '').lower()
        if label.startswith('pos'):
            norm.append({'positive': float(r['score']), 'neutral': 0.0, 'negative': 0.0})
        elif label.startswith('neg'):
            norm.append({'positive': 0.0, 'neutral': 0.0, 'negative': float(r['score'])})
        else:
            norm.append({'positive': 0.0, 'neutral': float(r['score']), 'negative': 0.0})
    return norm


def summarize(text: str) -> str:
    if not text.strip():
        return ''
    summ = get_summarizer()
    # Keep inputs under model max length; headlines are short anyway
    res = summ(text[:3800], max_length=120, min_length=40, do_sample=False)
    return res[0]['summary_text']