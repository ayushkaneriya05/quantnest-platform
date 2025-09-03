# scraper.py
import json
from pathlib import Path
import requests
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from slugify import slugify
from utils import get_db, LOG

# Sections to crawl for market/news content (can be extended)

db = get_db()
news_col = db.news_articles

# Ensure indexes (run once)
def ensure_indexes():
    news_col.create_index([("url", 1)], unique=True)
    news_col.create_index([("ticker", 1), ("ts", -1)])
    news_col.create_index([("ts", -1)])

BASE = "https://groww.in/v1/api/stocks_data/v1/company/search_id/"

def get_company_data(search_id: str):
    url = f"{BASE}{search_id}?page=0&size=10"
    r = requests.get(url, headers={"user-agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.json()
    
def fetch_all_news(company_id: str, size: int = 10):
    """
    Fetch all news for a given Groww companyId (like GSTK500400)
    Stops when API returns empty or less than 'size'
    """
    base_url = "https://groww.in/v1/api/groww-news/v2/stocks/news"
    headers = {"user-agent": "Mozilla/5.0"}
    
    page = 1
    all_news = []

    while True:
        url = f"{base_url}/{company_id}?page={page}&size={size}"
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()

        content = data.get("results", [])
        if not content:
            break  # no more news

        all_news.extend(content)

        # Stop if this page had less than requested size
        if len(content) < size:
            break

        page += 1
        time.sleep(SCRAPER_DELAY_SECONDS)

    return all_news




BASE_DIR = Path(__file__).resolve().parent
nifty100_path = BASE_DIR /"data"/"nifty100_symbols.json"
nifty100_data = json.loads(nifty100_path.read_text())

def crawl_groww():
    ensure_indexes()
    for t in nifty100_data:
        search_id = slugify(t["company_name"])
        try:
            company = get_company_data(search_id)
            groww_id = company["header"]["growwCompanyId"]
            news = fetch_all_news(groww_id, size=50)
            for n in news:
                doc = {
                    "title": n.get("title"),
                    "url": n.get("url"),
                    "source": n.get("source") or "groww.in",
                    "ts": datetime.fromisoformat(n.get("pubDate").replace("Z", "+00:00")) if n.get("pubDate") else None,
                    "ticker": t,
                    "fetched_at": datetime.now(timezone.utc)
                }
                try:
                    news_col.insert_one(doc)
                    LOG.info("Inserted article: %s", doc.get("title"))
                except DuplicateKeyError:
                    LOG.info("Already have article: %s", doc.get("url"))
        except Exception as e:
            LOG.exception("Error crawling section %s: %s",t["company_name"], e)
    LOG.info("Crawl completed. Total attempted")