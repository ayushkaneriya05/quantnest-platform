"""Typed boundary for validated, object-shaped API input."""
from collections.abc import Callable
from typing import Any, cast

from rest_framework.fields import Field
from rest_framework.serializers import BaseSerializer


def validate_value(field: Field, value: Any) -> Any:
    """DRF fields accept arbitrary input and own conversion and validation."""
    validator = cast(Callable[[Any], Any], field.run_validation)
    return validator(value)


def validate_data(serializer: BaseSerializer) -> dict[str, Any]:
    """Validate once and return an object's fields, never list-serializer data."""
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    if not isinstance(values, dict):
        raise TypeError('This API operation requires object-shaped serializer data.')
    return values


def serialize_object(serializer: BaseSerializer) -> dict[str, Any]:
    """Keep single-resource stream events separate from paginated collections."""
    data = serializer.data
    if not isinstance(data, dict):
        raise TypeError('This event requires one serialized object.')
    return data
