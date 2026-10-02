"""Minimal in-memory state for a single backtest run."""

class BacktestContext:
    """
    In-memory context for backtest execution.
    Holds positions and orders in memory for one backtest run.
    """
    def __init__(self, initial_capital, charge_profile=None, include_charges=True):
        self.current_capital = initial_capital
        self.charge_profile = charge_profile
        self.include_charges = include_charges
        
        # State storage (in-memory, no DB)
        self.positions = {}  # instrument_id -> position dict
        self.pending_orders = []  # Pending orders for next candle execution
        self.closed_trades = []  # completed fill records, retained after positions are removed
    
    # Unified cache interface methods
    def get_position(self, instrument_id):
        return self.positions.get(instrument_id)
    
    def update_position(self, instrument_id, position_data):
        self.positions[instrument_id] = position_data
    
    def remove_position(self, instrument_id):
        self.positions.pop(instrument_id, None)
    
    def get_available_capital(self):
        invested = sum(float(position.get("capital_used", 0.0)) for position in self.positions.values())
        return max(self.current_capital - invested, 0.0)
    
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
