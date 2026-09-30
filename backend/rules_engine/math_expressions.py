import ast


_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Constant, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.UAdd, ast.USub,
)
def is_safe_arithmetic_expression(expression, variable_names=()):
    """Allow arithmetic over configured variables and numeric constants only."""
    if not isinstance(expression, str) or not expression.strip():
        return False
    try:
        tree = ast.parse(expression, mode='eval')
    except (SyntaxError, ValueError):
        return False

    allowed_names = set(variable_names or ())
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            return False
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            return False
        if isinstance(node, ast.Constant) and (isinstance(node.value, bool) or not isinstance(node.value, (int, float))):
            return False
    return True
