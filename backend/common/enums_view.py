"""
Common app - view to serve all enum choices as a JSON API.
Used by the frontend to avoid hardcoding choice values.
"""
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .enums import (
    StrategyType, MarketType, Exchange, InstrumentType, OptionType,
    OrderType, OrderStatus, Side, ProductType, StrategyStatus, StrategyVisibility, ExecutionSessionStatus,
    CandleTimeframe, MarketSession,
    CandlePatternType,
    LogicalOperator, RuleType,
    OperandType,
    ComparisonOperator,
    QuantityType,
    TransactionType, Timezone, BacktestStatus,
    BrokerName,
    get_operand_parameter_config, TradingDay,
    DEFAULT_TRADING_DAYS, DEFAULT_TRADING_START_TIME, DEFAULT_TRADING_END_TIME,
    OPERAND_GROUPS, get_math_expression_operand_types,
    TerminalOrderType, TerminalOrderStatus, ChartTimeframe,
    PositionSide, TerminalPositionAction, TerminalExitReason,
    TERMINAL_USER_ORDER_TYPES, TERMINAL_PRICE_REQUIRED_TYPES, TERMINAL_TRIGGER_REQUIRED_TYPES,
)


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
    'TerminalOrderType': TerminalOrderType,
    'TerminalOrderStatus': TerminalOrderStatus,
    'PositionSide': PositionSide,
    'TerminalPositionAction': TerminalPositionAction,
    'TerminalExitReason': TerminalExitReason,
    'ProductType': ProductType,
    'BrokerName': BrokerName,

    # Strategy lifecycle
    'StrategyStatus': StrategyStatus,
    'ExecutionSessionStatus': ExecutionSessionStatus,
    'StrategyVisibility': StrategyVisibility,

    # Candle / time
    'CandleTimeframe': CandleTimeframe,
    'ChartTimeframe': ChartTimeframe,
    'TradingDay': TradingDay,

    'CandlePatternType': CandlePatternType,
    'MarketSession': MarketSession,

    # Rules
    'LogicalOperator': LogicalOperator,
    'RuleType': RuleType,
    'OperandType': OperandType,
    'ComparisonOperator': ComparisonOperator,

    # Position sizing
    'QuantityType': QuantityType,

    # Portfolio
    'TransactionType': TransactionType,
    'BacktestStatus': BacktestStatus,

    'Timezone':Timezone,
}


def get_enum_metadata():
    """Expose names, values, labels and field requirements to the frontend."""
    data = {
        name: [{'name': member.name, 'value': member.value, 'label': member.label} for member in source]
        for name, source in _ENUM_SOURCES.items()
    }

    for choice in data['TerminalOrderType']:
        choice.update(
            user_selectable=choice['value'] in TERMINAL_USER_ORDER_TYPES,
            requires_price=choice['value'] in TERMINAL_PRICE_REQUIRED_TYPES,
            requires_trigger=choice['value'] in TERMINAL_TRIGGER_REQUIRED_TYPES,
        )
    for choice in data['TerminalPositionAction']:
        choice.update(
            requires_quantity=choice['value'] not in (TerminalPositionAction.CLOSE, TerminalPositionAction.SETTLE),
            requires_expiry=choice['value'] == TerminalPositionAction.SETTLE,
            requires_settlement_price=choice['value'] == TerminalPositionAction.SETTLE,
        )

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
            'market_session': MarketSession.MARKET_OPEN,
            'start_time': DEFAULT_TRADING_START_TIME.strftime('%H:%M'),
            'end_time': DEFAULT_TRADING_END_TIME.strftime('%H:%M'),
            'candle_timeframe': CandleTimeframe.M5,
            'timezone': Timezone.ASIA_KOLKATA,
            'no_trade_windows': [],
        },
        'entry_order_config': {
            'entry_side': Side.BUY, 'entry_group_operator': LogicalOperator.OR,
            'order_type': OrderType.MARKET,
        },
        'position_sizing_rule': {
            'sizing_method': QuantityType.CAPITAL_BASED, 'fixed_quantity': 1,
            'capital_percentage': 10,
        },
    }
        
    return data


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def enum_choices(request):
    return Response(get_enum_metadata())
