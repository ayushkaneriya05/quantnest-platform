"""One cold-path contract for Studio, research tools and configuration readers.

This package has no dependency on models, views, providers or execution workers.
The common enum endpoint publishes it once through the existing frontend cache.
"""
from copy import deepcopy

from common import enums

from .configuration import DOCUMENT_VERSIONS, STAGES, configuration
from .expressions import specification as expression_specification
from .operands import specification as operand_specification


def studio_specification(*, operand_types=None):
    """Return a caller-owned catalog, optionally restricted for an AI schema tool."""
    conditions = {**operand_specification(), 'stages': deepcopy(STAGES), 'operators': expression_specification()}
    if operand_types is not None:
        selected = set(operand_types)
        conditions['operands'] = {key: value for key, value in conditions['operands'].items() if key in selected}
        conditions['groups'] = [{**group, 'operands': [key for key in group['operands'] if key in selected]}
                                for group in conditions['groups']]
    result = {'metadata_version': 1, 'document_versions': dict(DOCUMENT_VERSIONS),
              **configuration(), 'conditions': conditions}
    operators = conditions['operators']
    result['fields']['op'] = {'label': 'Operation', 'choices': [
        *operators['nodes'], *operators['numeric'], *operators['windows'], *operators['logic']]}
    result['fields']['type'] = {'label': 'Operand', 'choice_ref': 'OperandType'}
    result['fields']['ddof'] = {'label': 'Variance divisor', 'choices': operators['variance_divisors']}
    return result


def choice_metadata(specification):
    """Project only referenced shared vocabularies for the run-scoped AI tool."""
    names = {'OperandType', 'ComparisonOperator', 'LogicalOperator', 'RuleType'}

    def visit(value):
        if isinstance(value, dict):
            for key in ('choice_ref', 'enumKey'):
                if key in value:
                    names.add(value[key])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(specification)
    return {name: [{'name': item.name, 'value': item.value, 'label': item.label}
                   for item in getattr(enums, name)] for name in sorted(names)
            if name not in specification['conditions']['choices']}
