"""
Common app - view to serve all enum choices as a JSON API.
Used by the frontend to avoid hardcoding choice values.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .enums import (
    StrategyType, MarketType, Exchange, InstrumentType, OptionType,
    OrderType, OrderStatus, Side, ProductType, StrategyStatus, StrategyVisibility,
    CandleTimeframe, CandlePart, MarketSession,
    CandlePatternType,
    LogicalOperator, RuleType,
    RuleGroupAction,
    OperandType,
    ComparisonOperator,
    QuantityType, CapitalAllocationType, StrikeSelectionLogic, ExpiryType,
    AutoDisableTriggerType, Severity,
    TransactionType, RebalanceFrequency, Timezone, BacktestStatus,
    BrokerName,
    get_operand_parameter_config, OperandType, TradingDay,
    DEFAULT_TRADING_DAYS, DEFAULT_TRADING_START_TIME, DEFAULT_TRADING_END_TIME,
    OPERAND_GROUPS, get_math_expression_operand_types,
)


def _choices_to_list(choices):
    """Convert Django TextChoices / list-of-tuples into [{value, label}, ...]."""
    if hasattr(choices, 'choices'):
        # TextChoices enum
        return [{'value': v, 'label': l} for v, l in choices.choices]
    
    # Handle plain list of tuples
    try:
        if isinstance(choices, (list, tuple)):
            return [{'value': v, 'label': l} for v, l in choices]
    except Exception:
        pass
        
    return []


# Map of enum name → source
_ENUM_SOURCES = {
    # Strategy classification
    'StrategyType': StrategyType,
    'MarketType': MarketType,
    'Exchange': Exchange,
    'InstrumentType': InstrumentType,
    'OptionType': OptionType,
    'OrderType': OrderType,
    'OrderStatus': OrderStatus,
    'Side': Side,
    'ProductType': ProductType,
    'BrokerName': BrokerName,

    # Strategy lifecycle
    'StrategyStatus': StrategyStatus,
    'StrategyVisibility': StrategyVisibility,

    # Candle / time
    'CandleTimeframe': CandleTimeframe,
    'TradingDay': TradingDay,

    'CandlePart': CandlePart,
    'CandlePatternType': CandlePatternType,
    'MarketSession': MarketSession,

    # Rules
    'LogicalOperator': LogicalOperator,
    'RuleType': RuleType,
    'RuleGroupAction': RuleGroupAction,
    'OperandType': OperandType,
    'ComparisonOperator': ComparisonOperator,

    # Position sizing
    'QuantityType': QuantityType,
    'CapitalAllocationType': CapitalAllocationType,

    # Options
    'StrikeSelectionLogic': StrikeSelectionLogic,
    'ExpiryType': ExpiryType,


    # Risk management
    'AutoDisableTriggerType': AutoDisableTriggerType,
    'Severity': Severity,

    # Portfolio
    'TransactionType': TransactionType,
    'RebalanceFrequency': RebalanceFrequency,
    'BacktestStatus': BacktestStatus,

    'Timezone':Timezone,
}


@api_view(['GET'])
@permission_classes([AllowAny])
def enum_choices(request):
    """Return all enum choices as {EnumName: [{value, label}, ...]}."""
    data = {}
    for name, source in _ENUM_SOURCES.items():
        data[name] = _choices_to_list(source)

    data['OperandParameterConfig'] = {
        operand.value: get_operand_parameter_config(operand)
        for operand in OperandType
    }
    data['OperandGroups'] = {
        name: [operand.value for operand in operands]
        for name, operands in OPERAND_GROUPS.items()
    }
    data['MathExpressionOperandTypes'] = {
        rule_type.value: get_math_expression_operand_types(rule_type)
        for rule_type in RuleType
    }
    data['StrategyBuilderDefaults'] = {
        'time_rule': {
            'trading_days': list(DEFAULT_TRADING_DAYS),
            'market_session': 'ALL',
            'start_time': DEFAULT_TRADING_START_TIME.strftime('%H:%M'),
            'end_time': DEFAULT_TRADING_END_TIME.strftime('%H:%M'),
            'candle_timeframe': CandleTimeframe.M5,
            'timezone': Timezone.ASIA_KOLKATA,
            'no_trade_windows': [],
        },
        'entry_order_config': {
            'entry_side': 'BUY', 'entry_group_operator': 'OR',
            'order_type': 'MARKET', 'price_offset': 0, 'cooldown_seconds': 0,
        },
        'position_sizing_rule': {
            'sizing_method': 'CAPITAL_BASED', 'fixed_quantity': 1,
            'capital_percentage': 10, 'risk_per_trade_percentage': 1,
        },
        'auto_disable_rule': {
            'trigger_type': 'CONSECUTIVE_LOSSES', 'threshold_value': 0,
            'threshold_count': 5, 'auto_reenable': False,
            'cooldown_hours': 24, 'is_active': True,
        },
    }
        
    return Response(data)
