"""Minimal in-memory state for a single backtest run."""
from collections import Counter

class BacktestContext:
    """
    In-memory context for backtest execution.
    Holds positions and orders in memory for one backtest run.
    """
    def __init__(self, initial_capital, charge_profile=None, include_charges=True, strategy_config=None):
        self.initial_capital = float(initial_capital)
        self.strategy_config = strategy_config
        self.risk_stats = {"total_closed_trades": 0, "risk_capital": self.initial_capital}
        self.auto_disable_state = {}
        self.current_capital = initial_capital
        self.charge_profile = charge_profile
        self.include_charges = include_charges
        
        # State storage (in-memory, no DB)
        self.positions = {}  # instrument_id -> position dict
        self.pending_orders = []  # Pending orders for next candle execution
        self.closed_trades = []  # completed fill records, retained after positions are removed
        self.diagnostics = Counter({key: 0 for key in (
            "entry_signals", "time_event_restrictions", "cooldown_restrictions", "existing_positions",
            "sizing_rejections", "capital_rejections", "route_rejections", "queued_entries", "entry_fills",
            "auto_disable_restrictions", "auto_disable_pauses")})

    def record_risk_close(self, pnl, timestamp):
        from risk_management.metrics import record_close
        self.risk_stats = record_close(self.risk_stats, pnl, timestamp, self.initial_capital,
                                      self.strategy_config["time_rule"].get("timezone", "Asia/Kolkata"))

    def can_enter(self, timestamp):
        from risk_management.policy import evaluate_configuration, pause_state, release_state, cooldown_elapsed
        if self.auto_disable_state.get("paused_at"):
            if not cooldown_elapsed(self.auto_disable_state, timestamp):
                return False
            self.auto_disable_state = release_state(self.auto_disable_state, self.risk_stats)
        evaluation = evaluate_configuration(self.strategy_config, self.risk_stats, self.initial_capital,
                                            timestamp, self.auto_disable_state.get("release"))
        if evaluation["should_disable"]:
            self.auto_disable_state = pause_state(evaluation, timestamp)
            self.diagnostics["auto_disable_pauses"] += 1
            return False
        return True
    
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
