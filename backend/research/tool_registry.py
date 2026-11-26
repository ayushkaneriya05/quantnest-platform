"""One registry supplies tool schemas, validation, handlers and evidence projections."""
import hashlib
import json
import logging
import time
from functools import lru_cache

import fastjsonschema
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import ACTIVE_RUN_STATUSES, ResearchRun
from .validation import json_data

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def registry():
    from common.enums import CandleTimeframe, Exchange, InstrumentType
    from . import tools
    from .resources import find_resources

    string = {'type': 'string'}
    identity = {'type': 'integer', 'minimum': 1}
    ids = {'type': 'array', 'items': identity, 'uniqueItems': True}
    timeframe = {'type': 'string', 'enum': CandleTimeframe.values}
    registered = {}

    def add(name, handler, description, properties, required=()):
        parameters = {'type': 'object', 'properties': properties,
                      'required': list(required), 'additionalProperties': False}
        registered[name] = {'definition': {'name': name, 'description': description, 'parameters': parameters},
                            'handler': handler, 'validate': fastjsonschema.compile(parameters)}

    add('find_resources', find_resources,
        'Find catalog instruments or your own strategies, backtests and named watchlists. Page through results. Instruments need not be attached before analysis. Use exact sym_ticker for identity; indices are analysis inputs, not orderable securities.',
        {'kind': {'type': 'string', 'enum': ['instruments', 'strategies', 'backtests', 'watchlists']},
         'query': string, 'page': identity, 'exchange': {'type': 'string', 'enum': Exchange.values},
         'instrument_type': {'type': 'string', 'enum': InstrumentType.values}, 'include_expired': {'type': 'boolean'}}, ['kind'])
    add('analyze_market', tools.handle_market,
        'Analyze, compare or screen catalog instruments or an owned watchlist. Optional condition uses the canonical Studio boolean expression tree; indicators are named numeric expressions. All numeric market calculations use completed candles; quotes are reported separately. With no conditions, return observations without a dummy comparison. For large sets use page and page_size until next_page is null.',
        {'instrument_ids': ids, 'watchlist_id': identity, 'timeframe': timeframe,
         'condition': {'type': 'object'}, 'expressions': {'type': 'object'},
         'indicators': {'type': 'array', 'items': {'type': 'object', 'properties': {
             'name': {'type': 'string', 'minLength': 1}, 'expression': {'type': 'object'}},
             'required': ['name', 'expression'], 'additionalProperties': False}},
         'mode': {'type': 'string', 'enum': ['analyze', 'compare', 'screen']},
         'page': identity, 'page_size': {'type': 'integer', 'minimum': 1, 'maximum': 25},
         'as_of': {'type': 'string', 'format': 'date-time'}})
    add('get_strategy_snapshot', tools.handle_get_strategy_snapshot,
        'Read one of your strategies, current configuration or a specified saved version. An attachment is optional.',
        {'strategy_id': identity, 'version_number': identity})
    add('get_backtest_reports', tools.handle_get_backtest_reports,
        'Read one or several owned backtests, their recorded status, actual metrics, costs, fills, diagnostics and configuration differences. Incomplete runs are status reports, not performance evidence.',
        {'backtest_ids': ids, 'page': identity, 'page_size': {'type': 'integer', 'minimum': 1, 'maximum': 25}})
    add('get_execution_review', tools.handle_get_execution_review,
        'Review recorded Terminal/Paper/Live execution. Supply review.filters with source TERMINAL/PAPER/LIVE and optional date_from, date_to, account_id, strategy_id, instrument_id or search. Optional trade_id selects a close. Saved notes are included only when include_notes is explicitly true. Without review use attached execution context.',
        {'review': {'type': 'object'}})
    add('get_rule_schema', tools.handle_get_rule_schema,
        'Read the current canonical StrategyStudio specification, default document and parameter definitions for requested operands. Use before composing unfamiliar rules. Supports the same expression trees, contract policies, sizing and schedule as Studio.',
        {'operand_types': {'type': 'array', 'items': string}})
    add('validate_strategy_draft', tools.handle_validate_strategy_draft,
        'Validate and compile a complete canonical Studio draft. Include name, description, strategy_type, market_type, exchange, instrument_type and the document fields from get_rule_schema. It may use fixed contracts, supported automatic expiry/strike policies, signal/trade inputs, named formulas, capture/confirmation, sizing and schedules. This validates a proposal; it does not save or deploy it.',
        {'draft': {'type': 'object'}}, ['draft'])
    add('get_conversation_evidence', tools.handle_get_conversation_evidence,
        'Find earlier instructions/answers in this conversation using query and pagination. Or provide run_id and evidence_id to retrieve one earlier artifact, retaining its original observation time.',
        {'query': string, 'page': identity, 'run_id': identity, 'evidence_id': string})
    add('research_web', tools.handle_research_web,
        'Research current financial facts, announcements, regulations or supplied public URLs. Returns provider-grounded sources and an observation time. Use market tools for numerical prices and indicators. Search charges may be additional to token usage.',
        {'query': string, 'urls': {'type': 'array', 'items': {'type': 'string', 'format': 'uri'}}}, ['query'])
    return registered


def _compact_data(data):
    """Full charts stay in paged Django evidence; the model receives calculated values."""
    if 'rows' in data:
        data = {**data, 'rows': [{key: value for key, value in row.items() if key not in {'chart', 'coverage'}} for row in data['rows']]}
    data = {key: value for key, value in data.items() if key not in {'largest_winners', 'largest_losers'}}
    if 'reports' in data:
        data = {**data, 'reports': [_compact_data(report) for report in data['reports']]}
    return data


def compact_evidence(evidence):
    from .evidence import hydrate_evidence
    data = _compact_data(hydrate_evidence(evidence)['data'])
    return {key: value for key, value in {**evidence, 'data': data}.items() if key not in {'cache_key', 'arguments'}}


def tool_definitions(run):
    # Discovery makes every capability accessible without attachment-based gates.
    return [tool['definition'] for tool in registry().values()]


def execute_tool(run, name, arguments):
    from .services import publish_run
    tool = registry().get(name)
    if tool is None:
        raise ValidationError('Unknown research capability.')
    try:
        tool['validate'](arguments)
    except fastjsonschema.JsonSchemaException as exc:
        raise ValidationError(str(exc)) from None
    key = hashlib.sha256(json.dumps([name, arguments], sort_keys=True).encode()).hexdigest()
    with transaction.atomic():
        current = ResearchRun.objects.select_for_update().get(pk=run.pk)
        if current.status not in ACTIVE_RUN_STATUSES:
            raise ValidationError('Research was cancelled.')
        if current.started_at and (timezone.now() - current.started_at).total_seconds() >= settings.RESEARCH_TIMEOUT_SECONDS:
            raise ValidationError('Research deadline reached; return the evidence already collected.')
        cached = next((item for item in current.evidence if item.get('cache_key') == key), None)
        if cached:
            return {**cached, 'reused': True}
        current.tool_attempts += 1
        current.save(update_fields=['tool_attempts'])
        run = current
    started = time.monotonic()
    try:
        calculated = json_data(tool['handler'](run, arguments))
    except (ValueError, KeyError, TypeError) as exc:
        raise ValidationError(f'Invalid {name} arguments: {exc}') from None
    finally:
        logger.info('Research tool run=%s tool=%s duration_ms=%d', run.pk, name, (time.monotonic() - started) * 1000)
    with transaction.atomic():
        current = ResearchRun.objects.select_for_update().get(pk=run.pk)
        if current.status not in ACTIVE_RUN_STATUSES:
            raise ValidationError('Research was cancelled.')
        evidence = {'tool': name, 'arguments': json_data(arguments), **calculated,
            'evidence_id': f'E{len(current.evidence) + 1}', 'cache_key': key,
            'source_run_id': calculated.get('source_run_id', run.pk),
            'source_as_of': calculated.get('source_as_of', run.as_of.isoformat())}
        from .evidence import store_evidence
        evidence = store_evidence(current, evidence)
        current.evidence = [*current.evidence, evidence]
        current.progress_message = f'Completed {name.replace("_", " ")}'
        current.revision += 1
        current.save(update_fields=['evidence', 'progress_message', 'revision', 'updated_at'])
        publish_run(current)
    return evidence
