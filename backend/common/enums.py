"""
Common app - shared enums, base models, and utilities for QuantNest Algo Trading Platform.
"""
from django.db import models

class Timezone(models.TextChoices):
    """Supported timezones for trading rules."""
    ASIA_KOLKATA = 'Asia/Kolkata', 'Asia/Kolkata (IST)'
    UTC = 'UTC', 'UTC'
    AMERICA_NEW_YORK = 'America/New_York', 'America/New_York (EST/EDT)'
    EUROPE_LONDON = 'Europe/London', 'Europe/London (GMT/BST)'
    ASIA_TOKYO = 'Asia/Tokyo', 'Asia/Tokyo (JST)'
    AUSTRALIA_SYDNEY = 'Australia/Sydney', 'Australia/Sydney (AEST/AEDT)'


class StrategyType(models.TextChoices):
    """Type of trading strategy based on holding period."""
    INTRADAY = 'INTRADAY', 'Intraday'
    POSITIONAL = 'POSITIONAL', 'Positional'
    SWING = 'SWING', 'Swing'
    SCALPING = 'SCALPING', 'Scalping'


class MarketType(models.TextChoices):
    """Type of market/asset class."""
    EQUITY = 'EQUITY', 'Equity'
    FUTURES = 'FUTURES', 'Futures'
    OPTIONS = 'OPTIONS', 'Options'
    FOREX = 'FOREX', 'Forex'
    CRYPTO = 'CRYPTO', 'Crypto'


class Exchange(models.TextChoices):
    """Supported exchanges."""
    NSE = 'NSE', 'National Stock Exchange'
    BSE = 'BSE', 'Bombay Stock Exchange'
    MCX = 'MCX', 'Multi Commodity Exchange'
    BINANCE = 'BINANCE', 'Binance'
    BYBIT = 'BYBIT', 'Bybit'


class InstrumentType(models.TextChoices):
    """Type of trading instrument."""
    STOCK = 'STOCK', 'Stock'
    INDEX = 'INDEX', 'Index'
    FUTURE = 'FUTURE', 'Future'
    OPTION = 'OPTION', 'Option Contract'
    CURRENCY = 'CURRENCY', 'Currency Pair'
    COMMODITY = 'COMMODITY', 'Commodity'
    ETF = 'ETF', 'Exchange Traded Fund'
    BOND = 'BOND', 'Bond / Govt Securities'
    MF = 'MF', 'Mutual Fund'


class OptionType(models.TextChoices):
    """Option contract type."""
    CE = 'CE', 'Call Option'
    PE = 'PE', 'Put Option'


class OrderType(models.TextChoices):
    """Order type for execution."""
    MARKET = 'MARKET', 'Market Order'
    LIMIT = 'LIMIT', 'Limit Order'
    STOP_LIMIT = 'STOP_LIMIT', 'Stop Limit Order'
    STOP_MARKET = 'STOP_MARKET', 'Stop Market Order'


class OrderStatus(models.TextChoices):
    """Order execution status."""
    PENDING = 'PENDING', 'Pending'
    PLACED = 'PLACED', 'Placed'
    PARTIAL_FILL = 'PARTIAL_FILL', 'Partially Filled'
    FILLED = 'FILLED', 'Filled'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'
    EXPIRED = 'EXPIRED', 'Expired'


class Side(models.TextChoices):
    """Trade side/direction."""
    BUY = 'BUY', 'Buy'
    SELL = 'SELL', 'Sell'


class ProductType(models.TextChoices):
    """Broker product type (aligned with Fyers API)."""
    CNC = 'CNC', 'Cash and Carry (Equity delivery)'
    INTRADAY = 'INTRADAY', 'Intraday (All segments)'
    MARGIN = 'MARGIN', 'Margin (Derivatives only)'
    CO = 'CO', 'Cover Order'
    BO = 'BO', 'Bracket Order'
    MTF = 'MTF', 'Margin Trading Facility'


class StrategyStatus(models.TextChoices):
    """Strategy lifecycle status."""
    DRAFT = 'DRAFT', 'Draft'
    ACTIVE = 'ACTIVE', 'Active'
    ARCHIVED = 'ARCHIVED', 'Archived'


class StrategyVisibility(models.TextChoices):
    """Strategy visibility level."""
    PRIVATE = 'PRIVATE', 'Private'
    PUBLIC = 'PUBLIC', 'Public'
    MARKETPLACE = 'MARKETPLACE', 'Marketplace'


class CandleTimeframe(models.TextChoices):
    """Candle/chart timeframes."""
    M1 = '1m', '1 Minute'
    M3 = '3m', '3 Minutes'
    M5 = '5m', '5 Minutes'
    M15 = '15m', '15 Minutes'
    M30 = '30m', '30 Minutes'
    H1 = '1H', '1 Hour'
    H4 = '4H', '4 Hours'
    D1 = '1D', '1 Day'
    W1 = '1W', '1 Week'


class CandleCompletionRule(models.TextChoices):
    """When to evaluate candle-based rules."""
    ON_CLOSE = 'ON_CLOSE', 'On Candle Close'
    ON_OPEN = 'ON_OPEN', 'On Candle Open'
    REAL_TIME = 'REAL_TIME', 'Real-time Tick'


class CandlePart(models.TextChoices):
    """Part of the candle to use as reference."""
    OPEN = 'OPEN', 'Open'
    HIGH = 'HIGH', 'High'
    LOW = 'LOW', 'Low'
    CLOSE = 'CLOSE', 'Close'


class CandlePatternType(models.TextChoices):
    """Candlestick patterns for entry rules."""
    DOJI = 'DOJI', 'Doji'
    HAMMER = 'HAMMER', 'Hammer'
    SHOOTING_STAR = 'SHOOTING_STAR', 'Shooting Star'
    ENGULFING_BULLISH = 'ENGULFING_BULLISH', 'Bullish Engulfing'
    ENGULFING_BEARISH = 'ENGULFING_BEARISH', 'Bearish Engulfing'
    MORNING_STAR = 'MORNING_STAR', 'Morning Star'
    EVENING_STAR = 'EVENING_STAR', 'Evening Star'
    MARUBOZU = 'MARUBOZU', 'Marubozu'
    HARAMI_BULLISH = 'HARAMI_BULLISH', 'Bullish Harami'
    HARAMI_BEARISH = 'HARAMI_BEARISH', 'Bearish Harami'
    PIERCING_LINE = 'PIERCING_LINE', 'Piercing Line'


class MarketSession(models.TextChoices):
    """Market session filter."""
    PRE_MARKET = 'PRE_MARKET', 'Pre-Market'
    MARKET_OPEN = 'MARKET_OPEN', 'Market Open'
    MARKET_CLOSE = 'MARKET_CLOSE', 'Market Close'
    ALL = 'ALL', 'All Sessions'


class LogicalOperator(models.TextChoices):
    """Logical operator for rule groups."""
    AND = 'AND', 'AND'
    OR = 'OR', 'OR'


class RuleType(models.TextChoices):
    """Type of trading rule."""
    ENTRY = 'ENTRY', 'Entry Rule'
    EXIT = 'EXIT', 'Exit Rule'
    STOP_LOSS = 'STOP_LOSS', 'Stop Loss Rule'
    TARGET = 'TARGET', 'Target Rule'


class OperandType(models.TextChoices):
    """Universal operands for rules (Data, Indicators, State, Math)."""
    # Price Data
    LTP = 'LTP', 'Last Traded Price'
    OPEN = 'OPEN', 'Open Price'
    HIGH = 'HIGH', 'High Price'
    LOW = 'LOW', 'Low Price'
    CLOSE = 'CLOSE', 'Close Price'
    VOLUME = 'VOLUME', 'Volume'
    VWAP = 'VWAP', 'Volume Weighted Average Price'
    HL2 = 'HL2', 'HL2'
    HLC3 = 'HLC3', 'HLC3'
    OHLC4 = 'OHLC4', 'OHLC4'
    CURRENT_DAY_OPEN = 'CURRENT_DAY_OPEN', 'Current Day Open'
    PREV_WEEK_HIGH = 'PREV_WEEK_HIGH', 'Previous Week High'
    PREV_WEEK_LOW = 'PREV_WEEK_LOW', 'Previous Week Low'

    # Candle Analysis
    CANDLE_PATTERN = 'CANDLE_PATTERN', 'Candle Pattern'
    CANDLE_BODY_SIZE = 'CANDLE_BODY_SIZE', 'Candle Body Size'

    # Technical Indicators
    SMA = 'SMA', 'Simple Moving Average'
    EMA = 'EMA', 'Exponential Moving Average'
    WMA = 'WMA', 'Weighted Moving Average'
    HMA = 'HMA', 'Hull Moving Average'
    ALMA = 'ALMA', 'Arnaud Legoux Moving Average'
    KAMA = 'KAMA', 'Kaufman Adaptive Moving Average'
    DEMA = 'DEMA', 'Double Exponential Moving Average'
    TEMA = 'TEMA', 'Triple Exponential Moving Average'
    RSI = 'RSI', 'Relative Strength Index'
    ROC = 'ROC', 'Rate of Change'
    MACD = 'MACD', 'MACD'
    BOLLINGER_BANDS = 'BOLLINGER_BANDS', 'Bollinger Bands'
    SUPERTREND = 'SUPERTREND', 'SuperTrend'
    ADX = 'ADX', 'Average Directional Index'
    DMI = 'DMI', 'Directional Movement Index'
    STOCHASTIC = 'STOCHASTIC', 'Stochastic'
    ATR = 'ATR', 'Average True Range'
    CCI = 'CCI', 'Commodity Channel Index'
    WILLIAMS_R = 'WILLIAMS_R', 'Williams %R'
    OBV = 'OBV', 'On Balance Volume'
    MFI = 'MFI', 'Money Flow Index'
    PIVOT_POINT = 'PIVOT_POINT', 'Pivot Point'
    KELTNER_CHANNEL = 'KELTNER_CHANNEL', 'Keltner Channel'
    DONCHIAN_CHANNEL = 'DONCHIAN_CHANNEL', 'Donchian Channel'
    PARABOLIC_SAR = 'PARABOLIC_SAR', 'Parabolic SAR'
    ICHIMOKU_CLOUD = 'ICHIMOKU_CLOUD', 'Ichimoku Cloud'


    # Position State (For Exit Rules)
    POSITION_PNL_PERCENTAGE = 'POSITION_PNL_PERCENTAGE', 'Position PnL %'
    POSITION_PNL_POINTS = 'POSITION_PNL_POINTS', 'Position PnL Points'
    TRAILING_PEAK_OFFSET = 'TRAILING_PEAK_OFFSET', 'Trailing Peak Offset'
    ENTRY_PRICE = 'ENTRY_PRICE', 'Entry Price'
    TIME_DECAY = 'TIME_DECAY', 'Time Decay Exit'

    # Math/Constant
    CONSTANT = 'CONSTANT', 'Constant Value'
    MATH_EXPRESSION = 'MATH_EXPRESSION', 'Math Expression'
class ComparisonOperator(models.TextChoices):
    """Comparison operators for rules."""
    GREATER = 'GT', 'Greater Than'
    LESS = 'LT', 'Less Than'
    EQUAL = 'EQ', 'Equal To'
    GREATER_EQUAL = 'GTE', 'Greater Than or Equal'
    LESS_EQUAL = 'LTE', 'Less Than or Equal'
    CROSSES_ABOVE = 'CROSSES_ABOVE', 'Crosses Above'
    CROSSES_BELOW = 'CROSSES_BELOW', 'Crosses Below'


class QuantityType(models.TextChoices):
    """Position sizing method."""
    FIXED = 'FIXED', 'Fixed Quantity'
    CAPITAL_BASED = 'CAPITAL_BASED', 'Capital Based'
    RISK_FIXED = 'RISK_FIXED', 'Risk Based (Fixed Amount)'
    RISK_PERCENTAGE = 'RISK_PERCENTAGE', 'Risk Based (% of Capital)'
    VOLATILITY_ADJUSTED = 'VOLATILITY_ADJUSTED', 'Volatility Adjusted (ATR)'


class ExecutionStyle(models.TextChoices):
    """Unified entry execution logic."""
    LTP = 'LTP', 'Market (Instant)'
    MARKET_AT_CLOSE = 'MARKET_AT_CLOSE', 'Market at Close'
    LIMIT_OFFSET = 'LIMIT_OFFSET', 'Limit with Offset'
    STOP_BREAKOUT = 'STOP_BREAKOUT', 'Stop at Breakout'
    AT_OPEN = 'AT_OPEN', 'Market at Next Open'


class CapitalAllocationType(models.TextChoices):
    """Capital allocation method."""
    PERCENTAGE = 'PERCENTAGE', 'Percentage of Capital'
    FIXED = 'FIXED', 'Fixed Amount'


class StrikeSelectionLogic(models.TextChoices):
    """Option strike selection logic."""
    ATM = 'ATM', 'At The Money'
    ITM_1 = 'ITM_1', 'ITM 1 Strike'
    ITM_2 = 'ITM_2', 'ITM 2 Strikes'
    ITM_3 = 'ITM_3', 'ITM 3 Strikes'
    OTM_1 = 'OTM_1', 'OTM 1 Strike'
    OTM_2 = 'OTM_2', 'OTM 2 Strikes'
    OTM_3 = 'OTM_3', 'OTM 3 Strikes'


class ExpiryType(models.TextChoices):
    """Option expiry selection."""
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'
    NEAREST = 'NEAREST', 'Nearest Expiry'


class BrokerName(models.TextChoices):
    """Supported brokers."""
    ZERODHA = 'ZERODHA', 'Zerodha'
    ANGEL = 'ANGEL', 'Angel Broking'
    FYERS = 'FYERS', 'Fyers'
    UPSTOX = 'UPSTOX', 'Upstox'
    IIFL = 'IIFL', 'IIFL Securities'
    ICICI = 'ICICI', 'ICICI Direct'
    HDFC = 'HDFC', 'HDFC Securities'


class NotificationType(models.TextChoices):
    """Notification event types."""
    TRADE_EXECUTED = 'TRADE_EXECUTED', 'Trade Executed'
    SL_HIT = 'SL_HIT', 'Stop Loss Hit'
    TARGET_HIT = 'TARGET_HIT', 'Target Hit'
    STRATEGY_PAUSED = 'STRATEGY_PAUSED', 'Strategy Paused'
    STRATEGY_ERROR = 'STRATEGY_ERROR', 'Strategy Error'
    RISK_ALERT = 'RISK_ALERT', 'Risk Alert'
    DAILY_SUMMARY = 'DAILY_SUMMARY', 'Daily Summary'
    COMMUNITY_REPLY = 'COMMUNITY_REPLY', 'Community Reply'
    COMMUNITY_MENTION = 'COMMUNITY_MENTION', 'Community Mention'
    COMMUNITY_FOLLOW = 'COMMUNITY_FOLLOW', 'Community Follow'
    BADGE_UNLOCKED = 'BADGE_UNLOCKED', 'Badge Unlocked'
    STREAK_WARNING = 'STREAK_WARNING', 'Streak Warning'
    CHALLENGE_PROGRESS = 'CHALLENGE_PROGRESS', 'Challenge Progress'
    CERTIFICATE_ISSUED = 'CERTIFICATE_ISSUED', 'Certificate Issued'
    PROOF_VERIFIED = 'PROOF_VERIFIED', 'Proof Verified'
    MODERATION_ALERT = 'MODERATION_ALERT', 'Moderation Alert'


class EntryPriceLogic(models.TextChoices):
    """Entry price logic for order placement."""
    LTP = 'LTP', 'Last Traded Price (Instant)'
    AT_CLOSE = 'AT_CLOSE', 'At Close'
    AT_OPEN = 'AT_OPEN', 'At Next Open'
    ABOVE_HIGH = 'ABOVE_HIGH', 'Above High'
    BELOW_LOW = 'BELOW_LOW', 'Below Low'
    AT_BREAKOUT = 'AT_BREAKOUT', 'At Breakout'
    OFFSET = 'OFFSET', 'Limit with Offset'


class AutoDisableTriggerType(models.TextChoices):
    """Trigger types for strategy auto-disable."""
    CONSECUTIVE_LOSSES = 'CONSECUTIVE_LOSSES', 'Consecutive Losses'
    CONSECUTIVE_WINS = 'CONSECUTIVE_WINS', 'Consecutive Wins'
    DAILY_LOSS = 'DAILY_LOSS', 'Daily Loss Threshold'
    WEEKLY_LOSS = 'WEEKLY_LOSS', 'Weekly Loss Threshold'
    MONTHLY_LOSS = 'MONTHLY_LOSS', 'Monthly Loss Threshold'
    WIN_RATE_DROP = 'WIN_RATE_DROP', 'Win Rate Below Threshold'
    DRAWDOWN = 'DRAWDOWN', 'Drawdown Exceeded'


class ViolationType(models.TextChoices):
    """Risk violation types."""
    POSITION_SIZE = 'POSITION_SIZE', 'Position Size Exceeded'
    DAILY_LOSS = 'DAILY_LOSS', 'Daily Loss Limit'
    EXPOSURE = 'EXPOSURE', 'Exposure Limit'
    DRAWDOWN = 'DRAWDOWN', 'Drawdown Limit'
    CONSECUTIVE_LOSS = 'CONSECUTIVE_LOSS', 'Consecutive Losses'
    MAX_TRADES = 'MAX_TRADES', 'Max Trades Reached'
    HALT_TRIGGERED = 'HALT_TRIGGERED', 'Trading Halt Triggered'


class ViolationAction(models.TextChoices):
    """Actions taken on risk violations."""
    LOGGED = 'LOGGED', 'Logged Only'
    NOTIFIED = 'NOTIFIED', 'Notification Sent'
    BLOCKED = 'BLOCKED', 'Trade Blocked'
    HALTED = 'HALTED', 'Trading Halted'
    CLOSED = 'CLOSED', 'Positions Closed'
    DISABLED = 'DISABLED', 'Strategy Disabled'


class Severity(models.TextChoices):
    """Alert/notification severity."""
    INFO = 'INFO', 'Info'
    WARNING = 'WARNING', 'Warning'
    CRITICAL = 'CRITICAL', 'Critical'


class TransactionType(models.TextChoices):
    """Fund transaction types for portfolio."""
    DEPOSIT = 'DEPOSIT', 'Deposit'
    WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'
    ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'
    BROKER_TRANSFER_IN = 'BROKER_TRANSFER_IN', 'Transfer from Broker'
    BROKER_TRANSFER_OUT = 'BROKER_TRANSFER_OUT', 'Transfer to Broker'
    PROFIT_BOOKING = 'PROFIT_BOOKING', 'Profit Booking'
    LOSS_SETTLEMENT = 'LOSS_SETTLEMENT', 'Loss Settlement'
    ALLOCATION = 'ALLOCATION', 'Strategy Allocation'
    DEALLOCATION = 'DEALLOCATION', 'Strategy De-allocation'


class RebalanceFrequency(models.TextChoices):
    """Rebalance frequency for capital allocations."""
    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'


class BacktestStatus(models.TextChoices):
    """Backtest run status."""
    PENDING = 'PENDING', 'Pending'
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    CANCELLED = 'CANCELLED', 'Cancelled'


# ── Fyers-specific enums (integer-based for API communication) ──


class FyersSegment(models.IntegerChoices):
    """Fyers market segment codes."""
    CAPITAL_MARKET = 10, 'Capital Market'
    EQUITY_DERIVATIVES = 11, 'Equity Derivatives'
    CURRENCY_DERIVATIVES = 12, 'Currency Derivatives'
    COMMODITY_DERIVATIVES = 20, 'Commodity Derivatives'


class FyersOrderType(models.IntegerChoices):
    """Fyers order type codes."""
    LIMIT = 1, 'Limit Order'
    MARKET = 2, 'Market Order'
    STOP_MARKET = 3, 'Stop Order (SL-M)'
    STOP_LIMIT = 4, 'Stop Limit Order (SL-L)'


class FyersOrderStatus(models.IntegerChoices):
    """Fyers order status codes."""
    CANCELLED = 1, 'Cancelled'
    FILLED = 2, 'Traded / Filled'
    TRANSIT = 4, 'Transit'
    REJECTED = 5, 'Rejected'
    PENDING = 6, 'Pending'


class FyersOrderSide(models.IntegerChoices):
    """Fyers order side codes."""
    BUY = 1, 'Buy'
    SELL = -1, 'Sell'


class FyersPositionSide(models.IntegerChoices):
    """Fyers position side codes."""
    LONG = 1, 'Long'
    SHORT = -1, 'Short'
    CLOSED = 0, 'Closed'


class ExchangeInstrumentType(models.IntegerChoices):
    """Fyers exchange instrument type (exInstType) codes."""
    # ── CM Segment ──
    EQ = 0, 'EQ (Equity)'
    PREFSHARES = 1, 'Preference Shares'
    DEBENTURES = 2, 'Debentures'
    WARRANTS = 3, 'Warrants'
    MISC_NSE = 4, 'Misc (NSE/BSE)'
    SGB = 5, 'Sovereign Gold Bond'
    G_SECS = 6, 'Government Securities'
    T_BILLS = 7, 'Treasury Bills'
    MF = 8, 'Mutual Fund'
    ETF = 9, 'Exchange Traded Fund'
    INDEX = 10, 'Index'
    # ── FO Segment ──
    FUTIDX = 11, 'Index Futures'
    FUTIVX = 12, 'VIX Futures'
    FUTSTK = 13, 'Stock Futures'
    OPTIDX = 14, 'Index Options'
    OPTSTK = 15, 'Stock Options'
    # ── CD Segment ──
    FUTCUR = 16, 'Currency Futures'
    FUTIRT = 17, 'Interest Rate Futures (T)'
    FUTIRC = 18, 'Interest Rate Futures (C)'
    OPTCUR = 19, 'Currency Options'
    UNDCUR = 20, 'Underlying Currency'
    UNDIRC = 21, 'Underlying IRC'
    UNDIRT = 22, 'Underlying IRT'
    UNDIRD = 23, 'Underlying IRD'
    INDEX_CD = 24, 'Currency Index'
    FUTIRD = 25, 'Interest Rate Futures (D)'
    # ── COM Segment ──
    FUTCOM = 30, 'Commodity Futures'
    OPTFUT = 31, 'Options on Futures'
    OPTCOM = 32, 'Commodity Options'
    FUTBAS = 33, 'Basis Futures'
    FUTBLN = 34, 'Bullion Futures'
    FUTENR = 35, 'Energy Futures'
    OPTBLN = 36, 'Bullion Options'
    OPTFUT_NCOM = 37, 'Options on Futures (NCOM)'
    # ── BSE-specific ──
    MISC_BSE = 50, 'Misc (BSE)'

