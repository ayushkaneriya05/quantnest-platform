import re
import time
import httpx
from bs4 import BeautifulSoup
import feedparser
from django.conf import settings
from fake_useragent import UserAgent

CFG = getattr(settings, 'PULSE_CFG', {})
TIMEOUT = int(CFG.get('SCRAPE_TIMEOUT', 12))
MAX_ITEMS = int(CFG.get('MAX_HEADLINES', 25))

ua = UserAgent()

HEADERS = {
    'User-Agent': ua.random,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

async def fetch_html(client, url: str) -> str:
    r = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

async def scrape_moneycontrol_markets(client) -> list[dict]:
    url = 'https://www.moneycontrol.com/news/business/markets/'
    html = await fetch_html(client, url)
    soup = BeautifulSoup(html, 'lxml')
    out = []
    for a in soup.select('a'):  # broad fallback selection; filter below
        title = (a.get_text(strip=True) or '')
        href = a.get('href')
        if not href or not title:
            continue
        if len(title.split()) < 6:
            continue
        if '/news/business/markets/' not in href:
            continue
        out.append({
            'title': title,
            'url': href,
            'source': 'Moneycontrol',
            'published_at': None
        })
        if len(out) >= MAX_ITEMS:
            break
    return out

async def scrape_google_news_rss(query: str = None) -> list[dict]:
    if not CFG.get('ENABLE_GOOGLE_NEWS_RSS', True):
        return []
    q = query or CFG.get('GOOGLE_NEWS_RSS_Q', 'India markets')
    # English-India edition
    feed_url = f'https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en'
    feed = feedparser.parse(feed_url)
    items = []
    for e in (feed.entries or [])[:MAX_ITEMS]:
        items.append({
            'title': getattr(e, 'title', ''),
            'url': getattr(e, 'link', ''),
            'source': 'Google News',
            'published_at': getattr(e, 'published', None)
        })
    return items

async def collect_headlines() -> list[dict]:
    # Use HTTP/2 capable client for speed
    async with httpx.AsyncClient(http2=True) as client:
        mc = await scrape_moneycontrol_markets(client)
    rss = await scrape_google_news_rss()
    # Deduplicate by URL/title
    seen = set()
    out = []
    for it in mc + rss:
        key = (it['url'] or '')[:150]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
        if len(out) >= MAX_ITEMS:
            break
    return out