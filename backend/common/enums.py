"""Shared choices and rule-operand metadata used by the backend and frontend."""
from datetime import time

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


class Exchange(models.TextChoices):
    """Supported exchanges."""
    NSE = 'NSE', 'National Stock Exchange'
    BSE = 'BSE', 'Bombay Stock Exchange'
    MCX = 'MCX', 'Multi Commodity Exchange'


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


class ExecutionScope(models.TextChoices):
    PAPER = 'paper', 'Paper'
    LIVE = 'live', 'Live'


class ExecutionCommandType(models.TextChoices):
    REFRESH = 'REFRESH', 'Apply session or account configuration'
    ORDER = 'ORDER', 'Place order'
    CANCEL = 'CANCEL', 'Cancel order'
    AMEND = 'AMEND', 'Amend order'
    PROTECT = 'PROTECT', 'Change position protection'
    CLOSE = 'CLOSE', 'Close position'
    BALANCE = 'BALANCE', 'Adjust account capital'
    BROKER = 'BROKER', 'Apply broker order observation'
    FUNDS = 'FUNDS', 'Refresh broker available capital'
    SETTLE = 'SETTLE', 'Settle an expired simulated contract'


class ExecutionMode(models.TextChoices):
    """Adapters supported by the common execution kernel."""
    BACKTEST = 'backtest', 'Backtest'
    PAPER = 'paper', 'Paper'
    LIVE = 'live', 'Live'
    TERMINAL = 'terminal', 'Terminal'


class OrderIntent(models.TextChoices):
    ENTRY = 'ENTRY', 'Entry'
    EXIT = 'EXIT', 'Exit'


class TerminalOrderType(models.TextChoices):
    MARKET = 'MARKET', 'Market'
    LIMIT = 'LIMIT', 'Limit'
    STOP = 'STOP', 'Stop market'
    STOP_LIMIT = 'STOP_LIMIT', 'Stop limit'
    SETTLEMENT = 'SETTLEMENT', 'Manual simulation settlement'


TERMINAL_USER_ORDER_TYPES = tuple(kind for kind in TerminalOrderType if kind != TerminalOrderType.SETTLEMENT)
TERMINAL_PRICE_REQUIRED_TYPES = frozenset((TerminalOrderType.LIMIT, TerminalOrderType.STOP_LIMIT))
TERMINAL_TRIGGER_REQUIRED_TYPES = frozenset((TerminalOrderType.STOP, TerminalOrderType.STOP_LIMIT))


class TerminalOrderStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    COMPLETE = 'COMPLETE', 'Complete'
    CANCELLED = 'CANCELLED', 'Cancelled'
    REJECTED = 'REJECTED', 'Rejected'


class PositionSide(models.TextChoices):
    LONG = 'LONG', 'Long'
    SHORT = 'SHORT', 'Short'


class TerminalPositionAction(models.TextChoices):
    REDUCE = 'REDUCE', 'Reduce position'
    INCREASE = 'INCREASE', 'Increase position'
    CLOSE = 'CLOSE', 'Close remaining position'
    REVERSE = 'REVERSE', 'Reverse position'
    SETTLE = 'SETTLE', 'Settle expired contract'


class TerminalExitReason(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    STOP_LOSS = 'stop_loss', 'Stop loss'
    TAKE_PROFIT = 'take_profit', 'Take profit'
    MANUAL_SETTLEMENT = 'manual_settlement', 'Manual settlement'


class ProductType(models.TextChoices):
    """Broker product type (aligned with Fyers API)."""
    CNC = 'CNC', 'Cash and Carry (Equity delivery)'
    INTRADAY = 'INTRADAY', 'Intraday (All segments)'
    MARGIN = 'MARGIN', 'Margin (Derivatives only)'
    CO = 'CO', 'Cover Order'
    BO = 'BO', 'Bracket Order'
    MTF = 'MTF', 'Margin Trading Facility'


class ExecutionSessionStatus(models.TextChoices):
    RUNNING = "RUNNING", "Running"
    PAUSED = "PAUSED", "Paused"
    STOPPING = "STOPPING", "Stopping"
    STOPPED = "STOPPED", "Stopped"
    ERROR = "ERROR", "Error"


class StrategyStatus(models.TextChoices):
    """Strategy lifecycle status."""
    DRAFT = 'DRAFT', 'Draft'
    ACTIVE = 'ACTIVE', 'Active'
    PAUSED = 'PAUSED', 'Paused'
    ARCHIVED = 'ARCHIVED', 'Archived'


class StrategyVisibility(models.TextChoices):
    """Strategy visibility level."""
    PRIVATE = 'PRIVATE', 'Private'
    PUBLIC = 'PUBLIC', 'Public'


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


class ChartTimeframe(models.TextChoices):
    M1 = '1m', '1 Minute'
    M3 = '3m', '3 Minutes'
    M5 = '5m', '5 Minutes'
    M10 = '10m', '10 Minutes'
    M15 = '15m', '15 Minutes'
    M30 = '30m', '30 Minutes'
    H1 = '1H', '1 Hour'
    H4 = '4H', '4 Hours'
    D1 = '1D', '1 Day'
    W1 = '1W', '1 Week'
    MN1 = '1M', '1 Month'


class TradingDay(models.TextChoices):
    MONDAY = 'Monday', 'Monday'
    TUESDAY = 'Tuesday', 'Tuesday'
    WEDNESDAY = 'Wednesday', 'Wednesday'
    THURSDAY = 'Thursday', 'Thursday'
    FRIDAY = 'Friday', 'Friday'
    SATURDAY = 'Saturday', 'Saturday'
    SUNDAY = 'Sunday', 'Sunday'


DEFAULT_TRADING_DAYS = [
    TradingDay.MONDAY, TradingDay.TUESDAY, TradingDay.WEDNESDAY,
    TradingDay.THURSDAY, TradingDay.FRIDAY,
]
DEFAULT_TRADING_START_TIME = time(9, 15)
DEFAULT_TRADING_END_TIME = time(15, 30)


def default_trading_days():
    return list(DEFAULT_TRADING_DAYS)


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
    MARKET_OPEN = 'MARKET_OPEN', 'Market Open'
    ALL = 'ALL', 'All trading sessions'


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
    POSITION_RR_RATIO = 'POSITION_RR_RATIO', 'Position Risk:Reward Ratio'

    # Math/Constant
    CONSTANT = 'CONSTANT', 'Constant Value'
    MATH_EXPRESSION = 'MATH_EXPRESSION', 'Math Expression'


# The parameter contract for strategy-builder operands. This is the source of
# truth for frontend defaults/options and backend validation/evaluation. Keep
# entries JSON-serializable because the common enum endpoint exposes them.
PRICE_SOURCE_CHOICES = [
    {'value': operand.value, 'label': operand.label, 'group': 'Price'}
    for operand in (
        OperandType.OPEN, OperandType.HIGH, OperandType.LOW, OperandType.CLOSE,
        OperandType.VOLUME, OperandType.HL2, OperandType.HLC3, OperandType.OHLC4
    )
]
INDICATOR_SOURCE_CHOICES = [
    {'value': operand.value, 'label': operand.label, 'group': 'Indicators'}
    for operand in OperandType
    if operand in {
        OperandType.SMA, OperandType.EMA, OperandType.WMA, OperandType.HMA,
        OperandType.ALMA, OperandType.KAMA, OperandType.DEMA, OperandType.TEMA,
        OperandType.RSI, OperandType.ROC, OperandType.MACD,
        OperandType.BOLLINGER_BANDS, OperandType.SUPERTREND, OperandType.ADX,
        OperandType.DMI, OperandType.STOCHASTIC, OperandType.ATR, OperandType.CCI,
        OperandType.WILLIAMS_R, OperandType.OBV, OperandType.MFI,
        OperandType.PIVOT_POINT, OperandType.KELTNER_CHANNEL,
        OperandType.DONCHIAN_CHANNEL, OperandType.PARABOLIC_SAR,
        OperandType.ICHIMOKU_CLOUD, OperandType.VWAP,
    }
]

def _number(key, label, default, minimum=1, maximum=None, step=1):
    return {
        'key': key, 'label': label, 'type': 'number', 'default': default,
        'min': minimum, 'max': maximum, 'step': step,
    }


def _select(key, label, options, default):
    return {'key': key, 'label': label, 'type': 'select', 'options': options, 'default': default}


_CHANNEL_OPTIONS = [
    {'value': 'UPPER', 'label': 'Upper'},
    {'value': 'MIDDLE', 'label': 'Middle'},
    {'value': 'LOWER', 'label': 'Lower'},
]
_ADX_OPTIONS = [
    {'value': 'ADX', 'label': 'ADX'},
    {'value': 'PLUS_DI', 'label': '+DI'},
    {'value': 'MINUS_DI', 'label': '-DI'},
]

OPERAND_PARAMETER_CONFIG = {
    OperandType.SMA: [_number('period', 'Period', 14), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.EMA: [_number('period', 'Period', 14), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.WMA: [_number('period', 'Period', 14), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.HMA: [_number('period', 'Period', 14), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.ALMA: [_number('period', 'Period', 14), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.KAMA: [_number('period', 'Period', 14), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.DEMA: [_number('period', 'Period', 14), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.TEMA: [_number('period', 'Period', 14), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.RSI: [_number('period', 'Period', 14), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.ROC: [_number('period', 'Period', 9), {'key': 'source', 'label': 'Source', 'type': 'source', 'default': OperandType.CLOSE.value, 'options': PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES}],
    OperandType.CCI: [_number('period', 'Period', 20)],
    OperandType.ADX: [_number('period', 'Period', 14), _select('output_line', 'Output', _ADX_OPTIONS, 'ADX')],
    OperandType.DMI: [_number('period', 'Period', 14), _select('output_line', 'Output', _ADX_OPTIONS, 'ADX')],
    OperandType.MACD: [_number('fast_period', 'Fast', 12), _number('slow_period', 'Slow', 26), _number('signal_period', 'Signal', 9), _select('output_line', 'Output', [
        {'value': 'MACD_LINE', 'label': 'MACD Line'}, {'value': 'MACD_SIGNAL', 'label': 'Signal'}, {'value': 'MACD_HISTOGRAM', 'label': 'Histogram'},
    ], 'MACD_LINE')],
    OperandType.BOLLINGER_BANDS: [_number('period', 'Period', 20), _number('std_dev', 'StdDev', 2, step=0.1), _select('output_line', 'Output Line', _CHANNEL_OPTIONS, 'UPPER')],
    OperandType.KELTNER_CHANNEL: [_number('period', 'Period', 20), _number('multiplier', 'Multiplier', 2, step=0.1), _select('output_line', 'Output Line', _CHANNEL_OPTIONS, 'UPPER')],
    OperandType.DONCHIAN_CHANNEL: [_number('period', 'Period', 20), _select('output_line', 'Output Line', _CHANNEL_OPTIONS, 'UPPER')],
    OperandType.STOCHASTIC: [_number('k_period', '%K', 14), _number('d_period', '%D', 3), _number('smooth', 'Smooth', 3), _select('output_line', 'Output Line', [{'value': 'K', 'label': '%K'}, {'value': 'D', 'label': '%D'}], 'K')],
    OperandType.SUPERTREND: [_number('period', 'Period', 7), _number('multiplier', 'Multiplier', 3, step=0.1)],
    OperandType.ATR: [_number('period', 'Period', 14)],
    OperandType.MFI: [_number('period', 'Period', 14)],
    OperandType.WILLIAMS_R: [_number('period', 'Period', 14)],
    OperandType.PARABOLIC_SAR: [_number('af', 'Acceleration Factor', 0.02, minimum=0, step=0.01), _number('max_af', 'Max AF', 0.2, minimum=0, step=0.01)],
    OperandType.ICHIMOKU_CLOUD: [_number('tenkan', 'Tenkan (Conversion)', 9), _number('kijun', 'Kijun (Base)', 26), _number('senkou', 'Senkou B', 52), _select('output_line', 'Output Line', [
        {'value': 'TENKAN', 'label': 'Tenkan'}, {'value': 'KIJUN', 'label': 'Kijun'}, {'value': 'SENKOU_A', 'label': 'Senkou A'}, {'value': 'SENKOU_B', 'label': 'Senkou B'}, {'value': 'CHIKOU', 'label': 'Historical close (Kijun candles ago)'},
    ], 'TENKAN')],
    OperandType.CONSTANT: [{'key': 'value', 'label': 'Value', 'type': 'number', 'default': 0, 'step': 0.01}],
    OperandType.CANDLE_PATTERN: [{'key': 'pattern', 'label': 'Pattern', 'type': 'enum', 'enumKey': 'CandlePatternType', 'default': CandlePatternType.DOJI}],
    OperandType.CANDLE_BODY_SIZE: [_select('mode', 'Mode', [{'value': 'POINTS', 'label': 'Points'}, {'value': 'PERCENTAGE', 'label': 'Percentage'}], 'POINTS')],
    OperandType.VWAP: [_select('anchor', 'Anchor', [{'value': 'D', 'label': 'Daily'}, {'value': 'W', 'label': 'Weekly'}, {'value': 'M', 'label': 'Monthly'}], 'D')],
    OperandType.MATH_EXPRESSION: [{'key': 'expression', 'label': 'Math Formula', 'type': 'math', 'default': {'expression': '', 'variables': {}}}],
}

OPERAND_SHIFT_CONFIG = {'key': 'shift', 'label': 'Shift (Candles)', 'type': 'number', 'default': 0, 'min': 0, 'step': 1}

OPERAND_GROUPS = {
    'Price Action & Volume': [
        OperandType.LTP, OperandType.OPEN, OperandType.HIGH, OperandType.LOW,
        OperandType.CLOSE, OperandType.VOLUME, OperandType.VWAP, OperandType.HL2,
        OperandType.HLC3, OperandType.OHLC4, OperandType.CURRENT_DAY_OPEN,
        OperandType.PREV_WEEK_HIGH, OperandType.PREV_WEEK_LOW,
    ],
    'Candle Analysis': [OperandType.CANDLE_PATTERN, OperandType.CANDLE_BODY_SIZE],
    'Position State (Exit)': [
        OperandType.POSITION_PNL_PERCENTAGE, OperandType.POSITION_PNL_POINTS,
        OperandType.TRAILING_PEAK_OFFSET, OperandType.ENTRY_PRICE,
        OperandType.POSITION_RR_RATIO,
    ],
    'Math & Constants': [OperandType.CONSTANT, OperandType.MATH_EXPRESSION],
}
_GROUPED_OPERANDS = {operand for group in OPERAND_GROUPS.values() for operand in group}
OPERAND_GROUPS['Technical Indicators'] = [operand for operand in OperandType if operand not in _GROUPED_OPERANDS]
INDICATOR_OPERANDS = frozenset((*OPERAND_GROUPS['Technical Indicators'], OperandType.VWAP, OperandType.CANDLE_PATTERN))

# Math expressions accept numeric operands only. Position-state operands need
# an open position, so they are offered only to exit-related rule groups.
_MATH_EXPRESSION_BASE_TYPES = {
    OperandType.LTP, OperandType.OPEN, OperandType.HIGH, OperandType.LOW,
    OperandType.CLOSE, OperandType.VOLUME, OperandType.VWAP, OperandType.HL2,
    OperandType.HLC3, OperandType.OHLC4, OperandType.CURRENT_DAY_OPEN,
    OperandType.PREV_WEEK_HIGH, OperandType.PREV_WEEK_LOW,
    OperandType.CANDLE_BODY_SIZE, OperandType.CONSTANT,
    *(operand for operand in OPERAND_PARAMETER_CONFIG if operand not in {
        OperandType.CONSTANT, OperandType.MATH_EXPRESSION,
        OperandType.CANDLE_PATTERN,
    }),
}
POSITION_OPERANDS = {
    OperandType.POSITION_PNL_PERCENTAGE, OperandType.POSITION_PNL_POINTS,
    OperandType.TRAILING_PEAK_OFFSET, OperandType.ENTRY_PRICE,
    OperandType.POSITION_RR_RATIO,
}


def get_math_expression_operand_types(rule_type):
    """Return numeric math-variable types valid for a rule context."""
    try:
        rule_type = RuleType(rule_type)
    except (TypeError, ValueError):
        rule_type = None

    allowed = set(_MATH_EXPRESSION_BASE_TYPES)
    if rule_type in {RuleType.EXIT, RuleType.STOP_LOSS, RuleType.TARGET}:
        allowed.update(POSITION_OPERANDS)
    return sorted(operand.value for operand in allowed)


def get_operand_parameter_config(operand_type):
    """Return a JSON-safe parameter schema for a rule operand."""
    try:
        operand_type = OperandType(operand_type)
    except (TypeError, ValueError):
        return []
    config = [dict(item) for item in OPERAND_PARAMETER_CONFIG.get(operand_type, [])]
    if operand_type not in {OperandType.CONSTANT, OperandType.MATH_EXPRESSION} | POSITION_OPERANDS:
        config.append(dict(OPERAND_SHIFT_CONFIG))
    return config


def get_operand_parameter_defaults(operand_type):
    """Return persisted defaults from the same schema rendered by the UI."""
    return {item['key']: item['default'] for item in get_operand_parameter_config(operand_type)}


class ComparisonOperator(models.TextChoices):
    """Comparison operators for rules."""
    GREATER = 'GT', 'Greater Than'
    LESS = 'LT', 'Less Than'
    EQUAL = 'EQ', 'Equal To'
    GREATER_EQUAL = 'GTE', 'Greater Than or Equal'
    LESS_EQUAL = 'LTE', 'Less Than or Equal'
    CROSSES_ABOVE = 'CROSSES_ABOVE', 'Crosses Above'
    CROSSES_BELOW = 'CROSSES_BELOW', 'Crosses Below'
    NOT_EQUAL = 'NEQ', 'Not Equal To'


class QuantityType(models.TextChoices):
    """How position quantity is determined."""
    FIXED = 'FIXED', 'Fixed Quantity'
    CAPITAL_BASED = 'CAPITAL_BASED', 'Capital Based'


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
    """Fixed notification urgency values; event details belong in title/message."""
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


class BacktestStatus(models.TextChoices):
    """Backtest run status."""
    PENDING = 'PENDING', 'Pending'
    QUEUED = 'QUEUED', 'Queued'
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


class ActivityResource(models.TextChoices):
    STRATEGY = "Strategy", "Strategy"
    BROKER = "BrokerCredential", "Broker account"
    PAPER_ACCOUNT = "PaperAccount", "Paper account"
    PAPER_ALLOCATION = "CapitalAllocation", "Paper allocation"
    LIVE_ALLOCATION = "LiveStrategyAllocation", "Live allocation"
    PAPER_SESSION = "PaperTradingSession", "Paper session"
    LIVE_SESSION = "TradingSession", "Live session"
    USER = "User", "Authentication"
