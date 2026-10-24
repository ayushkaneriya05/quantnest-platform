"""Catalog schema, launch seed and data-managed publication.

The constants below seed a fresh database. Runtime terms come from
the active database revision; published and purchased snapshots are immutable.
"""
from copy import deepcopy

REVISION = "2026-10-markets-2"
MARKETS = {
    "nse_stocks": {"code": "nse_stocks", "name": "NSE stocks", "status": "available"},
    "nse_futures": {"code": "nse_futures", "name": "NSE futures", "status": "coming_soon"},
    "nse_options": {"code": "nse_options", "name": "NSE options", "status": "coming_soon"},
}
PLAN_MARKETS = {
    "explore": ("nse_stocks",),
    "build": ("nse_stocks", "nse_futures", "nse_options"),
    "pro": ("nse_stocks", "nse_futures", "nse_options"),
}
# One definition per allowance. Defaults are Explore, Build and Pro respectively;
# Published database catalogs supply public values; Private has no quotas.
ALLOWANCES = {
    "strategies": {"label": "Saved strategies", "kind": "inventory", "defaults": (3, 10, 50), "model": "strategies.Strategy"},
    "saved_screens": {"label": "Saved screens", "kind": "inventory", "defaults": (2, 10, 30),
                      "model": "research.ResearchSession", "filters": {"kind": "SCREEN"}},
    "paper_deployments": {"label": "Active Paper deployments", "kind": "inventory", "defaults": (1, 1, 3)},
    "paper_instruments": {"label": "Active Paper instruments", "kind": "inventory", "defaults": (1, 5, 20)},
    "backtest_credits": {"label": "Backtest credits per period", "kind": "period", "defaults": (5, 20, 100),
                         "resource_type": "backtest", "model": "backtesting.BacktestRun", "task": "backtesting.run_backtest",
                         "pricing": "source_candles"},
    "research_turns": {"label": "AI messages per period", "kind": "period", "defaults": (3, 10, 30),
                       "resource_type": "research", "model": "research.ResearchRun", "task": "research.start_research"},
    "screens": {"label": "Screener runs per period", "kind": "period", "defaults": (10, 100, 300),
                "resource_type": "research", "model": "research.ResearchRun", "task": "research.start_research"},
    "monte_carlo": {"label": "Monte Carlo runs per period", "kind": "period", "defaults": (1, 5, 10),
                    "resource_type": "monte_carlo", "model": "backtesting.MonteCarloRun", "task": "backtesting.run_monte_carlo"},
    "research_instruments": {"label": "Stocks per research request", "kind": "per_request", "defaults": (5, 20, 50)},
    "backtest_attachments": {"label": "Backtests attached per request", "kind": "per_request", "defaults": (3, 3, 3)},
    "backtest_workload": {"label": "Source candles per backtest", "kind": "per_request", "defaults": (100000, 250000, 1000000)},
    "mc_simulations": {"label": "Simulations per Monte Carlo run", "kind": "per_request", "defaults": (1000, 1000, 1000)},
}
LIMIT_LABELS = {key: definition["label"] for key, definition in ALLOWANCES.items()}
PLANS = {
    code: {"code": code, "name": name, "price_minor": price, "currency": "INR",
           "interval": "month", "limits": {key: definition["defaults"][i] for key, definition in ALLOWANCES.items()},
           "markets": [deepcopy(MARKETS[market]) for market in PLAN_MARKETS[code]]}
    for i, (code, name, price) in enumerate((("explore", "Explore", 0), ("build", "Build", 49900), ("pro", "Pro", 149900)))
}
FEATURES = [
    {"code": code, "name": name, "documentation": f"/docs/{code}/", "description": description}
    for code, name, description in [
        ("research", "AI Research Assistant", "Explain calculations, clarify your rules and review recorded evidence."),
        ("screener", "Market Screener", "Evaluate your selected stocks against your explicit conditions."),
        ("builder", "Strategy Builder", "Define your own entry, exit, sizing and risk settings; preserve versions."),
        ("backtesting", "Backtesting", "Evaluate saved rules against historical candles with costs and diagnostics."),
        ("terminal", "Simulated Terminal", "Practise manual order handling against observed prices."),
        ("paper", "Automated Paper", "Run your approved versions in a separate simulated account."),
        ("journal", "Journal and Reports", "Review recorded closes separately for Terminal, Paper and Live."),
        ("controls", "Account and Controls", "Manage security, versions, activity and execution restrictions."),
    ]
]


def get_catalog_specification():
    return deepcopy({"revision": REVISION, "plans": PLANS, "features": FEATURES,
                     "markets": [market["name"] for market in MARKETS.values() if market["status"] == "available"],
                     "market_catalog": list(MARKETS.values()),
                     "live": "not-offered", "credit_candles": 100000,
                     "refund_days": 7, "rollover": False, "paid_overages": False,
                     "pricing": "Prices exclude applicable taxes. No automatic overages.",
                     "simulation": "Simulated fills differ from actual broker execution."})


def validate_catalog_specification(data, revision):
    """Reject incomplete revisions before they can become customer terms."""
    from django.core.exceptions import ValidationError
    if not isinstance(data, dict) or data.get("revision") != revision:
        raise ValidationError("The specification revision must match the catalog revision.")
    plans = data.get("plans")
    if not isinstance(plans, dict) or set(plans) != set(PLANS):
        raise ValidationError("Provide Explore, Build and Pro plans.")
    for code, plan in plans.items():
        if not isinstance(plan, dict) or plan.get("code") != code or not isinstance(plan.get("name"), str) or not plan["name"].strip():
            raise ValidationError(f"Provide a valid code and customer name for {code}.")
        if type(plan.get("price_minor")) is not int or plan["price_minor"] < 0 or (code == "explore" and plan["price_minor"] != 0):
            raise ValidationError("Plan prices must be non-negative integers in paise; Explore must be free.")
        if plan.get("currency") != "INR" or plan.get("interval") != "month":
            raise ValidationError("Hosted plans currently support monthly INR billing.")
        allowances = plan.get("limits")
        if not isinstance(allowances, dict) or set(allowances) != set(LIMIT_LABELS) or any(type(value) is not int or value < 0 for value in allowances.values()):
            raise ValidationError(f"Enter a non-negative integer for every {code} allowance.")
        markets = plan.get("markets")
        if not isinstance(markets, list) or any(not isinstance(market, dict) or market.get("code") not in MARKETS or market.get("status") not in {"available", "coming_soon"} for market in markets):
            raise ValidationError(f"Provide valid markets for {code}.")
        if any(market["code"] != "nse_stocks" and market["status"] == "available" for market in markets):
            raise ValidationError("Futures/options execution is not implemented; retain Coming soon.")
    features = data.get("features")
    expected = {row["code"] for row in FEATURES}
    if not isinstance(features, list) or any(not isinstance(row, dict) for row in features) or {row.get("code") for row in features} != expected or len(features) != len(expected):
        raise ValidationError("Provide each supported feature exactly once.")
    if type(data.get("credit_candles")) is not int or data["credit_candles"] < 1:
        raise ValidationError("The backtest credit candle unit must be a positive integer.")


def get_active_catalog():
    from .models import CatalogRevision
    try:
        return CatalogRevision.objects.get(is_active=True)
    except CatalogRevision.DoesNotExist as exc:
        raise RuntimeError("No active catalog. Run database migrations, then publish a catalog in Operations Admin.") from exc


def publish_catalog(catalog):
    """Activate a validated snapshot without changing existing purchased terms."""
    from django.db import transaction
    from django.utils import timezone
    from .models import CatalogRevision
    with transaction.atomic():
        # A fresh database is seeded during migration, so this serializes all
        # publications against the same existing rows. The unique constraint
        # additionally prevents two active revisions.
        list(CatalogRevision.objects.select_for_update().order_by("pk"))
        row = CatalogRevision.objects.get(pk=catalog.pk)
        row.full_clean()
        CatalogRevision.objects.filter(is_active=True).exclude(pk=row.pk).update(is_active=False)
        row.is_active = True
        row.published_at = row.published_at or timezone.now()
        row.save(update_fields=["is_active", "published_at"])
        return row
