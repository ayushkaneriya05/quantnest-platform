"""
Common app - view to serve all enum choices as a JSON API.
Used by the frontend to avoid hardcoding choice values.
"""
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .enums import (
    StrategyType, MarketType, Exchange, InstrumentType, OptionType, ExpirySelection, StrikeSelection,
    OrderType, OrderStatus, Side, ProductType, StrategyStatus, StrategyVisibility, ExecutionSessionStatus,
    CandleTimeframe, MarketSession,
    CandlePatternType,
    LogicalOperator, RuleType,
    OperandType,
    ComparisonOperator,
    QuantityType, QuantityUnit,
    TransactionType, Timezone, BacktestStatus,
    BrokerName,
    TradingDay,
    TerminalOrderType, TerminalOrderStatus, ChartTimeframe,
    PositionSide, TerminalPositionAction, TerminalExitReason,
    TERMINAL_USER_ORDER_TYPES, TERMINAL_PRICE_REQUIRED_TYPES, TERMINAL_TRIGGER_REQUIRED_TYPES,
)


# Map of enum name → source
_ENUM_SOURCES = {
    'QuantityUnit': QuantityUnit,
    # Strategy classification
    'StrategyType': StrategyType,
    'MarketType': MarketType,
    'Exchange': Exchange,
    'InstrumentType': InstrumentType,
    'OptionType': OptionType,
    'ExpirySelection': ExpirySelection,
    'StrikeSelection': StrikeSelection,
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
            requires_quantity=choice['value'] != TerminalPositionAction.CLOSE,
        )

    from strategies.specification import studio_specification
    data['StrategyStudio'] = studio_specification()

    from common.pagination import StandardPagination
    data['PaginationDefaults'] = StandardPagination.defaults()
    return data


@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def enum_choices(request):
    return Response(get_enum_metadata())
