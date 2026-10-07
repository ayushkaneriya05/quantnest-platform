"""Small, inspectable presets; operands and defaults use the shared builder contract."""
from common.enums import OperandType, ComparisonOperator
from .validation import validate_rule, json_data


def _rule(a, b, comparison=ComparisonOperator.GREATER, a_params=None, b_params=None):
    return json_data(validate_rule({"operand_a_type": a, "operand_a_params": a_params or {},
                                  "comparison": comparison, "operand_b_type": b, "operand_b_params": b_params or {}}))


def screening_presets():
    return [
        {"id": "trend_momentum", "name": "Trend and momentum", "description": "Close above EMA 50 and RSI above 50.",
         "timeframe": "1D", "logical_operator": "AND", "conditions": [
             _rule(OperandType.CLOSE, OperandType.EMA, b_params={"period": 50}),
             _rule(OperandType.RSI, OperandType.CONSTANT, b_params={"value": 50})]},
        {"id": "ema_crossover", "name": "EMA crossover", "description": "EMA 20 crosses above EMA 50 on the latest closed candle.",
         "timeframe": "1D", "logical_operator": "AND", "conditions": [
             _rule(OperandType.EMA, OperandType.EMA, comparison=ComparisonOperator.CROSSES_ABOVE,
                   a_params={"period": 20}, b_params={"period": 50})]},
    ]
