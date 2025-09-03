# QuantNest AI Research Assistant (FastAPI microservice)

This microservice is part of the **QuantNest trading platform**.  
It provides research snapshots for tickers using:

- OHLC data & technical indicators
- Scraped market news
- Lightweight NLP (sentiment & summarization)

---

## 🚀 Quickstart (Development)

1. Create and populate a `.env` file (do NOT commit it to git). Example:

   ```
   MONGO_URI="<Your-MongoDB-connection-string>"
   MONGO_DB="<Your-database-name>"
   FASTAPI_SECRET='your-secret'
   SCRAPER_DELAY_SECONDS= 3
   SNAPSHOT_FRESHNESS_MINUTES= 2
   ```

2. Create a virtualenv and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Start the service:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8001 --reload
   ```

## Quickstart (Docker)

Build :

```bash
docker build -t quantnest-ai:latest .
```

Run :

```bash
docker run -e MONGO_URI='mongodb://host.docker.internal:27017/' -p 8001:8001 quantnest-ai:latest
```
