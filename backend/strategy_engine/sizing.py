"""
Standalone position sizing utilities shared by Live, Paper, and Backtest.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def compute_position_size(
    risk_evaluator: Any,
    sizing_config: Optional[Dict[str, Any]],
    price: float,
    lot_size: int = 1,
    strategy_config: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Compute order quantity using a route override or the strategy configuration.
    A quantity of zero rejects the entry.

    Args:
        risk_evaluator: RiskEvaluator instance
        sizing_config: Route-level sizing override (flat dict with sizing_method) or None
        price: Entry price
        lot_size: Lot size for derivatives
        strategy_config: Full strategy config (used when sizing_config is None)
    """
    # Determine which config to use: route override or strategy default
    config_to_use = sizing_config if sizing_config is not None else strategy_config
    
    try:
        qty = risk_evaluator.calculate_quantity(
            config_to_use,
            price,
            lot_size=lot_size,
        )
    except Exception as exc:
        logger.error("Sizing calculation error: %s", exc)
        return 0

    qty = max(int(qty or 0), 0)
    if qty <= 0:
        return 0

    return qty
