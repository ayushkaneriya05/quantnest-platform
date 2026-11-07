"""Expression vocabulary and limits; numerical implementations stay in execution."""
from copy import deepcopy
from .configuration import SOURCE_ROLES

MAX_NODES = 512
MAX_DEPTH = 24
MAX_EXPRESSIONS = 32
MAX_WINDOW = 1000
WINDOWS = {'lag': 'Lag by bars', 'highest': 'Rolling highest', 'lowest': 'Rolling lowest',
           'rolling_mean': 'Rolling average', 'rolling_sum': 'Rolling sum',
           'rolling_std': 'Rolling standard deviation', 'zscore': 'Rolling z-score',
           'return_pct': 'Return over bars (%)'}
WINDOW_DESCRIPTIONS = {
    'lag': 'Reads the input value from {bars} completed candles ago.',
    'highest': 'Returns the highest input value across the last {bars} completed candles.',
    'lowest': 'Returns the lowest input value across the last {bars} completed candles.',
    'rolling_mean': 'Averages the input values across the last {bars} completed candles.',
    'rolling_sum': 'Adds the input value from each of the last {bars} completed candles.',
    'rolling_std': 'Measures the input values\' dispersion across the last {bars} completed candles, using the selected variance divisor.',
    'zscore': 'Measures how many selected-window standard deviations the latest input is above or below its {bars}-candle mean. Zero variance is unavailable.',
    'return_pct': 'Calculates (latest input / input {bars} completed candles ago - 1) × 100. The starting value must be positive.',
}
VARIANCE_WINDOWS = frozenset(('rolling_std', 'zscore'))
NUMERIC = {
    'add': ('Add', 2), 'subtract': ('Subtract', 2),
    'multiply': ('Multiply', 2), 'divide': ('Divide', 2),
    'min': ('Minimum', 2), 'max': ('Maximum', 2),
    'abs': ('Absolute value', 1), 'negate': ('Negate', 1),
}
LOGIC = {'all': 'All conditions', 'any': 'Any condition', 'not': 'Not', 'at_least': 'At least K'}
DISPLAY_SYMBOLS = {'add': '+', 'subtract': '−', 'multiply': '×', 'divide': '÷', 'all': 'AND', 'any': 'OR'}


MAX_ARITHMETIC_NODES = 512
MAX_ARITHMETIC_DEPTH = 64
ARITHMETIC_VARIABLE_PREFIX = 'VAR_'
NODES = {
    'input': {'label': 'Value or indicator', 'result': 'number', 'fields': ['type', 'params', 'timeframe', 'source']},
    'expression': {'label': 'Named formula', 'result': 'number', 'fields': ['name']},
    'capture': {'label': 'Captured value', 'result': 'number', 'fields': ['setup', 'name']},
    'compare': {'label': 'Comparison', 'result': 'boolean', 'fields': ['left', 'comparison', 'right']},
}


def specification():
    """The editor receives the same operator catalog that compilation accepts."""
    return {
        'schema_version': 1,
        'numeric': [{'value': key, 'label': value[0], 'arity': value[1], 'result': 'number',
                     'display_symbol': DISPLAY_SYMBOLS.get(key)} for key, value in NUMERIC.items()],
        'windows': [{'value': key, 'label': label, 'description': WINDOW_DESCRIPTIONS[key], 'arity': 1, 'result': 'number', 'variance': key in VARIANCE_WINDOWS, 'default_bars': 1 if key == 'lag' else 20, 'default_ddof': 0}
                    for key, label in WINDOWS.items()],
        'variance_divisors': [{'value': 0, 'label': 'Population (N)'}, {'value': 1, 'label': 'Sample (N - 1)'}],
        'max_window': MAX_WINDOW,
        'logic': [{'value': key, 'label': value, 'result': 'boolean',
                   'display_symbol': DISPLAY_SYMBOLS.get(key)} for key, value in LOGIC.items()],
        'max_nodes': MAX_NODES, 'max_depth': MAX_DEPTH, 'max_expressions': MAX_EXPRESSIONS,
        'source_roles': deepcopy(SOURCE_ROLES),
        'nodes': [{'value': key, **value} for key, value in NODES.items()],
        'text_arithmetic': {'operators': ['+', '-', '*', '/', '%', '(', ')'],
                            'variable_prefix': ARITHMETIC_VARIABLE_PREFIX,
                            'max_nodes': MAX_ARITHMETIC_NODES, 'max_depth': MAX_ARITHMETIC_DEPTH},
    }


