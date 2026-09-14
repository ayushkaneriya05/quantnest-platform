# QuantNest - Trading Research, Backtesting, Paper Trading, and Live Execution

QuantNest is a full-stack trading platform for building strategies, validating them with historical data, deploying them to paper trading, placing manual trades, and running broker-connected live trading sessions.

The codebase combines a Django/DRF backend with a React/Vite dashboard. It includes authentication, instruments and market data, strategy configuration, rule evaluation, risk management, portfolio allocation, backtesting, paper trading, manual trading, broker integrations, live execution, analytics, AI/research modules, marketplace/community features, and operational audit trails.

> Trading systems can lose money. This project is software infrastructure, not financial advice. Always test with paper trading before connecting live capital.

---

## Contents

- [Core Workflow](#core-workflow)
- [Feature Map](#feature-map)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Local Setup](#local-setup)
- [Environment Notes](#environment-notes)
- [API Overview](#api-overview)
- [Background Jobs and Commands](#background-jobs-and-commands)
- [Testing](#testing)
- [Operational Notes](#operational-notes)
- [Roadmap](#roadmap)

---

## Core Workflow

### 1. Create a Strategy

Strategies are configured through the strategy builder and persisted through the `strategies` app.

Supported configuration areas include:

- Strategy metadata, status, visibility, tags, and version history.
- Watchlist instruments.
- Entry rule groups.
- Stop-loss and target rule groups.
- Entry order settings: side, order type, price logic, offsets, cooldowns, and attempt limits.
- Exit order settings.
- Re-entry and reverse-entry behavior.
- Time rules: trading days, sessions, start/end times, no-trade windows, candle completion mode.
- Special event filters.
- Position sizing rules.
- Auto-disable rules.

The shared runtime representation is produced by `Strategy.to_execution_dict()` and consumed by the unified executor in `backend/strategy_engine/executor.py`.

### 2. Backtest the Strategy

Backtesting runs historical OHLC data through the same strategy executor used by paper and live flows.

The backtest engine supports:

- Historical candle loading with warmup periods.
- Multi-timeframe market data with proper alignment (no look-ahead bias).
- Indicator/rule evaluation on completed candles only.
- Entry, stop-loss, target, trailing, EOD, expiry, and time-based exits.
- Position sizing and portfolio risk checks.
- Simulated market, limit, stop-market, and stop-limit entries.
- Equity curve generation.
- Trade list, metrics, analytics, drawdown, brokerage, and slippage.
- WebSocket progress updates.
- Monte Carlo simulation endpoints.

Primary code:

- `backend/backtesting/engine.py` - Core backtest engine
- `backend/backtesting/context.py` - In-memory state management
- `backend/backtesting/execution_service.py` - Execution service
- `backend/backtesting/views.py` - Backtest API endpoints
- `frontend/src/features/dashboard/pages/backtest/`

### 3. Allocate Capital

Capital is managed through the paper portfolio layer and reused by paper and live deployment flows.

Portfolio support includes:

- Deposits and withdrawals.
- Fixed and percentage strategy allocations.
- Allocation-level used/available capital.
- Paper account creation per strategy allocation.
- Daily performance snapshots.
- Exposure snapshots.
- Portfolio, allocation, and transaction APIs.

Primary code:

- `backend/paper_trading/services.py`
- `frontend/src/features/dashboard/pages/portfolio/`
- `frontend/src/features/dashboard/pages/paper/PaperAllocations.jsx`

### 4. Deploy to Paper Trading

Paper deployment enables a strategy to run against live/recent market data without sending orders to a broker.

Paper trading supports:

- Strategy deployment through `deploy-paper`.
- Paper accounts tied to strategy allocations.
- Live tick processing via `PaperExecutionService`.
- Strategy-driven paper orders.
- Paper positions and trade history.
- PnL, margin, exposure, and allocation sync.
- Pending order handling for limit/stop orders.
- Manual paper account lifecycle operations.

Primary code:

- `backend/paper_trading/services.py`
- `backend/paper_trading/views.py`
- `frontend/src/features/dashboard/pages/paper/`

### 5. Manual Trading Terminal

Manual trading is exposed through the trading terminal APIs and dashboard page.

Manual trading supports:

- Terminal snapshot.
- Instrument search.
- Watchlist add/remove.
- Candle and latest quote loading.
- Manual order placement.
- Order book, positions, account summary, and trade history.

Primary code:

- `backend/trading/views.py`
- `backend/trading/services.py`
- `frontend/src/features/dashboard/pages/trading/`

### 6. Connect Broker Accounts

Broker support is handled separately from strategy logic so live trading can sync funds, orders, sessions, and broker health.

Broker functionality includes:

- Broker credential management.
- Fyers auth URL and callback flow.
- Session creation and refresh.
- Funds, positions, holdings, and orderbook sync.
- Order settings.
- API logs.
- Order reconciliation.
- Broker circuit breaker utilities.

Primary code:

- `backend/brokers/`
- `backend/strategy_engine/circuit_breaker.py`
- `frontend/src/features/dashboard/pages/brokers/`

### 7. Deploy to Live Trading

Live deployment creates a broker-connected trading session for a strategy.

Live trading supports:

- Deploy strategy to live with fixed or percentage allocation.
- Session pause, resume, stop, stop-all, run-once, and sync.
- Broker margin and allocation validation.
- Strategy-driven order placement.
- Broker order lifecycle tracking.
- Partial fill handling.
- Position sync from broker state.
- Slippage records.
- Execution logs.
- Emergency controls and live portfolio views.

Primary code:

- `backend/live_trading/services.py`
- `backend/live_trading/views.py`
- `frontend/src/features/dashboard/pages/live/`

### 8. Review, Analyze, and Improve

QuantNest also includes modules for:

- Analytics and reports.
- Trade journal.
- AI advisor, strategy health, and market regime.
- Marketplace and subscriptions.
- Community, learning, reputation, proofs, replays, and gamification.
- Notifications, audit logs, and platform events.

---

## Feature Map

### Implemented Backend Domains

- Authentication, JWT, profile, 2FA, password reset.
- Instruments and watchlists.
- Market data, candles, latest ticks, live quotes, Fyers utilities.
- Strategy CRUD, versioning, activation, pause/archive, clone, paper/live deployment.
- Rules engine and shared strategy executor.
- Risk management and runtime risk cache.
- Backtesting and Monte Carlo.
- Paper portfolio, allocations, accounts, positions, orders, trades, transactions, exposure, performance.
- Manual trading terminal APIs.
- Broker credentials, sessions, settings, logs, reconciliation.
- Live trading sessions, orders, positions, allocations, logs, slippage.
- Analytics, AI, marketplace, audit, notifications, journal, community, learning, reputation, proofs, replays, moderation, gamification.

### Implemented Frontend Areas

- Landing page.
- Auth screens and 2FA flows.
- Dashboard shell and navigation.
- Market overview and search.
- Strategy wizard, rule builders, risk/time/asset settings, version history, marketplace pages.
- Backtest setup, results, trade list, equity/drawdown charts, Monte Carlo.
- Trading terminal.
- Portfolio overview, risk, exposure, allocations, transactions.
- Paper capital, allocations, portfolio, positions, orders, trade history, analytics, wallet.
- Broker connections, order settings, broker logs.
- Live portfolio, strategies, orders, positions, execution logs, emergency controls, performance and analysis components.
- AI/research, alerts, journal, governance, community, learning, marketplace.

---

## Architecture

### Backend

- Python, Django, Django REST Framework.
- SimpleJWT, dj-rest-auth, allauth, django-otp.
- Channels and Redis for WebSocket-ready workflows.
- Celery for background jobs and scheduled tasks.
- ZeroMQ for order routing from strategy workers to execution services.
- Redis Pub/Sub for session execution manager orchestration.
- PostgreSQL recommended for production (TimescaleDB for candle data).
- Fyers and SmartAPI related broker packages.
- Pandas/pandas-ta for market data and indicators.

### Frontend

- React 18 with Vite.
- TailwindCSS and Radix UI primitives.
- Redux Toolkit.
- Axios service layer.
- lightweight-charts and Recharts.
- lucide-react icons.

### Shared Execution Model

The strategy decision layer is centralized in:

- `backend/strategy_engine/executor.py`
- `backend/strategy_engine/runtime.py`
- `backend/rules_engine/`
- `backend/risk_management/evaluator.py`

Backtest, paper, and live all use the shared executor for signals and exits. Execution accounting is intentionally separated by environment:

- Backtest simulates historical fills.
- Paper simulates orders and positions in the database.
- Live submits and reconciles broker orders.

Because live brokers introduce real fills, rejections, partial fills, and latency, exact equality between backtest, paper, and live should be treated as a deterministic simulation target, not a guarantee for real broker execution.

---

## Project Structure

```text
QuantNest/
+-- backend/
|   +-- backend/             # Django settings, ASGI/WSGI, root URLs
|   +-- users/               # Auth, profile, 2FA
|   +-- instruments/         # Instrument search and sync
|   +-- marketdata/          # Candles, ticks, Fyers market data, streaming
|   +-- strategies/          # Strategy CRUD, config, versioning, deployment
|   +-- rules_engine/        # Rule models and evaluation
|   +-- strategy_engine/     # Shared executor, runtime state, circuit breaker
|   +-- risk_management/     # Risk profiles, evaluator, cache
|   +-- backtesting/         # Historical simulation and Monte Carlo
|   +-- paper_trading/       # Portfolio, allocations, paper accounts/orders/trades
|   +-- trading/             # Manual trading terminal APIs
|   +-- brokers/             # Broker credentials, sessions, settings, logs
|   +-- live_trading/        # Live sessions, orders, positions, slippage
|   +-- analytics/           # Analytics suite
|   +-- ai_engine/           # AI advisor and health/regime services
|   +-- trade_journal/       # Journal entries and reporting
|   +-- marketplace/         # Strategy listings/subscriptions
|   +-- notifications/       # User notifications
|   +-- audit/               # Audit records
|   +-- manage.py
+-- frontend/
|   +-- src/shared/          # API clients, hooks, store, UI components
|   +-- src/features/auth/   # Login/register/password/2FA UI
|   +-- src/features/dashboard/
|   |   +-- pages/strategy/  # Strategy builder
|   |   +-- pages/backtest/  # Backtest UX
|   |   +-- pages/trading/   # Manual terminal
|   |   +-- pages/paper/     # Paper trading UX
|   |   +-- pages/live/      # Live trading UX
|   |   +-- pages/brokers/   # Broker UX
|   |   +-- pages/portfolio/ # Portfolio UX
|   +-- vite.config.js
+-- README.md
```

---

## Local Setup

### Prerequisites

- Python 3.11 recommended.
- Node.js 18+.
- PostgreSQL recommended.
- Redis recommended for cache, locks, Channels, and Celery.
- Broker API credentials only if testing live trading.

### Backend

```bash
cd backend
python -m venv ..\.venv
..\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

On macOS/Linux, activate the virtualenv with:

```bash
source ../.venv/bin/activate
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

Backend URL:

```text
http://localhost:8000
```

Health check:

```text
GET /health/
```

---

## Environment Notes

The backend uses `python-decouple`, so boolean environment values must be valid booleans.

Use:

```env
DEBUG=False
```

Do not use:

```env
DEBUG=release
```

Common production settings:

```env
SECRET_KEY=change-me
DEBUG=False
DATABASE_URL=postgres://...
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Configure broker, Cloudinary, email, and AI/provider keys only for modules you actively use.

---

## API Overview

All application APIs are mounted under:

```text
/api/v1/
```

### Auth and Users

```text
POST /api/v1/users/auth/registration/
POST /api/v1/users/auth/login/
POST /api/v1/users/auth/token/refresh/
GET  /api/v1/users/profile/
PUT  /api/v1/users/profile/
POST /api/v1/users/2fa/*
POST /api/v1/users/auth/password/reset/
POST /api/v1/users/auth/password/reset/confirm/
```

### Market Data

```text
GET /api/v1/market/candles/
GET /api/v1/market/ohlc/
GET /api/v1/market/latest-tick/
GET /api/v1/market/live/quote/
GET /api/v1/market/live/indices/
GET /api/v1/market/events/
GET /api/v1/market/fyers/login/
GET /api/v1/market/fyers/callback/
GET /api/v1/market/fyers/token/status/
GET /api/v1/market/fyers/token/refresh/
```

### Manual Trading Terminal

```text
GET    /api/v1/trading/terminal/
GET    /api/v1/trading/instruments/search/
GET    /api/v1/trading/watchlist/
POST   /api/v1/trading/watchlist/
DELETE /api/v1/trading/watchlist/
GET    /api/v1/trading/account/
GET    /api/v1/trading/account/summary/
GET    /api/v1/trading/positions/
GET    /api/v1/trading/orders/
POST   /api/v1/trading/orders/
GET    /api/v1/trading/history/
```

### Strategies

```text
GET    /api/v1/strategies/strategies/
POST   /api/v1/strategies/strategies/
GET    /api/v1/strategies/strategies/{id}/
PATCH  /api/v1/strategies/strategies/{id}/
DELETE /api/v1/strategies/strategies/{id}/
POST   /api/v1/strategies/strategies/{id}/activate/
POST   /api/v1/strategies/strategies/{id}/pause/
POST   /api/v1/strategies/strategies/{id}/archive/
POST   /api/v1/strategies/strategies/{id}/unarchive/
POST   /api/v1/strategies/strategies/{id}/clone/
POST   /api/v1/strategies/strategies/{id}/create-version/
GET    /api/v1/strategies/strategies/{id}/versions/
POST   /api/v1/strategies/strategies/{id}/rollback/
GET    /api/v1/strategies/strategies/{id}/tunable-parameters/
POST   /api/v1/strategies/strategies/{id}/deploy-paper/
POST   /api/v1/strategies/strategies/{id}/deploy-live/
```

Related config routes:

```text
/api/v1/strategies/tags/
/api/v1/strategies/entry-configs/
/api/v1/strategies/exit-configs/
/api/v1/strategies/reentry-rules/
/api/v1/rules/
/api/v1/risk/
```

### Backtesting

```text
GET    /api/v1/backtest/runs/
POST   /api/v1/backtest/runs/
GET    /api/v1/backtest/runs/{id}/
PATCH  /api/v1/backtest/runs/{id}/
DELETE /api/v1/backtest/runs/{id}/
POST   /api/v1/backtest/runs/{id}/start/
POST   /api/v1/backtest/runs/{id}/rerun/
POST   /api/v1/backtest/runs/{id}/cancel/
GET    /api/v1/backtest/runs/{id}/trades/
GET    /api/v1/backtest/runs/{id}/metrics/
GET    /api/v1/backtest/runs/{id}/equity_curve/
GET    /api/v1/backtest/runs/{id}/analytics/
GET    /api/v1/backtest/montecarlo/
POST   /api/v1/backtest/montecarlo/
POST   /api/v1/backtest/montecarlo/{id}/start/
GET    /api/v1/backtest/montecarlo/{id}/results/
```

Backtest WebSocket:

```text
/ws/backtest/progress/
```

### Portfolio and Paper Trading

The paper trading routes are available through both `/api/v1/paper/` and `/api/v1/portfolio/` in the current root URL configuration.

```text
GET    /api/v1/paper/portfolios/
GET    /api/v1/paper/portfolios/summary/
POST   /api/v1/paper/portfolios/deposit/
POST   /api/v1/paper/portfolios/withdraw/
GET    /api/v1/paper/allocations/
POST   /api/v1/paper/allocations/
POST   /api/v1/paper/allocations/{id}/deallocate/
GET    /api/v1/paper/allocations/summary/
GET    /api/v1/paper/accounts/
POST   /api/v1/paper/accounts/
GET    /api/v1/paper/accounts/active/
POST   /api/v1/paper/accounts/{id}/activate/
POST   /api/v1/paper/accounts/{id}/deactivate/
POST   /api/v1/paper/accounts/{id}/reset/
POST   /api/v1/paper/accounts/{id}/validate_delete/
GET    /api/v1/paper/accounts/{id}/summary/
GET    /api/v1/paper/positions/
GET    /api/v1/paper/orders/
GET    /api/v1/paper/trades/
GET    /api/v1/paper/trades/analytics/
GET    /api/v1/paper/transactions/
GET    /api/v1/paper/exposure/
GET    /api/v1/paper/performance/
```

### Brokers

```text
GET    /api/v1/brokers/credentials/
POST   /api/v1/brokers/credentials/
POST   /api/v1/brokers/credentials/{id}/verify/
POST   /api/v1/brokers/credentials/{id}/refresh/
POST   /api/v1/brokers/credentials/{id}/deactivate/
POST   /api/v1/brokers/credentials/{id}/create-session/
GET    /api/v1/brokers/credentials/{id}/auth-url/
POST   /api/v1/brokers/credentials/{id}/exchange-auth-code/
GET    /api/v1/brokers/credentials/{id}/funds-summary/
GET    /api/v1/brokers/sessions/
GET    /api/v1/brokers/settings/
POST   /api/v1/brokers/settings/
GET    /api/v1/brokers/reconciliation/
POST   /api/v1/brokers/reconciliation/{id}/resolve/
GET    /api/v1/brokers/logs/
GET    /api/v1/brokers/credentials/fyers/callback/
```

### Live Trading

```text
GET  /api/v1/live/sessions/
POST /api/v1/live/sessions/deploy/
GET  /api/v1/live/sessions/summary/
POST /api/v1/live/sessions/{id}/pause/
POST /api/v1/live/sessions/{id}/resume/
POST /api/v1/live/sessions/{id}/stop/
POST /api/v1/live/sessions/stop-all/
POST /api/v1/live/sessions/{id}/run-once/
POST /api/v1/live/sessions/{id}/sync/
POST /api/v1/live/sessions/{id}/update-allocation/
GET  /api/v1/live/orders/
POST /api/v1/live/orders/{id}/cancel/
GET  /api/v1/live/positions/
GET  /api/v1/live/allocations/
GET  /api/v1/live/execution-logs/
GET  /api/v1/live/slippage/
```

### Additional Modules

```text
/api/v1/analytics/
/api/v1/journal/
/api/v1/notifications/
/api/v1/ai/
/api/v1/marketplace/
/api/v1/audit/
/api/v1/events/
/api/v1/activity/
/api/v1/community/
/api/v1/gamification/
/api/v1/challenges/
/api/v1/learning/
/api/v1/reputation/
/api/v1/proofs/
/api/v1/replays/
/api/v1/moderation/
```

---

## Background Jobs and Commands

### Required Continuous Processes

**For Basic Development (3 processes):**

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Django ASGI
cd backend
python manage.py runserver

# Terminal 3: Frontend
cd frontend
npm run dev
```

**For Production (5 processes):**

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
cd backend
celery -A backend worker -l info

# Terminal 3: Celery Beat
cd backend
celery -A backend beat -l info

# Terminal 4: Django ASGI
cd backend
python manage.py runserver

# Terminal 5: Frontend
cd frontend
npm run dev
```

**For Full Live Trading (9 processes):**

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
cd backend
celery -A backend worker -l info

# Terminal 3: Celery Beat
cd backend
celery -A backend beat -l info

# Terminal 4: Django ASGI
cd backend
uvicorn backend.asgi:application

# Terminal 5: Frontend
cd frontend
npm run dev

# Terminal 6: Fyers Live Data Ingestion (Continuous)
cd backend
python manage.py fyers_ingest

# Terminal 7: WebSocket for Live Trading (Continuous)
cd backend
python manage.py start_websocket

# Terminal 8: Session Execution Manager (Continuous)
cd backend
python manage.py run_execution_manager

# Terminal 9: Order Subscribers (Continuous)
cd backend
python manage.py run_order_subscribers
```

### One-Time Setup Commands

```bash
cd backend

# Database setup
python manage.py migrate
python manage.py createsuperuser

# Optional: TimescaleDB setup (if using PostgreSQL + TimescaleDB)
python manage.py setup_timescale
```

### Data Management Commands

```bash
cd backend

# Sync instrument master data from Fyers (Run periodically)
python manage.py sync_instruments
# Or specific source:
python manage.py sync_instruments --source NSE_CM

# Ingest historical data with flexible options (Uses 90-day chunks per broker limit)
python manage.py ingest_historical --days 30 --timeframe 1m
python manage.py ingest_historical --start 2024-01-01 --end 2024-12-31 --timeframe 1D
python manage.py ingest_historical --days 365 --timeframe 1m
```

### Command Summary

| Command             | Purpose                                | Type       | Use Case                      |
| ------------------- | -------------------------------------- | ---------- | ----------------------------- |
| `sync_instruments`  | Sync instrument master from Fyers      | Periodic   | Nightly data sync             |
| `ingest_historical` | Ingest historical data (90-day chunks) | Periodic   | All historical data ingestion |
| `fyers_ingest`      | Live WebSocket market data streaming   | Continuous | Real-time live market data    |
| `setup_timescale`   | Enable TimescaleDB for candle table    | One-time   | Database optimization         |

### Scheduled Tasks (Celery Beat)

The following tasks are **automatically scheduled** by Celery Beat (no manual command needed):

- **Every 30s:** Refresh live market subscriptions
- **Every 1min:** Fetch live candles from broker
- **Every 1min:** Live trading reconcile OMS
- **Every 5min:** Risk check re-enable strategies
- **Every 15min:** Analytics refresh daily reports
- **Every 1hr:** Notifications dispatch daily summaries
- **Daily 00:05:** Portfolio daily performance snapshot
- **Daily 00:15:** Portfolio rebalance allocations
- **Daily 06:00:** Instruments sync Fyers master
- **Daily 23:55:** Reconcile daily market data

---

## Testing

Install development requirements if needed:

```bash
cd backend
pip install -r requirements-dev.txt
```

Run backend tests:

```powershell
cd backend
$env:DEBUG = "False"
..\.venv\Scripts\python.exe -m pytest
```

Run focused workflow tests:

```powershell
cd backend
$env:DEBUG = "False"
..\.venv\Scripts\python.exe -m pytest backtesting/tests/test_pipeline_e2e.py live_trading/tests/test_broker_sync.py paper_trading/tests/test_lifecycle_integration.py -q
```

On macOS/Linux:

```bash
DEBUG=False ../.venv/bin/python -m pytest
```

Frontend:

```bash
cd frontend
npm run build
npm run lint
```

---

## Operational Notes

### Process Requirements

**Minimum for Development:**

- Redis server
- Django ASGI server (runserver)
- Frontend dev server

**Minimum for Production:**

- Redis server
- Django ASGI server (daphne/runserver)
- Celery worker
- Celery beat
- Frontend dev server

**Full Live Trading:**

- All production processes plus:
- Fyers live data ingestion (continuous)
- WebSocket for live trading (continuous)
- Session execution manager (continuous)
- Order subscribers (continuous)

### Key Notes

- Keep Redis running for runtime locks, risk cache, Django Channels, and Celery broker/result backend.
- Use PostgreSQL for production-like testing (TimescaleDB recommended for candle data).
- Live trading requires valid broker credentials and an active broker session.
- Backtest, paper, and live share signal/exit logic via the unified executor, but fills and accounting differ by environment.
- For deterministic parity testing, compare backtest and paper using the same candles, fill model, fees, slippage, and timestamps.
- For live trading, compare expected strategy decisions to actual broker fills through execution logs, slippage records, and reconciliation records.
- Never run live execution with real capital until paper trading, risk limits, broker settings, and emergency controls are verified.
- The system uses ZeroMQ for order routing from strategy workers to execution services.
- Session execution manager uses Redis Pub/Sub for strategy worker orchestration.
- Fyers WebSocket ingestion provides real-time market data for paper/live trading.

---

## Roadmap

- Add a canonical execution ledger shared by backtest and paper simulation.
- Add formal parity tests for backtest vs paper on identical candle streams.
- Expand to futures and options backtesting with proper routing support.
- Add limit order simulation in backtest engine.
- Add partial fill simulation in backtest engine.
- Add expected-vs-actual live execution reporting for broker fills.
- Expand broker adapters beyond current integrations.
- Harden production deployment docs for ASGI, Redis, Celery, PostgreSQL, and HTTPS.
- Improve frontend coverage for every backend action endpoint.

---

## License

This project is licensed under the MIT License.

---

## Acknowledgements

- Django
- Django REST Framework
- React
- Vite
- TailwindCSS
- Radix UI
- lightweight-charts
- Recharts
- Fyers API
- Redis
- Celery
