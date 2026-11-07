"""Studio sections and defaults. Real instruments, calendars and accounts stay data.

Serializers and React read these same facts; specialized validation stays in the
owning app. Always copy a template before attaching user-owned mutable values.
"""
from copy import deepcopy

from common.enums import (
    CandleTimeframe, Exchange, ExpirySelection, InstrumentType, LogicalOperator,
    MarketSession, OrderType, QuantityType, QuantityUnit, RuleType, Side, OperandType,
    ComparisonOperator,
    StrikeSelection, Timezone, TradingDay, OptionType, StrategyType, MarketType,
    StrategyVisibility, StrategyStatus,
)

DOCUMENT_VERSIONS = {'schema_version': 1, 'semantics_version': 1}
LIMITS = {'document_bytes': 256_000, 'groups': 32, 'group_id_length': 80,
          'group_name_length': 100, 'name_length': 40, 'route_id_length': 80,
          'sizing_overrides_per_contract': 1}
NAME_PATTERN = rf'[A-Za-z][A-Za-z0-9_]{{0,{LIMITS["name_length"] - 1}}}'
ROUTE_ID_PATTERN = rf'[A-Za-z][A-Za-z0-9_-]{{0,{LIMITS["route_id_length"] - 1}}}'
SETUP_LIMITS = {'captures': 16, 'steps': 8, 'expiry_bars': 1000}
SOURCE_ROLES = [{'value': 'signal', 'label': 'Signal instrument'},
                {'value': 'trade', 'label': 'Traded contract'}]
STAGES = [
    {'value': RuleType.ENTRY, 'label': 'Entry', 'combination': ['entry_order_config', 'entry_group_operator'], 'position': False, 'setup': True},
    {'value': RuleType.STOP_LOSS, 'label': 'Stop loss', 'combination': ['exit_order_config', 'stop_loss_group_operator'], 'position': True, 'setup': False},
    {'value': RuleType.TARGET, 'label': 'Target', 'combination': ['exit_order_config', 'target_group_operator'], 'position': True, 'setup': False},
    {'value': RuleType.EXIT, 'label': 'Exit', 'combination': ['exit_order_config', 'exit_group_operator'], 'position': True, 'setup': False},
]
STAGE_BY_TYPE = {stage['value']: stage for stage in STAGES}


def choice(label, family, default=None):
    return {'label': label, 'choice_ref': family, 'default': default}


def number(label, default, minimum, maximum=None, step=1):
    return {'label': label, 'default': default, 'min': minimum, 'max': maximum, 'step': step}


DETAIL_FIELDS = {
    'name': {'label': 'Strategy name', 'default': '', 'min_length': 3, 'max_length': 255},
    'description': {'label': 'Description', 'default': ''},
    'strategy_type': choice('Strategy type', 'StrategyType', StrategyType.INTRADAY),
    'market_type': choice('Market', 'MarketType', MarketType.EQUITY),
    'exchange': choice('Exchange', 'Exchange', Exchange.NSE),
    'instrument_type': choice('Instrument type', 'InstrumentType', InstrumentType.STOCK),
    'visibility': choice('Visibility', 'StrategyVisibility', StrategyVisibility.PRIVATE),
    'status': choice('Status', 'StrategyStatus', StrategyStatus.DRAFT),
    'paper_trading_enabled': {'label': 'Paper trading', 'default': True},
    'live_trading_enabled': {'label': 'Live trading', 'default': False},
}


SIZING_FIELDS = {
    'sizing_method': choice('Sizing method', 'QuantityType', QuantityType.CAPITAL_BASED),
    'quantity_unit': choice('Measured in', 'QuantityUnit', QuantityUnit.UNITS),
    'fixed_quantity': number('Fixed quantity', 1, 1),
    'capital_percentage': number('Available capital (%)', '10.00', 0.01, 100, 0.01),
}
SCHEDULE_FIELDS = {
    'candle_timeframe': choice('Default candle timeframe', 'CandleTimeframe', CandleTimeframe.M5),
    'timezone': choice('Schedule timezone', 'Timezone', Timezone.ASIA_KOLKATA),
    'trading_days': choice('Selected weekdays', 'TradingDay', [TradingDay.MONDAY, TradingDay.TUESDAY,
                          TradingDay.WEDNESDAY, TradingDay.THURSDAY, TradingDay.FRIDAY]),
    'market_session': choice('Market session', 'MarketSession', MarketSession.MARKET_OPEN),
    'start_time': {'label': 'Entry start', 'default': '09:15:00'},
    'end_time': {'label': 'Entry end', 'default': '15:30:00'},
    'no_trade_windows': {'label': 'Excluded entry windows', 'default': []},
}
ENTRY_FIELDS = {
    'entry_side': choice('Entry direction', 'Side', Side.BUY),
    'entry_group_operator': choice('Entry groups', 'LogicalOperator', LogicalOperator.OR),
    'order_type': {**choice('Order type', 'OrderType', OrderType.MARKET), 'values': [OrderType.MARKET]},
}
EXIT_FIELDS = {name: choice(label, 'LogicalOperator', LogicalOperator.OR) for name, label in (
    ('exit_group_operator', 'Exit groups'), ('stop_loss_group_operator', 'Stop-loss groups'),
    ('target_group_operator', 'Target groups'))}
POLICY_FIELDS = {
    'instrument_type': {**choice('Contract family', 'InstrumentType', InstrumentType.OPTION),
                        'values': [InstrumentType.OPTION, InstrumentType.FUTURE]},
    'option_type': choice('Option right', 'OptionType', OptionType.CE),
    'expiry': choice('Expiry selection', 'ExpirySelection', ExpirySelection.NEAREST),
    'expiry_date': {'label': 'Specific expiry', 'default': None},
    'allow_expiry_day': {'label': 'Include contracts expiring today', 'default': False},
    'strike': choice('Strike selection', 'StrikeSelection', StrikeSelection.ATM),
    'distance': number('Listed strikes from ATM', 0, 0, 20),
    'strike_price': {'label': 'Specific strike', 'default': None, 'min': 0.01, 'step': 0.01},
}
AUTOMATIC = {
    'fields': POLICY_FIELDS,
    'underlying_types': [InstrumentType.STOCK, InstrumentType.INDEX],
    'exchanges': [Exchange.NSE, Exchange.BSE],
    'relative_strikes': [StrikeSelection.ITM, StrikeSelection.OTM],
    'fixed_sizing_unit': QuantityUnit.LOTS,
    'sizing_override': {'override_sizing': True,
                       'sizing_method': QuantityType.FIXED,
                       'fixed_quantity': SIZING_FIELDS['fixed_quantity']['default'],
                       'quantity_unit': QuantityUnit.LOTS},
    # Switching family clears incompatible fields independently of the default
    # family selected for newly added policies.
    'family_resets': {
        InstrumentType.OPTION: {key: POLICY_FIELDS[key]['default']
                                for key in ('option_type', 'strike', 'distance', 'strike_price')},
        InstrumentType.FUTURE: {'option_type': '', 'strike': StrikeSelection.ATM, 'distance': 0, 'strike_price': None},
    },
    'description': 'Selects while flat. Working orders and open positions keep their original contract.',
    'selection_help': 'Next expiry is the next listed eligible date. ATM ties use the lower strike; distance follows listed strikes, not fixed point intervals.',
}

# Field-aware value formatting: identical values in different vocabularies never
# share a guessed label. Parameter and node labels live with their own definitions.
FIELDS = {
    **SCHEDULE_FIELDS, **SIZING_FIELDS, **ENTRY_FIELDS, **EXIT_FIELDS, **POLICY_FIELDS,
    **DETAIL_FIELDS,
    **{name: choice(label, family) for name, label, family in (
        ('rule_type', 'Condition stage', 'RuleType'), ('comparison', 'Comparison', 'ComparisonOperator'),
        ('operand_a_type', 'Left operand', 'OperandType'), ('operand_b_type', 'Right operand', 'OperandType'),
        ('operand_a_timeframe', 'Left timeframe', 'CandleTimeframe'), ('operand_b_timeframe', 'Right timeframe', 'CandleTimeframe'))},
    'is_active': {'label': 'Enabled'}, 'override_sizing': {'label': 'Custom size'},
    'operand_a_params': {'label': 'Left parameters'}, 'operand_b_params': {'label': 'Right parameters'},
    'logical_operator': choice('Combine conditions', 'LogicalOperator'),
    'rule_groups': {'label': 'Groups'}, 'rules': {'label': 'Conditions'},
    'execution_routes': {'label': 'Sizing overrides'}, 'instrument_id': {'label': 'Instrument'},
    'source': {'label': 'Market source', 'choices': SOURCE_ROLES},
}


def defaults(fields):
    return {key: deepcopy(field['default']) for key, field in fields.items()}


def default_trading_days():
    return deepcopy(SCHEDULE_FIELDS['trading_days']['default'])


def new_document():
    """One complete canonical document; callers own every nested container."""
    return {**DOCUMENT_VERSIONS, 'expressions': {}, 'initial_risk': None,
            'time_rule': defaults(SCHEDULE_FIELDS), 'entry_order_config': defaults(ENTRY_FIELDS),
            'exit_order_config': defaults(EXIT_FIELDS), 'position_sizing_rule': defaults(SIZING_FIELDS),
            'watchlist_instruments': [], 'rule_groups': []}


def input_template(kind=OperandType.CLOSE, params=None):
    return {'op': 'input', 'type': kind, 'params': deepcopy(params or {}), 'timeframe': None, 'source': 'signal'}


COMPARISON_TEMPLATE = {'op': 'compare', 'comparison': ComparisonOperator.GREATER, 'left': input_template(),
                       'right': input_template(OperandType.EMA, {'period': 20})}
SCREEN_COMPARISON_TEMPLATE = {'op': 'compare', 'comparison': ComparisonOperator.GREATER,
                             'left': input_template(OperandType.RSI), 'right': input_template(OperandType.CONSTANT)}
SETUP_TEMPLATE = {
    'arm': None, 'captures': {'signal_high': input_template(OperandType.HIGH), 'signal_low': input_template(OperandType.LOW)},
    'steps': [], 'invalidate': {'op': 'compare', 'comparison': ComparisonOperator.LESS, 'left': input_template(OperandType.LTP),
                             'right': {'op': 'capture', 'setup': '', 'name': 'signal_low'}},
    'timeframe': None, 'expires_after_bars': 3,
}
CONFIRM_TEMPLATE = {'op': 'compare', 'comparison': ComparisonOperator.CROSSES_ABOVE, 'left': input_template(OperandType.LTP),
                    'right': {'op': 'capture', 'setup': '', 'name': 'signal_high'}}


def configuration():
    return deepcopy({
        'details': {'fields': DETAIL_FIELDS, 'defaults': defaults(DETAIL_FIELDS)},
        'markets': {'source_roles': SOURCE_ROLES, 'automatic': AUTOMATIC},
        'sizing': {'fields': SIZING_FIELDS, 'entry_side': ENTRY_FIELDS['entry_side']},
        'schedule': {'fields': SCHEDULE_FIELDS, 'description': 'Entry end stops new entries; it does not close positions or cancel pending orders.'},
        'setup': {'constraints': SETUP_LIMITS, 'single_active_entry': True,
                  'phases': ['Arm', 'Remember values', 'Intermediate confirmations', 'Confirm entry', 'Invalidate or expire'],
                  'template': SETUP_TEMPLATE, 'confirmation': CONFIRM_TEMPLATE},
        'defaults': {'document': new_document(), 'templates': {
            'input': input_template(), 'comparison': COMPARISON_TEMPLATE,
            'numeric_argument': input_template(OperandType.CONSTANT, {'value': 1}),
            'screen_comparison': SCREEN_COMPARISON_TEMPLATE,
            'initial_risk': {**input_template(OperandType.ATR), 'source': 'trade'},
            'group': {'name': 'Condition group', 'priority': 1, 'is_active': True,
                      'condition': {'op': 'all', 'args': [COMPARISON_TEMPLATE]}},
            'contract_selection': defaults(POLICY_FIELDS)}},
        'constraints': LIMITS, 'fields': FIELDS,
        'patterns': {'name': f'^{NAME_PATTERN}$', 'route_id': f'^{ROUTE_ID_PATTERN}$'},
        'steps': ['Markets & size', 'Conditions', 'Schedule', 'Review'],
    })
