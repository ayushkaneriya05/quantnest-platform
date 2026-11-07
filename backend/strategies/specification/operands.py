"""Operand facts shared by Studio, validation, research and compilation."""
from copy import deepcopy

from common.enums import CandlePatternType, OperandType, RuleType

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


SOURCE_CHOICES = PRICE_SOURCE_CHOICES + INDICATOR_SOURCE_CHOICES


def _period_source(period=14):
    """The common period/source contract, with explicit per-indicator overrides."""
    return [_number('period', 'Period', period),
            {'key': 'source', 'label': 'Source', 'type': 'source',
             'default': OperandType.CLOSE.value, 'options': SOURCE_CHOICES}]


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

PARAMETERS = {
    OperandType.SMA: _period_source(),
    OperandType.EMA: _period_source(),
    OperandType.WMA: _period_source(),
    OperandType.HMA: _period_source(),
    OperandType.ALMA: _period_source(),
    OperandType.KAMA: _period_source(),
    OperandType.DEMA: _period_source(),
    OperandType.TEMA: _period_source(),
    OperandType.RSI: _period_source(),
    OperandType.ROC: _period_source(9),
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

SHIFT_FIELD = {'key': 'shift', 'label': 'Shift (Candles)', 'type': 'number', 'default': 0, 'min': 0, 'step': 1}

POSITION_TYPES = (
    OperandType.POSITION_PNL_PERCENTAGE, OperandType.POSITION_PNL_POINTS,
    OperandType.TRAILING_PEAK_OFFSET, OperandType.ENTRY_PRICE, OperandType.POSITION_RR_RATIO,
)
POSITION_OPERANDS = frozenset(POSITION_TYPES)

INDICATOR_OPERANDS = frozenset(OperandType(item['value']) for item in INDICATOR_SOURCE_CHOICES) | {OperandType.CANDLE_PATTERN}
GROUPS = [
    {'value': 'price_volume', 'label': 'Price Action & Volume', 'operands': [
        OperandType.LTP, OperandType.OPEN, OperandType.HIGH, OperandType.LOW,
        OperandType.CLOSE, OperandType.VOLUME, OperandType.VWAP, OperandType.HL2,
        OperandType.HLC3, OperandType.OHLC4, OperandType.CURRENT_DAY_OPEN,
        OperandType.PREV_WEEK_HIGH, OperandType.PREV_WEEK_LOW,
    ]},
    {'value': 'candles', 'label': 'Candle Analysis',
     'operands': [OperandType.CANDLE_PATTERN, OperandType.CANDLE_BODY_SIZE]},
    {'value': 'position', 'label': 'Position State (Exit)', 'operands': list(POSITION_TYPES)},
    {'value': 'math', 'label': 'Math & Constants',
     'operands': [OperandType.CONSTANT, OperandType.MATH_EXPRESSION]},
    {'value': 'indicators', 'label': 'Technical Indicators', 'operands': [kind for kind in OperandType
        if kind in INDICATOR_OPERANDS and kind not in (OperandType.VWAP, OperandType.CANDLE_PATTERN)]},
]

# Math expressions accept numeric operands only. Position-state operands need
# an open position, so they are offered only to exit-related rule groups.
_MATH_EXPRESSION_BASE_TYPES = {
    OperandType.LTP, OperandType.OPEN, OperandType.HIGH, OperandType.LOW,
    OperandType.CLOSE, OperandType.VOLUME, OperandType.VWAP, OperandType.HL2,
    OperandType.HLC3, OperandType.OHLC4, OperandType.CURRENT_DAY_OPEN,
    OperandType.PREV_WEEK_HIGH, OperandType.PREV_WEEK_LOW,
    OperandType.CANDLE_BODY_SIZE, OperandType.CONSTANT,
    *(operand for operand in PARAMETERS if operand not in {
        OperandType.CONSTANT, OperandType.MATH_EXPRESSION,
        OperandType.CANDLE_PATTERN,
    }),
}
# Each operand owns its capabilities independently of component presentation.
def _operand(kind):
    position = kind in POSITION_OPERANDS
    constant = kind == OperandType.CONSTANT
    live = kind == OperandType.LTP
    context = 'position' if position else 'constant' if constant else 'market'
    observation = 'position' if position else 'constant' if constant else 'tick' if live else 'candle'
    parameters = deepcopy(PARAMETERS.get(kind, []))
    if kind not in {OperandType.CONSTANT, OperandType.MATH_EXPRESSION} | POSITION_OPERANDS:
        parameters.append({**SHIFT_FIELD, 'editable': not live})
    return {'value': kind.value, 'label': kind.label, 'context': context,
            'observation': observation, 'source_policy': 'trade' if position else 'none' if constant else 'selectable',
            'supports_timeframe': not position and not constant and not live,
            'supports_shift': not position and not constant and not live and kind != OperandType.MATH_EXPRESSION,
            'calculation_kind': 'indicator' if kind in INDICATOR_OPERANDS else observation,
            'allowed_in': {'entry': not position, 'exit': True, 'screen': not position and not live,
                           'rolling': not position and not live, 'math': kind in _MATH_EXPRESSION_BASE_TYPES or position},
            'parameters': parameters}


OPERANDS = {kind.value: _operand(kind) for kind in OperandType}


def get_operand_parameter_config(operand_type):
    return deepcopy(OPERANDS[OperandType(operand_type).value]['parameters'])


def get_operand_parameter_defaults(operand_type):
    return {item['key']: deepcopy(item['default']) for item in OPERANDS[OperandType(operand_type).value]['parameters']}


def operand_types(context, *, math=False):
    return [kind for kind, spec in OPERANDS.items()
            if spec['allowed_in'][context] and (not math or spec['allowed_in']['math'])]


def get_math_expression_operand_types(rule_type):
    return operand_types('entry' if RuleType(rule_type) == RuleType.ENTRY else 'exit', math=True)


def specification():
    operands = deepcopy(OPERANDS)
    # Source options are large and identical for many indicators. Publish them
    # once; authoring validation retains the same resolved Python parameter schema.
    for operand in operands.values():
        for field in operand['parameters']:
            if field['type'] == 'source':
                field.pop('options')
                field['choice_ref'] = 'OperandSources'
    return {'operands': operands,
            'choices': {'OperandSources': deepcopy(SOURCE_CHOICES)},
            'groups': [{**group, 'operands': [kind.value for kind in group['operands']]}
                       for group in GROUPS]}
