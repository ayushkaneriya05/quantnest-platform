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
    sl_distance: Optional[float] = None,
    lot_size: int = 1,
    strategy_config: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Compute order quantity while preserving risk/sizing rejection.

    A return value of 0 means "do not place an order". We only fall back to
    fixed quantity when the sizing config explicitly asks for a valid fixed
    quantity and the evaluator itself errors.

    Args:
        risk_evaluator: RiskEvaluator instance
        sizing_config: Route-level sizing override (flat dict with sizing_method) or None
        price: Entry price
        sl_distance: Stop loss distance
        lot_size: Lot size for derivatives
        strategy_config: Full strategy config (used when sizing_config is None)
    """
    # Determine which config to use: route override or strategy default
    config_to_use = sizing_config if sizing_config is not None else strategy_config
    
    try:
        qty = risk_evaluator.calculate_quantity(
            config_to_use,
            price,
            sl_distance=sl_distance,
            lot_size=lot_size,
            strategy_config=strategy_config
        )
    except Exception as exc:
        logger.error("Sizing calculation error: %s", exc)
        return 0

    qty = max(int(qty or 0), 0)
    if qty <= 0:
        return 0

    return qty
