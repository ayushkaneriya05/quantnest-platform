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
    CandleTimeframe, CandleCompletionRule, CandlePart, MarketSession,
    CandlePatternType,
    LogicalOperator, RuleType,
    OperandType,
    ComparisonOperator,
    QuantityType, CapitalAllocationType, StrikeSelectionLogic, ExpiryType,
    ExecutionStyle, AutoDisableTriggerType,
    ViolationType, ViolationAction, Severity,
    TransactionType, RebalanceFrequency, Timezone, BacktestStatus,
    BrokerName, OptimizationMetric, OptimizableParameter
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
    'CandleCompletionRule': CandleCompletionRule,
    'CandlePart': CandlePart,
    'CandlePatternType': CandlePatternType,
    'MarketSession': MarketSession,

    # Rules
    'LogicalOperator': LogicalOperator,
    'RuleType': RuleType,
    'OperandType': OperandType,
    'ComparisonOperator': ComparisonOperator,

    # Position sizing
    'QuantityType': QuantityType,
    'CapitalAllocationType': CapitalAllocationType,

    # Options
    'StrikeSelectionLogic': StrikeSelectionLogic,
    'ExpiryType': ExpiryType,

    # Entry config
    'ExecutionStyle': ExecutionStyle,

    # Risk management
    'AutoDisableTriggerType': AutoDisableTriggerType,
    'ViolationType': ViolationType,
    'ViolationAction': ViolationAction,
    'Severity': Severity,

    # Portfolio
    'TransactionType': TransactionType,
    'RebalanceFrequency': RebalanceFrequency,
    'BacktestStatus': BacktestStatus,
    'OptimizationMetric': OptimizationMetric,
    'OptimizableParameter': OptimizableParameter,

    'Timezone':Timezone,
}


@api_view(['GET'])
@permission_classes([AllowAny])
def enum_choices(request):
    """Return all enum choices as {EnumName: [{value, label}, ...]}."""
    data = {}
    for name, source in _ENUM_SOURCES.items():
        data[name] = _choices_to_list(source)
        
    return Response(data)
