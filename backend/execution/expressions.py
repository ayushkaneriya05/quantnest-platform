"""Bounded authoring trees compiled to scalar slots, never evaluated as user code.

Numerical leaves reuse the existing indicator graph. Boolean instructions run
after *all* comparisons advance, so an AND/OR cannot hide a crossing event.
"""
import ast
from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite, nan
import operator

from common.enums import ComparisonOperator, OperandType


from strategies.specification.expressions import (
    MAX_NODES, MAX_DEPTH, MAX_WINDOW, WINDOWS, VARIANCE_WINDOWS,
    NUMERIC, LOGIC, MAX_ARITHMETIC_NODES, MAX_ARITHMETIC_DEPTH,
)

# Functions are bound during compilation, never looked up through UI metadata
# during market evaluation. Vocabulary/arity are owned by the specification.
NUMERIC_FUNCTIONS = {'add': operator.add, 'subtract': operator.sub, 'multiply': operator.mul,
                     'divide': operator.truediv, 'min': min, 'max': max, 'abs': abs, 'negate': operator.neg}


def validate_tree(root, validate_input=None, *, expected='boolean', captures=None, expressions=None):
    """Return an owned, normalized tree; reject ignored fields and wrong types."""
    count = 0
    expanding = set()

    def visit(node, expected, depth, path):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError(f'{path}: expression exceeds the supported size or nesting depth.')
        if not isinstance(node, dict):
            raise ValueError(f'{path}: expected an expression object.')
        op = node.get('op')
        allowed = {'op', 'args'}
        if op == 'expression' and expected == 'number':
            allowed = {'op', 'name'}
            name = node.get('name')
            if not isinstance(name, str) or name not in (expressions or {}):
                raise ValueError(f'{path}: named formula {name!r} does not exist.')
            if name in expanding:
                raise ValueError(f'{path}: circular formula reference {name!r}.')
            expanding.add(name)
            # Validate expanded cost and context, but retain a reference in the
            # document. Saving never duplicates a formula into every use site.
            visit(expressions[name], 'number', depth + 1, f'{path}.{name}')
            expanding.remove(name)
            result = dict(op=op, name=name)
        elif op == 'capture' and expected == 'number':
            allowed = {'op', 'setup', 'name'}
            reference = (node.get('setup'), node.get('name'))
            if not all(isinstance(value, str) and value for value in reference):
                raise ValueError(f'{path}: choose a named value from a setup.')
            if captures is not None and reference not in captures:
                raise ValueError(f'{path}: captured value does not exist in this context.')
            result = dict(op=op, setup=reference[0], name=reference[1])
        elif op == 'input' and expected == 'number':
            allowed = {'op', 'type', 'params', 'timeframe', 'source'}
            kind = OperandType(node.get('type'))
            if node.get('source', 'signal') not in ('signal', 'trade'):
                raise ValueError(f'{path}: choose the signal or traded-contract source.')
            params = node.get('params', {})
            if not isinstance(params, dict):
                raise ValueError(f'{path}: operand parameters must be an object.')
            result = dict(op=op, type=kind, params=params, timeframe=node.get('timeframe'), source=node.get('source', 'signal'))
            if validate_input:
                result = validate_input(result)
        elif op in WINDOWS and expected == 'number':
            allowed.add('bars')
            bars, args = node.get('bars'), node.get('args')
            if type(bars) is not int or not 1 <= bars <= MAX_WINDOW:
                raise ValueError(f'{path}: bars must be between 1 and {MAX_WINDOW}.')
            if not isinstance(args, list) or len(args) != 1:
                raise ValueError(f'{path}: {op} requires one numerical expression.')
            result = dict(op=op, bars=bars, args=[visit(args[0], 'number', depth + 1, f'{path}.args[0]')])
            if op in VARIANCE_WINDOWS:
                allowed.add('ddof')
                ddof = node.get('ddof', 0)
                if type(ddof) is not int or ddof not in (0, 1) or bars <= ddof:
                    raise ValueError(f'{path}: choose population (0) or sample (1) variance and more bars than ddof.')
                result['ddof'] = ddof
        elif op in NUMERIC and expected == 'number':
            args = node.get('args')
            if not isinstance(args, list) or len(args) != NUMERIC[op][1]:
                raise ValueError(f'{path}: {op} requires {NUMERIC[op][1]} numerical inputs.')
            result = dict(op=op, args=[visit(arg, 'number', depth + 1, f'{path}.args[{i}]') for i, arg in enumerate(args)])
        elif op == 'compare' and expected == 'boolean':
            allowed = {'op', 'comparison', 'left', 'right'}
            result = dict(op=op, comparison=ComparisonOperator(node.get('comparison')),
                          left=visit(node.get('left'), 'number', depth + 1, f'{path}.left'),
                          right=visit(node.get('right'), 'number', depth + 1, f'{path}.right'))
        elif op in LOGIC and expected == 'boolean':
            args = node.get('args')
            if not isinstance(args, list) or not args or op == 'not' and len(args) != 1:
                raise ValueError(f'{path}: {op} requires {"one condition" if op == "not" else "at least one condition"}.')
            result = dict(op=op, args=[visit(arg, 'boolean', depth + 1, f'{path}.args[{i}]') for i, arg in enumerate(args)])
            if op == 'at_least':
                allowed.add('count')
                k = node.get('count')
                if type(k) is not int or not 1 <= k <= len(args):
                    raise ValueError(f'{path}: count must be between 1 and the number of conditions.')
                result['count'] = k
        else:
            raise ValueError(f'{path}: unsupported {expected} operator {op!r}.')
        extra = set(node) - allowed
        if extra:
            raise ValueError(f'{path}: unknown fields {sorted(extra)}.')
        return result

    return visit(root, expected, 0, 'condition')


def input_requirements(root, expressions=None, _trail=(), _extra=0):
    """Propagate native-bar lookback through nested windows during preparation."""
    if root['op'] == 'input':
        yield root, _extra
    elif root['op'] == 'expression':
        name = root['name']
        if name in _trail or len(_trail) >= MAX_DEPTH or name not in (expressions or {}):
            raise ValueError(f'Invalid or circular formula reference {name!r}.')
        yield from input_requirements(expressions[name], expressions, (*_trail, name), _extra)
    elif root['op'] == 'capture':
        return
    elif root['op'] == 'compare':
        yield from input_requirements(root['left'], expressions, _trail, _extra)
        yield from input_requirements(root['right'], expressions, _trail, _extra)
    else:
        if root['op'] in WINDOWS:
            _extra += root['bars'] if root['op'] in ('lag', 'return_pct') else root['bars'] - 1
        for child in root['args']:
            yield from input_requirements(child, expressions, _trail, _extra)


def inputs(root, expressions=None):
    """Input leaves for validation; window depth belongs to the history planner."""
    for item, _ in input_requirements(root, expressions):
        yield item


@dataclass(frozen=True, slots=True)
class Calculation:
    # Each instruction reads earlier slots. Callable objects are compiler-owned.
    instructions: tuple
    result: int = -1

    def evaluate(self, values):
        slots = list(values)
        for function, indexes in self.instructions:
            if function is None:
                slots.append(indexes[0])  # Compiler-owned literal, not a slot index.
                continue
            args = [slots[index] for index in indexes]
            try:
                result = function(*args) if all(isfinite(x) for x in args) else nan
                slots.append(result if isfinite(result) else nan)
            except (ArithmeticError, ValueError):
                slots.append(nan)
        return slots[self.result]


# Text formulas share one bounded grammar between authoring and compilation.
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Constant, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.UAdd, ast.USub,
)


def parse_arithmetic_expression(expression: str, variable_names: Iterable[str] = ()) -> ast.expr:
    """Return a validated expression body, or raise ValueError for invalid syntax.

    The compiler lowers this tree into scalar instructions during preparation.
    Calls, attributes and undeclared names are never accepted.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError('Enter a non-empty arithmetic expression.')
    try:
        tree = ast.parse(expression.strip(), mode='eval')
    except (SyntaxError, ValueError):
        raise ValueError('Enter a valid arithmetic expression.') from None

    allowed_names = set(variable_names)
    pending, count = [(tree, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        if count > MAX_ARITHMETIC_NODES or depth > MAX_ARITHMETIC_DEPTH:
            raise ValueError('Arithmetic expression is too large; split it into smaller conditions.')
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError('Only numeric constants, configured variables and arithmetic operators are supported.')
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            raise ValueError(f'Unknown expression variable: {node.id}.')
        if isinstance(node, ast.Constant) and (isinstance(node.value, bool) or not isinstance(node.value, (int, float))):
            raise ValueError('Expression constants must be numbers.')
        if isinstance(node, ast.Constant):
            try:
                finite = isfinite(node.value)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError('Expression constants must be finite numbers within the supported range.')
        pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    return tree.body


def compile_arithmetic(tree, variable_names):
    """Lower the existing validated formula grammar once during preparation.

    Keep every declared variable slot, including unused variables, so source
    stamps/warmup retain their recorded semantics after this optimization.
    """
    variables = {name: index for index, name in enumerate(variable_names)}
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                  ast.Div: operator.truediv, ast.Mod: operator.mod}
    instructions = []

    def visit(node):
        if isinstance(node, ast.Name):
            return variables[node.id]
        if isinstance(node, ast.Constant):
            instructions.append((None, (float(node.value),)))
        elif isinstance(node, ast.UnaryOp):
            index = visit(node.operand)
            if isinstance(node.op, ast.UAdd):
                return index
            instructions.append((operator.neg, (index,)))
        else:
            left, right = visit(node.left), visit(node.right)
            instructions.append((operations[type(node.op)], (left, right)))
        return len(variables) + len(instructions) - 1

    result = visit(tree)
    return Calculation(tuple(instructions), result)


def compile_numeric(node, operand, named=None, window=None):
    """Lower a tree into leaves plus a topologically ordered numerical program."""
    from .compiler import Operand
    if node['op'] in WINDOWS:
        return window(node)
    if node['op'] == 'expression':
        return named(node['name'])
    if node['op'] == 'capture':
        return Operand('', '', {}, capture=(node['setup'], node['name']))
    if node['op'] == 'input':
        return operand(node['type'], node['params'], node.get('timeframe'), node.get('source', 'signal'))
    leaves, expressions = [], []

    def collect(item):
        if item['op'] in ('input', 'capture', 'expression') or item['op'] in WINDOWS:
            index = len(leaves)
            leaves.append(compile_numeric(item, operand, named, window))
            return ('leaf', index)
        args = tuple(collect(arg) for arg in item['args'])
        index = len(expressions)
        expressions.append((NUMERIC_FUNCTIONS[item['op']], args))
        return ('node', index)

    collect(node)
    instructions = tuple((function, tuple(i if kind == 'leaf' else len(leaves) + i for kind, i in args))
                         for function, args in expressions)
    return Operand(OperandType.MATH_EXPRESSION, '', {},
                   variables=tuple((str(i), leaf) for i, leaf in enumerate(leaves)),
                   tick_sensitive=any(leaf.tick_sensitive for leaf in leaves), calculation=Calculation(instructions))


def compile_condition(root, operand, first_identity, named=None, window=None):
    """Compile comparisons and Boolean slots. Returns rules and slot program."""
    from .compiler import Rule
    rules, instructions = [], []

    def visit(node):
        op = node['op']
        if op == 'compare':
            rule = Rule(first_identity + len(rules) + 1, compile_numeric(node['left'], operand, named, window),
                        node['comparison'], compile_numeric(node['right'], operand, named, window))
            rules.append(rule)
            instructions.append(('rule', (len(rules) - 1,), 0))
        else:
            children = tuple(visit(child) for child in node['args'])
            instructions.append((op, children, node.get('count', 0)))
        return len(instructions) - 1

    visit(root)
    return tuple(rules), tuple(instructions)


def boolean_result(instructions, hits):
    """Three-valued logic: unavailable data never becomes true through NOT."""
    slots = []
    for op, indexes, count in instructions:
        if op == 'rule':
            result = hits[indexes[0]]
        else:
            args = [slots[index] for index in indexes]
            if op == 'not':
                result = None if args[0] is None else not args[0]
            else:
                required = len(args) if op == 'all' else 1 if op == 'any' else count
                yes, unknown = args.count(True), args.count(None)
                result = True if yes >= required else False if yes + unknown < required else None
        slots.append(result)
    return slots[-1]

