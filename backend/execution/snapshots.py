"""Explicit JSON encoding of an account checkpoint; no executable serialized objects."""
from dataclasses import fields
from datetime import date, datetime
from decimal import Decimal

from .types import Account, Contract, EntryLot, Order, Position

# Only these local value types can be restored. Provider payloads never enter a
# checkpoint until their broker adapter has validated and normalized them.
RECORDS = {record.__name__: record for record in (Account, Contract, EntryLot, Order, Position)}


def encode(value):
    record = RECORDS.get(type(value).__name__)
    if record is type(value):
        return {'record': record.__name__, 'fields': {field.name: encode(getattr(value, field.name)) for field in fields(value) if field.init}}
    if isinstance(value, Decimal):
        return {'decimal': str(value)}
    if isinstance(value, datetime):
        return {'datetime': value.isoformat()}
    if isinstance(value, date):
        return {'date': value.isoformat()}
    if isinstance(value, dict):
        return {'mapping': [[encode(key), encode(item)] for key, item in value.items()]}
    if isinstance(value, tuple):
        return {'tuple': [encode(item) for item in value]}
    if isinstance(value, list):
        return [encode(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f'Unsupported checkpoint value: {type(value).__name__}')


def decode(value):
    if isinstance(value, list):
        return [decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    if 'record' in value:
        return RECORDS[value['record']](**{key: decode(item) for key, item in value['fields'].items()})
    if 'decimal' in value:
        return Decimal(value['decimal'])
    if 'datetime' in value:
        return datetime.fromisoformat(value['datetime'])
    if 'date' in value:
        return date.fromisoformat(value['date'])
    if 'mapping' in value:
        return {decode(key): decode(item) for key, item in value['mapping']}
    if 'tuple' in value:
        return tuple(decode(item) for item in value['tuple'])
    raise ValueError('Unknown account checkpoint value.')
