"""Contract terms on the preparation boundary; never queried on market ticks."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import is_aware

from common.enums import InstrumentType
from .models import ContractSpecification, Instrument

TERMS = ('lot_size', 'tick_size', 'qty_multiplier', 'qty_freeze', 'strike_price', 'expiry_date')
DERIVATIVES = (InstrumentType.FUTURE, InstrumentType.OPTION)


def record_observed_specifications(instruments, *, at, source):
    """Bulk-archive changed economic terms in the instrument sync transaction.

    Locking instrument rows orders concurrent syncs. Unchanged masters produce
    no revisions; current observations are never backdated into missing history.
    """
    instruments = [item for item in instruments if item.instrument_type in DERIVATIVES]
    if not instruments:
        return
    latest = {row.instrument_id: row for row in ContractSpecification.objects.filter(
        instrument_id__in=[item.pk for item in instruments], effective_at__lte=at).order_by('instrument_id', '-effective_at').distinct('instrument_id')}
    additions = []
    for item in instruments:
        values = {name: getattr(item, name) for name in TERMS}
        values['qty_freeze'] = values['qty_freeze'] or 0
        previous = latest.get(item.pk)
        if previous is None or any(values[name] != getattr(previous, name) for name in TERMS):
            row = ContractSpecification(instrument=item, effective_at=at, source=source, **values)
            row.clean_fields()
            additions.append(row)
    ContractSpecification.objects.bulk_create(additions, batch_size=2000)


@transaction.atomic
def import_specifications(document, *, dry_run=False):
    """Import explicit dated terms, never infer past economics from today's master.

    A batch is all-or-nothing. An identical effective revision is a no-op; a
    conflicting revision must be reviewed instead of overwriting evidence.
    Instrument locks serialize this with the master-sync upsert transaction.
    """
    if not isinstance(document, dict) or set(document) != {'schema_version', 'source', 'specifications'}:
        raise ValueError('Provide schema_version, source and specifications.')
    if type(document['schema_version']) is not int or document['schema_version'] != 1:
        raise ValueError('Unsupported specification schema_version; expected 1.')
    source, rows = document['source'], document['specifications']
    if not isinstance(source, str) or not source.strip() or len(source) > 500:
        raise ValueError('Provide a source reference of 1 to 500 characters.')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 5000:
        raise ValueError('Provide between 1 and 5000 contract specifications per batch.')
    fields = {'sym_ticker', 'effective_at', *TERMS}
    if any(not isinstance(row, dict) or set(row) != fields or
           not isinstance(row['sym_ticker'], str) for row in rows):
        raise ValueError(f'Each specification needs exactly these fields: {", ".join(sorted(fields))}.')
    instruments = {item.sym_ticker: item for item in Instrument.objects.select_for_update().filter(
        sym_ticker__in={row['sym_ticker'] for row in rows}).order_by('pk')}
    candidates, identities = [], set()
    for index, row in enumerate(rows, 1):
        try:
            instrument = instruments.get(row['sym_ticker'])
            if instrument is None or instrument.instrument_type not in DERIVATIVES:
                raise ValueError('Choose an existing derivative by its exact sym_ticker.')
            if not isinstance(row['effective_at'], str):
                raise ValueError('effective_at must be an ISO datetime with a timezone offset.')
            at = datetime.fromisoformat(row['effective_at'])
            if not is_aware(at):
                raise ValueError('effective_at must include a timezone offset.')
            if not isinstance(row['expiry_date'], str):
                raise ValueError('expiry_date must be an ISO date.')
            values = {'expiry_date': date.fromisoformat(row['expiry_date'])}
            for field in ('lot_size', 'qty_freeze'):
                if type(row[field]) is not int:
                    raise ValueError(f'{field} must be an integer.')
                values[field] = row[field]
            for field in ('tick_size', 'qty_multiplier', 'strike_price'):
                value = row[field]
                if field == 'strike_price' and value is None:
                    values[field] = None
                    continue
                if not isinstance(value, str):
                    raise ValueError(f'{field} must be a decimal string, preserving exact precision.')
                values[field] = Decimal(value)
                if not values[field].is_finite():
                    raise ValueError(f'{field} must be finite.')
            if instrument.instrument_type == InstrumentType.OPTION and (values['strike_price'] is None or values['strike_price'] <= 0):
                raise ValueError('An option specification needs a positive strike_price.')
            record = ContractSpecification(instrument=instrument, effective_at=at, source=source.strip(), **values)
            record.clean_fields()
            identity = (instrument.pk, at)
            if identity in identities:
                raise ValueError('Duplicate instrument/effective_at in this batch.')
            identities.add(identity)
            candidates.append(record)
        except (ValueError, InvalidOperation, ValidationError) as exc:
            raise ValueError(f'Specification {index} ({row["sym_ticker"]}): {exc}') from None
    existing = {(row.instrument_id, row.effective_at): row for row in ContractSpecification.objects.filter(
        instrument_id__in=[item.pk for item in instruments.values()],
        effective_at__in=[item.effective_at for item in candidates])}
    additions = []
    for record in candidates:
        previous = existing.get((record.instrument_id, record.effective_at))
        if previous is None:
            additions.append(record)
        elif any(getattr(previous, name) != getattr(record, name) for name in (*TERMS, 'source')):
            raise ValueError(f'{record.instrument.sym_ticker} already has different terms/source at {record.effective_at.isoformat()}. Existing evidence was not changed.')
    if not dry_run:
        ContractSpecification.objects.bulk_create(additions, batch_size=1000)
    return {'created': len(additions), 'unchanged': len(candidates) - len(additions)}


def historical_specification(instrument, start, end):
    """Require known terms throughout a derivative replay, with no guessed history.

    Corporate-action/specification transitions still require separate ranges.
    The backtest preparation boundary verifies sourced settlement coverage.
    """
    if instrument.instrument_type not in DERIVATIVES:
        return None
    from marketdata.calendar import MarketSessionCalendar
    zone = MarketSessionCalendar.for_instrument(instrument).zone
    if not is_aware(start) or not is_aware(end) or end <= start:
        raise ValueError('Historical contract ranges need increasing timezone-aware datetimes.')
    rows = instrument.specifications
    spec = rows.filter(effective_at__lte=start).order_by('-effective_at').first()
    if spec is None:
        raise ValueError(f'{instrument.name}: contract terms are not recorded for this start date. Import a sourced historical specification or choose a later range.')
    if rows.filter(effective_at__gt=start, effective_at__lte=end).exists():
        raise ValueError(f'{instrument.name}: contract terms change inside this range. Split the backtest at the specification change.')
    if spec.expiry_date is None:
        raise ValueError(f'{instrument.name}: the derivative expiry is missing from its specification.')
    if start.astimezone(zone).date() > spec.expiry_date:
        raise ValueError(f'{instrument.name}: the requested history starts after contract expiry.')
    return spec
