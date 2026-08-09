"""
Backtesting Models

Handles backtest runs, trades, metrics, equity curves,
optimization, and Monte Carlo simulations.
"""
from django.db import models
from django.conf import settings
from common.models import BaseTimestampModel
from common.enums import BacktestStatus, Side, CandleTimeframe


class BacktestRun(BaseTimestampModel):
    """
    A single backtest execution run.
    """
    strategy = models.ForeignKey(
        'strategies.Strategy',
        on_delete=models.CASCADE,
        related_name='backtest_runs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='backtest_runs'
    )
    
    name = models.CharField(max_length=200)
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Configuration
    strategy_version = models.ForeignKey(
        'strategies.StrategyVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backtest_runs',
        help_text="The specific strategy version used for this backtest."
    )
    initial_capital = models.DecimalField(max_digits=15, decimal_places=2, default=100000)
    slippage_pct = models.DecimalField(max_digits=5, decimal_places=4, default=0.01)
    brokerage_per_trade = models.DecimalField(max_digits=8, decimal_places=2, default=20)
    brokerage_pct = models.DecimalField(max_digits=5, decimal_places=4, default=0.0003)
    fill_model = models.CharField(
        max_length=20,
        choices=[
            ('SIGNAL_CLOSE', 'Signal Close'),
            ('NEXT_OPEN', 'Next Open'),
            ('VWAP', 'VWAP'),
        ],
        default='NEXT_OPEN',
        help_text='Fill price model: SIGNAL_CLOSE (optimistic), NEXT_OPEN (realistic), VWAP (conservative)'
    )
    charge_profile = models.ForeignKey(
        'brokers.BrokerChargeProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='backtest_runs',
        help_text='Charge profile for realistic cost simulation'
    )
    include_charges = models.BooleanField(
        default=True,
        help_text='Whether to include realistic charges (STT, stamp duty, etc.) in PnL'
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Strategy parameters used for this run."
    )
    # Execution settings (JSON for flexibility)
    config_snapshot = models.JSONField(default=dict, blank=True)
    risk_profile_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of the user's risk profile at the time of the run."
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=BacktestStatus.choices,
        default=BacktestStatus.PENDING
    )
    progress_pct = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'backtest_run'
        verbose_name = 'Backtest Run'
        verbose_name_plural = 'Backtest Runs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.status})"


class BacktestTrade(BaseTimestampModel):
    """
    Individual trade executed during a backtest.
    """
    run = models.ForeignKey(
        BacktestRun,
        on_delete=models.CASCADE,
        related_name='trades'
    )
    instrument = models.ForeignKey(
        'instruments.Instrument',
        on_delete=models.SET_NULL,
        null=True,
        related_name='backtest_trades'
    )
    
    # Trade details
    side = models.CharField(max_length=10, choices=Side.choices)
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField(null=True, blank=True)
    entry_price = models.DecimalField(max_digits=12, decimal_places=4)
    exit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    
    # P&L
    gross_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    brokerage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    slippage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    charges_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='Itemized charge breakdown: {entry_charges: {...}, exit_charges: {...}, total_charges: N}'
    )
    pnl_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    
    # Risk Metrics
    mae = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        help_text="Maximum Adverse Excursion (Max paper loss during trade)"
    )
    mfe = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        help_text="Maximum Favorable Excursion (Max paper profit during trade)"
    )
    
    # Duration
    holding_duration_minutes = models.PositiveIntegerField(default=0)
    
    # Context
    exit_reason = models.CharField(max_length=50, blank=True)
    entry_rule = models.CharField(max_length=100, blank=True)
    exit_rule = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'backtest_trade'
        verbose_name = 'Backtest Trade'
        verbose_name_plural = 'Backtest Trades'
        ordering = ['entry_time']

    def __str__(self):
        return f"{self.side} {self.instrument} @ {self.entry_price}"


class BacktestMetrics(BaseTimestampModel):
    """
    Computed metrics for a backtest run.
    """
    run = models.OneToOneField(
        BacktestRun,
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    
    # Trade counts
    total_trades = models.PositiveIntegerField(default=0)
    winning_trades = models.PositiveIntegerField(default=0)
    losing_trades = models.PositiveIntegerField(default=0)
    breakeven_trades = models.PositiveIntegerField(default=0)
    max_consecutive_wins = models.PositiveIntegerField(default=0)
    max_consecutive_losses = models.PositiveIntegerField(default=0)
    
    # Win rate
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # P&L stats
    avg_win = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_loss = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    largest_win = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    largest_loss = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_trade_pnl = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Duration
    avg_holding_time_minutes = models.PositiveIntegerField(default=0)
    avg_winning_hold_time = models.PositiveIntegerField(default=0)
    avg_losing_hold_time = models.PositiveIntegerField(default=0)
    
    # Risk metrics
    profit_factor = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    expectancy = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    payoff_ratio = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Risk-adjusted returns
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    sortino_ratio = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    calmar_ratio = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Drawdown
    max_drawdown_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    max_drawdown_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_drawdown_duration_days = models.PositiveIntegerField(default=0)
    recovery_factor = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Capital
    final_capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_return_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    cagr = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    volatility_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Fees
    total_brokerage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_slippage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_mae = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    avg_mfe = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    trade_efficiency = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    monthly_returns_json = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'backtest_metrics'
        verbose_name = 'Backtest Metrics'
        verbose_name_plural = 'Backtest Metrics'

    def __str__(self):
        return f"Metrics for {self.run.name}"


class EquityCurvePoint(models.Model):
    """
    Point-in-time equity value for charting.
    """
    run = models.ForeignKey(
        BacktestRun,
        on_delete=models.CASCADE,
        related_name='equity_curve'
    )
    
    timestamp = models.DateTimeField()
    equity_value = models.DecimalField(max_digits=15, decimal_places=2)
    drawdown_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    
    class Meta:
        db_table = 'backtest_equity_curve'
        verbose_name = 'Equity Curve Point'
        verbose_name_plural = 'Equity Curve Points'
        ordering = ['timestamp']
        unique_together = ['run', 'timestamp']


class MonteCarloRun(BaseTimestampModel):
    """
    Monte Carlo simulation run.
    """
    backtest_run = models.ForeignKey(
        BacktestRun,
        on_delete=models.CASCADE,
        related_name='monte_carlo_runs'
    )
    
    num_simulations = models.PositiveIntegerField(default=1000)
    confidence_level = models.DecimalField(max_digits=4, decimal_places=2, default=0.95)
    
    status = models.CharField(
        max_length=20,
        choices=BacktestStatus.choices,
        default=BacktestStatus.PENDING
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    equity_distribution_json = models.JSONField(
        default=list, blank=True,
        help_text='Percentile-based equity distribution for histogram rendering.'
    )
    
    class Meta:
        db_table = 'backtest_monte_carlo_run'
        verbose_name = 'Monte Carlo Run'
        verbose_name_plural = 'Monte Carlo Runs'

    def __str__(self):
        return f"Monte Carlo: {self.num_simulations} sims"


class MonteCarloResult(models.Model):
    """
    Results from Monte Carlo simulation.
    """
    monte_carlo_run = models.ForeignKey(
        MonteCarloRun,
        on_delete=models.CASCADE,
        related_name='results'
    )
    
    metric_name = models.CharField(max_length=50)
    mean_value = models.DecimalField(max_digits=15, decimal_places=6)
    median_value = models.DecimalField(max_digits=15, decimal_places=6)
    std_dev = models.DecimalField(max_digits=15, decimal_places=6)
    percentile_5 = models.DecimalField(max_digits=15, decimal_places=6)
    percentile_95 = models.DecimalField(max_digits=15, decimal_places=6)
    worst_case = models.DecimalField(max_digits=15, decimal_places=6)
    best_case = models.DecimalField(max_digits=15, decimal_places=6)
    
    class Meta:
        db_table = 'backtest_monte_carlo_result'
        verbose_name = 'Monte Carlo Result'
        verbose_name_plural = 'Monte Carlo Results'

    def __str__(self):
        return f"{self.metric_name}: {self.mean_value}"
