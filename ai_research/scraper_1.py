import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
from pymongo.errors import DuplicateKeyError

from datetime import datetime

def parse_et_timestamp(ts_str):
    if not ts_str:
        return None
    try:
        return datetime.strptime(ts_str.replace(" IST", ""), "%d %b %Y, %I:%M%p")
    except Exception as e:
        print("Timestamp parse error:", ts_str, e)
        return None
    
# Mongo Setup
client = MongoClient("mongodb://localhost:27017/")
db = client["stock_news"]
tickers_col = db["et_tickers"]
news_col = db["et_news"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

def ensure_indexes():
    news_col.create_index([("url", 1)], unique=True)
BASE_DIR = Path(__file__).resolve().parent
nifty100_path = BASE_DIR /"data"/"nifty100_symbols.json"
# Step 1: Load Nifty100 symbols JSON
with open(nifty100_path, "r") as f:
    nifty100 = json.load(f)

# Step 2: Fetch companyid from ET stocksearch
def fetch_company_id(symbol):
    url = f"https://economictimes.indiatimes.com/stocksearch.cms?ticker={symbol}"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    li = soup.select_one("li a[data-compid]")
    if not li:
        print(f"No companyid found for {symbol}")
        return None

    comp_id = li["data-compid"]
    comp_name = li.text.strip()
    return comp_id, comp_name

# Step 3: Save ticker -> companyid mapping to Mongo
for stock in nifty100:
    symbol = stock["symbol"]
    comp_data = fetch_company_id(symbol)
    if comp_data:
        comp_id, comp_name = comp_data
        tickers_col.update_one(
            {"symbol": symbol},
            {"$set": {"company_name": comp_name, "company_id": comp_id}},
            upsert=True
        )
        print(f"Saved {symbol} ({comp_id})")
    time.sleep(1)  # avoid rate limit

# Step 4: Fetch news list for companyid
def fetch_news_list(company_id):
    url = f"https://economictimes.indiatimes.com/stocksupdate_news/companyid-{company_id}.cms"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    stories = []
    for story in soup.select("div.eachStory"):
        title_tag = story.select_one("h3 a")
        time_tag = story.select_one("time")
        summary_tag = story.select_one("p")
        if not title_tag:
            continue

        stories.append({
            "title": title_tag.text.strip(),
            "url": "https://economictimes.indiatimes.com" + title_tag["href"],
            "timestamp": time_tag.text.strip() if time_tag else None,
            "summary": summary_tag.text.strip() if summary_tag else ""
        })
    return stories

# Step 5: Fetch full article text
def fetch_article(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    article_div = soup.select_one("div.artText")
    if not article_div:
        article_div = soup.select_one("div.content")
        if not article_div:
            return ""

    # Remove unwanted elements (ads, widgets, styles, scripts, etc.)
    for bad in article_div.find_all(["style", "script", "iframe", "noscript", "table", "ul", "ol", "div"]):
        bad.decompose()

    # Get continuous text (anchors included)
    article_text = article_div.get_text(" ", strip=True)

    # Normalize spaces
    return " ".join(article_text.split())


# Step 6: Store news articles in Mongo
def scrape_and_store(symbol, company_id, company_name):
    ensure_indexes()
    news_list = fetch_news_list(company_id)
    for news in news_list:
        # article_text = fetch_article(news["url"])
        doc = {
            "tickers": [{"symbol": symbol, "company_name": company_name}],
            "title": news["title"],
            "url": news["url"],
            # "article": article_text,
            "summary": news["summary"],
            "timestamp": parse_et_timestamp(news["timestamp"])
        }
        try:
            news_col.insert_one(doc)
        except DuplicateKeyError:
            result = news_col.update_one({"url": doc["url"]}, {"$push": {"tickers": {"symbol": symbol, "company_name": company_name}}})
        print(f"Stored article: {news['title'][:50]}...")

# Step 7: Run for all stocks
for ticker_doc in tickers_col.find():
    scrape_and_store(
        ticker_doc["symbol"],
        ticker_doc["company_id"],
        ticker_doc["company_name"]
    )
    time.sleep(2)  # politeness delay
