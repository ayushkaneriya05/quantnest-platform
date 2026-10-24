"""Shared arithmetic grammar for rule validation and execution compilation."""
import ast
from collections.abc import Iterable


_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Constant, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.UAdd, ast.USub,
)

def parse_arithmetic_expression(expression: str, variable_names: Iterable[str] = ()) -> ast.expr:
    """Return a validated expression body, or raise ValueError for invalid syntax.

    The compiler executes this tree directly; it must not parse the text again
    after validation. Calls, attributes and undeclared names are never accepted.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError('Enter a non-empty arithmetic expression.')
    try:
        tree = ast.parse(expression.strip(), mode='eval')
    except (SyntaxError, ValueError):
        raise ValueError('Enter a valid arithmetic expression.') from None

    allowed_names = set(variable_names)
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError('Only numeric constants, configured variables and arithmetic operators are supported.')
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            raise ValueError(f'Unknown expression variable: {node.id}.')
        if isinstance(node, ast.Constant) and (isinstance(node.value, bool) or not isinstance(node.value, (int, float))):
            raise ValueError('Expression constants must be numbers.')
    return tree.body
