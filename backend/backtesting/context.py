"""
BacktestContext - In-memory context for backtest execution.
Mirrors the unified cache interface but operates in-memory.
"""

import logging

logger = logging.getLogger(__name__)


class BacktestContext:
    """
    In-memory context for backtest execution.
    Mirrors the unified cache interface but operates in-memory.
    """
    def __init__(self, run_id, strategy_id, config, initial_capital, charge_profile=None, include_charges=True):
        self.run_id = run_id
        self.strategy_id = strategy_id
        self.config = config
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.charge_profile = charge_profile
        self.include_charges = include_charges
        
        # State storage (in-memory, no DB)
        self.positions = {}  # instrument_id -> position dict
        self.orders = []     # list of order dicts
        self.pending_orders = []  # Pending orders for next candle execution
        self.closed_trades = []  # completed fill records, retained after positions are removed
        self.runtime_state = {}  # instrument_id -> state dict
        self.risk_metrics = {
            "daily_trades": 0,
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "monthly_pnl": 0.0,
            "total_closed_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
        }
    
    # Unified cache interface methods
    def get_position(self, instrument_id):
        return self.positions.get(instrument_id)
    
    def update_position(self, instrument_id, position_data):
        self.positions[instrument_id] = position_data
    
    def remove_position(self, instrument_id):
        self.positions.pop(instrument_id, None)
    
    def get_risk_metrics(self):
        return self.risk_metrics.copy()
    
    def update_risk_metrics(self, metrics):
        self.risk_metrics.update(metrics)

    def reset_daily_metrics(self):
        self.risk_metrics["daily_trades"] = 0
        self.risk_metrics["daily_pnl"] = 0.0
    
    def get_available_capital(self):
        return self.current_capital
    
    def get_charge_profile(self):
        return self.charge_profile
    
    def should_include_charges(self):
        return self.include_charges
    
    # Pending order management for next candle execution
    def add_pending_order(self, order):
        """Add a pending order to be executed at next candle open."""
        self.pending_orders.append(order)
    
    def get_pending_orders(self):
        """Get all pending orders."""
        return self.pending_orders
    
    def clear_pending_orders(self):
        """Clear all pending orders after execution."""
        self.pending_orders = []
