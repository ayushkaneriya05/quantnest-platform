# fastapi-signal (MongoDB)
FastAPI microservice for ML trading signals using MongoDB as the feature & signal store.
## Quickstart (dev)
1. Put a trained XGBoost model in `models/current.xgb` (or run the included `trainer` script to train from `feature_snapshot` data in MongoDB).
2. Start services:
```bash
docker-compose up --build
```
3. Insert features into MongoDB `feature_snapshot` collection. Example document:
```json
{
  "symbol": "AAPL",
  "ts": "2025-09-03T15:30:00Z",
  "features": {"close": 173.12, "rsi14": 55.1, "momentum_5": 0.012}
}
```
4. Call the service (use the `SERVICE_API_KEY` header):
```bash
curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -H 'X-SERVICE-API-KEY: dev-secret' \
  -d '{"symbol":"AAPL","ts":"2025-09-03T15:30:00Z"}'
```
## Collections
- `feature_snapshot` — per-symbol per-timestamp features (document per snapshot)
- `ai_signal` — predictions saved by the service
## Extending
- Replace pymongo with motor for async DB access.
- Integrate MLflow for model registry.
- Add role-based access to endpoints.
