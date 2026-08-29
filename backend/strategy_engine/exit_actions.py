"""
Exit action logic extracted from OrderDispatcher.

These functions interpret exit actions (EXIT_ALL, PARTIAL_EXIT,
MOVE_TO_BREAKEVEN) and compute the resulting state mutations and
order parameters.  They are pure functions that do NOT publish
orders or touch Redis — the caller is responsible for dispatch.

This module is shared by Live/Paper engines (via OrderDispatcher) and
the Backtest engine.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from common.enums import Side, OrderType

logger = logging.getLogger(__name__)


@dataclass
class ExitDecision:
    """Result of processing an exit action."""
    should_send_order: bool = False
    quantity: int = 0
    side: str = ""
    order_type: str = OrderType.MARKET
    reason: str = ""
    # State updates to apply to the runtime state
    state_updates: Dict[str, Any] = None

    def __post_init__(self):
        if self.state_updates is None:
            self.state_updates = {}


def process_exit_action(
    action: str,
    params: Optional[Dict[str, Any]],
    position: Dict[str, Any],
    reason: str,
) -> ExitDecision:
    """
    Process an exit action and return a decision describing what to do.

    Parameters
    ----------
    action : str
        One of 'EXIT_ALL', 'PARTIAL_EXIT', 'MOVE_TO_BREAKEVEN'.
    params : dict, optional
        Action parameters (e.g. {'exit_pct': 50}).
    position : dict
        Current position state from runtime.
    reason : str
        Human-readable reason for the exit.

    Returns
    -------
    ExitDecision
        Contains whether to send an order, the quantity, side, and any
        state updates to apply.
    """
    params = params or {}

    if action == "MOVE_TO_BREAKEVEN":
        if not position.get(f"breakeven_{reason}"):
            return ExitDecision(
                should_send_order=False,
                state_updates={
                    "protected_stop_price": position.get("avg_price"),
                    f"breakeven_{reason}": True,
                },
            )
        # Already applied — no-op
        return ExitDecision()

    elif action == "PARTIAL_EXIT":
        exit_pct = float(params.get("exit_pct", 50))
        if not position.get(f"partial_exit_{reason}"):
            exit_qty = int(position.get("quantity", 0) * (exit_pct / 100.0))
            state_updates = {f"partial_exit_{reason}": True}
            if exit_qty > 0:
                return ExitDecision(
                    should_send_order=True,
                    quantity=exit_qty,
                    side=Side.SELL if position.get("side") == Side.BUY else Side.BUY,
                    reason=f"Partial Exit ({exit_pct}%): {reason}",
                    state_updates=state_updates,
                )
            # Qty too small but mark as evaluated
            return ExitDecision(should_send_order=False, state_updates=state_updates)
        return ExitDecision()

    else:  # EXIT_ALL (default)
        qty = position.get("quantity", 0)
        if qty > 0:
            return ExitDecision(
                should_send_order=True,
                quantity=qty,
                side=Side.SELL if position.get("side") == Side.BUY else Side.BUY,
                reason=reason,
            )
        return ExitDecision()
