import asyncio
from datetime import date
from django.conf import settings
from .models import PulseCache, PulseHistory
from .scrapers import collect_headlines
from .nlp import score_headlines, summarize

CFG = getattr(settings, 'PULSE_CFG', {})
TTL = int(CFG.get('CACHE_TTL_SEC', 1800))

async def _build_payload():
    items = await collect_headlines()
    titles = [i['title'] for i in items if i.get('title')]
    scores = score_headlines(titles)
    for i, s in zip(items, scores):
        i['sentiment'] = s
    # Aggregate
    agg = {'pos': 0.0, 'neu': 0.0, 'neg': 0.0}
    for s in scores:
        agg['pos'] += s['positive']
        agg['neu'] += s['neutral']
        agg['neg'] += s['negative']
    n = max(len(scores), 1)
    for k in agg:
        agg[k] = round(agg[k] / n, 4)
    # Summary
    summary = summarize(" \n".join(titles[:15]))
    return {'ai_summary': summary, 'items': items, 'agg': agg}


def get_daily_pulse():
    key = 'pulse::daily'
    cached = PulseCache.get(key)
    if cached:
        return cached
    payload = asyncio.run(_build_payload())
    PulseCache.put(key, payload, TTL)

    # Save history row
    today = date.today()
    try:
        PulseHistory.objects.update_or_create(as_of_date=today, defaults={
            'n_headlines': len(payload['items']),
            'pos': payload['agg']['pos'],
            'neu': payload['agg']['neu'],
            'neg': payload['agg']['neg'],
            'summary': payload['ai_summary'][:1000]
        })
    except Exception:
        pass

    return payload