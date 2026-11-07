"""Strategy Studio's cold path: one document, validation and atomic version saves.

Every strategy and saved version uses the same canonical document.
Validation and compilation happen before execution, outside the market-event loop.
"""
from copy import deepcopy
from hashlib import sha256
import json
import re

from common.enums import CandleTimeframe, OperandType, RuleType
from strategies.specification.operands import POSITION_OPERANDS
from execution.expressions import validate_tree
from .specification.expressions import MAX_EXPRESSIONS
from .specification.configuration import AUTOMATIC, DOCUMENT_VERSIONS, LIMITS, SETUP_LIMITS, NAME_PATTERN, ROUTE_ID_PATTERN, STAGE_BY_TYPE


CONFIG_FIELDS = ('time_rule', 'entry_order_config', 'exit_order_config',
                 'position_sizing_rule', 'watchlist_instruments', 'rule_groups')


def default_definition():
    from .specification.configuration import new_document
    return new_document()


def document_from_snapshot(snapshot):
    """Extract the canonical document without modifying saved definitions."""
    if any(snapshot.get(key) != value for key, value in DOCUMENT_VERSIONS.items()):
        raise ValueError('Strategy data requires the canonical-definition migration.')
    return {name: deepcopy(snapshot[name]) for name in (*CONFIG_FIELDS, 'expressions', 'initial_risk', 'schema_version', 'semantics_version')}


def current_document(strategy):
    return document_from_snapshot(strategy.definition)


def revision(document):
    return sha256(json.dumps(document, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_definition(document):
    """Structural and semantic validation before compilation or history I/O."""
    from .serializers import (TimeRuleSerializer, PositionSizingRuleSerializer,
                              EntryOrderConfigSerializer, ExitOrderConfigSerializer, SizingOverrideSerializer)
    from .validation import validate_operand_parameters
    from instruments.models import Instrument

    if (not isinstance(document, dict) or type(document.get('schema_version')) is not int or
            type(document.get('semantics_version')) is not int or
            any(document[key] != value for key, value in DOCUMENT_VERSIONS.items())):
        raise ValueError('Use strategy schema_version 1 and semantics_version 1.')
    if set(document) - {'expressions', 'initial_risk'} != set(CONFIG_FIELDS) | {'schema_version', 'semantics_version'}:
        raise ValueError('The strategy document has missing or unsupported sections.')
    if len(json.dumps(document, allow_nan=False).encode()) > LIMITS['document_bytes']:
        raise ValueError('The strategy document is too large.')
    result = deepcopy(document)
    result.setdefault('expressions', {})
    result.setdefault('initial_risk', None)
    for key, cls in (('time_rule', TimeRuleSerializer), ('entry_order_config', EntryOrderConfigSerializer),
                     ('exit_order_config', ExitOrderConfigSerializer), ('position_sizing_rule', PositionSizingRuleSerializer)):
        if not isinstance(result[key], dict):
            raise ValueError(f'{key} must be an object.')
        values = dict(result[key])
        serializer = cls(data=values)
        extra = set(values) - {name for name, field in serializer.fields.items() if not field.read_only}
        if extra:
            raise ValueError(f'{key}: unsupported fields {sorted(extra)}.')
        serializer.is_valid(raise_exception=True)
        # Serializer representation keeps times and Decimal values JSON-safe.
        result[key] = dict(serializer.data)
    def normalize_input(item, *, allow_position):
        if not allow_position and item['type'] in POSITION_OPERANDS:
            raise ValueError('Entry conditions and reusable formulas cannot reference an open position.')
        if item.get('timeframe'):
            CandleTimeframe(item['timeframe'])
        from strategies.specification.operands import get_math_expression_operand_types
        item['params'] = validate_operand_parameters(item['type'], item['params'], 'params',
            math_variable_types=set(get_math_expression_operand_types(RuleType.EXIT if allow_position else RuleType.ENTRY)))
        if item['type'] in POSITION_OPERANDS:
            item['source'] = 'trade'
        if not allow_position and any(child.get('type') in POSITION_OPERANDS
                for child in item['params'].get('expression', {}).get('variables', {}).values()):
            raise ValueError('Entry formulas cannot reference an open position.')
        return item

    expressions = result['expressions']
    if (not isinstance(expressions, dict) or len(expressions) > MAX_EXPRESSIONS or
            any(not isinstance(name, str) or not re.fullmatch(NAME_PATTERN, name) for name in expressions)):
        raise ValueError(f'Use at most {MAX_EXPRESSIONS} formulas with names starting with a letter.')
    result['expressions'] = {name: validate_tree(tree,
        lambda item: normalize_input(item, allow_position=False), expected='number', captures=set(), expressions=expressions)
        for name, tree in expressions.items()}
    expressions = result['expressions']

    def risk_input(item):
        item = normalize_input(item, allow_position=False)
        if item['type'] != OperandType.CONSTANT and item['source'] != 'trade':
            raise ValueError('Initial risk must use traded-contract price points, not underlying signal prices.')
        return item

    if result['initial_risk'] is not None:
        result['initial_risk'] = validate_tree(result['initial_risk'], risk_input,
            expected='number', captures=set(), expressions=expressions)

    groups = result['rule_groups']
    if not isinstance(groups, list) or len(groups) > LIMITS['groups']:
        raise ValueError(f'Use at most {LIMITS["groups"]} condition groups.')
    identities = set()
    capture_references = set()
    for group in groups:
        setup = group.get('setup') if isinstance(group, dict) else None
        if setup is not None:
            if not isinstance(setup, dict) or not isinstance(setup.get('captures'), dict):
                raise ValueError('A setup needs a named capture object.')
            if group.get('rule_type') != RuleType.ENTRY:
                raise ValueError('Setups arm entries. Exit rules use captured values without arming again.')
            if not isinstance(group.get('id'), str):
                raise ValueError('A setup needs a stable group ID.')
            if group.get('is_active', True):
                capture_references.update((group['id'], name) for name in setup['captures'])
    active_entries = [group for group in groups if isinstance(group, dict) and
                      group.get('rule_type') == RuleType.ENTRY and group.get('is_active', True)]
    if any(group.get('setup') for group in active_entries) and len(active_entries) != 1:
        raise ValueError('A stateful entry uses one active entry group. Combine its filters inside that setup.')
    for group in groups:
        if not isinstance(group, dict) or set(group) - {'id', 'name', 'rule_type', 'priority', 'is_active', 'condition', 'setup'}:
            raise ValueError('Invalid condition group fields.')
        identity = group.get('id')
        if not isinstance(identity, str) or not identity or len(identity) > LIMITS['group_id_length'] or identity in identities:
            raise ValueError('Each condition group needs a unique stable ID.')
        identities.add(identity)
        kind = RuleType(group.get('rule_type'))
        if type(group.get('is_active', True)) is not bool:
            raise ValueError('Group is_active must be true or false.')
        if type(group.get('priority', 1)) is not int or group.get('priority', 1) < 1:
            raise ValueError('Group priority must be a positive integer.')
        if not isinstance(group.get('name', ''), str) or len(group.get('name', '')) > LIMITS['group_name_length']:
            raise ValueError(f'Group name must contain at most {LIMITS["group_name_length"]} characters.')

        def validate_input(item):
            return normalize_input(item, allow_position=STAGE_BY_TYPE[kind]['position'])

        allowed_captures = ({(identity, name) for name in (group.get('setup') or {}).get('captures', {})}
                            if kind == RuleType.ENTRY else capture_references)
        group['condition'] = validate_tree(group.get('condition'), validate_input, captures=allowed_captures, expressions=expressions)
        setup = group.get('setup')
        if setup is not None:
            if set(setup) != {'arm', 'invalidate', 'captures', 'steps', 'timeframe', 'expires_after_bars'}:
                raise ValueError('Provide the complete setup: arm, captures, steps, invalidate, timeframe and expiry.')
            CandleTimeframe(setup['timeframe'])
            if type(setup['expires_after_bars']) is not int or not 1 <= setup['expires_after_bars'] <= SETUP_LIMITS['expiry_bars']:
                raise ValueError(f'Setup expiry must be between 1 and {SETUP_LIMITS["expiry_bars"]} native bars.')
            if not isinstance(setup['steps'], list) or len(setup['steps']) > SETUP_LIMITS['steps']:
                raise ValueError(f'A setup supports at most {SETUP_LIMITS["steps"]} intermediate confirmation steps.')
            if len(setup['captures']) > SETUP_LIMITS['captures'] or any(not isinstance(name, str) or not re.fullmatch(NAME_PATTERN, name) for name in setup['captures']):
                raise ValueError(f'Use at most {SETUP_LIMITS["captures"]} captured values with names starting with a letter.')
            setup['arm'] = validate_tree(setup['arm'], validate_input, captures=set(), expressions=expressions)
            setup['captures'] = {name: validate_tree(tree, validate_input, expected='number', captures=set(), expressions=expressions)
                                 for name, tree in setup['captures'].items()}
            setup['steps'] = [validate_tree(tree, validate_input, captures=allowed_captures, expressions=expressions) for tree in setup['steps']]
            if setup['invalidate'] is not None:
                setup['invalidate'] = validate_tree(setup['invalidate'], validate_input, captures=allowed_captures, expressions=expressions)

    def uses_reward_risk(value):
        if isinstance(value, dict):
            return value.get('type') == OperandType.POSITION_RR_RATIO or any(uses_reward_risk(item) for item in value.values())
        return isinstance(value, list) and any(uses_reward_risk(item) for item in value)

    inferred_risk = result['initial_risk'] is None and uses_reward_risk(result['rule_groups'])
    watches = result['watchlist_instruments']
    if not isinstance(watches, list) or any(not isinstance(w, dict) or type(w.get('instrument_id')) is not int for w in watches):
        raise ValueError('Choose instruments from the contract catalog.')
    ids = [w['instrument_id'] for w in watches]
    instruments = Instrument.objects.in_bulk(ids)
    if set(instruments) != set(ids):
        raise ValueError('Choose existing instruments.')
    signal_ids = [watch.get('signal_instrument_id', watch['instrument_id']) for watch in watches]
    if any(type(identity) is not int for identity in signal_ids):
        raise ValueError('Choose the signal instrument from the catalog.')
    signals = Instrument.objects.in_bulk(set(signal_ids) - set(ids)) | instruments
    routes_seen = set()
    for watch in watches:
        if set(watch) - {'instrument_id', 'instrument_symbol', 'instrument_name', 'execution_routes', 'source_id', 'route_id', 'leg_id', 'signal_instrument_id', 'signal_instrument_name', 'contract_selection'}:
            raise ValueError('Unsupported instrument binding fields.')
        instrument = instruments[watch['instrument_id']]
        signal_id = watch.get('signal_instrument_id', instrument.pk)
        signal = signals.get(signal_id)
        if signal is None:
            raise ValueError('The signal instrument no longer exists.')
        if 'contract_selection' in watch:
            from instruments.selection import SelectionPolicy
            SelectionPolicy.parse(watch['contract_selection'])
            if (signal.pk != instrument.pk or instrument.exchange not in AUTOMATIC['exchanges']
                    or instrument.instrument_type not in AUTOMATIC['underlying_types']):
                raise ValueError('An automatic route uses one NSE/BSE stock or index as its underlying and signal source.')
        if (signal.pk != instrument.pk or 'contract_selection' in watch) and inferred_risk:
            raise ValueError('Separate signal and traded markets need an explicit traded-contract initial risk for reward/risk rules.')
        watch['signal_instrument_id'], watch['signal_instrument_name'] = signal.pk, signal.name
        watch['instrument_symbol'], watch['instrument_name'] = instrument.sym_ticker, instrument.name
        for key, value in (('source_id', f'instrument-{instrument.pk}'), ('route_id', f'direct-{instrument.pk}'), ('leg_id', 'primary')):
            chosen = watch.get(key, value)
            if not isinstance(chosen, str) or not re.fullmatch(ROUTE_ID_PATTERN, chosen):
                raise ValueError('Source, route and leg identities must start with a letter and contain at most 80 letters, numbers, dashes or underscores.')
            watch[key] = chosen
        route_key = watch['route_id'], watch['leg_id']
        if route_key in routes_seen:
            raise ValueError('Each route/leg identity must be unique.')
        routes_seen.add(route_key)
        overrides = watch.get('execution_routes', [])
        if not isinstance(overrides, list) or len(overrides) > LIMITS['sizing_overrides_per_contract']:
            raise ValueError('Each contract supports one sizing override.')
        for override in overrides:
            if not isinstance(override, dict) or set(override) - {'override_sizing', 'sizing_method', 'fixed_quantity', 'capital_percentage', 'quantity_unit'}:
                raise ValueError('Unsupported sizing override fields.')
            serializer = SizingOverrideSerializer(data=override)
            serializer.is_valid(raise_exception=True)
            override.update(serializer.data)
        if 'contract_selection' in watch:
            from instruments.services import InstrumentResolver
            from common.enums import QuantityType
            sizing = InstrumentResolver.sizing_for(watch, result['position_sizing_rule'])
            if sizing['sizing_method'] == QuantityType.FIXED and sizing.get('quantity_unit') != AUTOMATIC['fixed_sizing_unit']:
                raise ValueError('Automatic contracts require Lots for fixed sizing.')
    return result


def compile_preview(strategy, document):
    """Explain dependencies without fetching provider data or submitting orders."""
    from execution.compiler import compile_strategy
    from marketdata.calendar import MarketSessionCalendar
    from instruments.models import Instrument
    from .services import StrategySnapshotService
    config = {**({} if strategy.pk is None else StrategySnapshotService._serialize_strategy(strategy)),
              'strategy_type': strategy.strategy_type, **document}
    instruments = Instrument.objects.in_bulk([w['instrument_id'] for w in document['watchlist_instruments']])
    # An empty watchlist is a valid draft; use the existing NSE cash calendar for
    # numerical validation only. Deployment still requires actual instruments.
    from common.enums import Exchange, FyersSegment
    signal_ids = [watch.get('signal_instrument_id', watch['instrument_id']) for watch in document['watchlist_instruments']]
    signals = Instrument.objects.in_bulk(signal_ids)
    calendars = {(instruments[watch['instrument_id']].exchange,
                  FyersSegment.EQUITY_DERIVATIVES if watch.get('contract_selection') else instruments[watch['instrument_id']].segment,
                  signals[watch.get('signal_instrument_id', watch['instrument_id'])].exchange,
                  signals[watch.get('signal_instrument_id', watch['instrument_id'])].segment)
                 for watch in document['watchlist_instruments']} or {(Exchange.NSE, FyersSegment.CAPITAL_MARKET, Exchange.NSE, FyersSegment.CAPITAL_MARKET)}
    summaries = []
    for exchange, segment, signal_exchange, signal_segment in sorted(calendars):
        program = compile_strategy(config, 0, calendar=MarketSessionCalendar.for_exchange(exchange, segment),
                                   signal_calendar=MarketSessionCalendar.for_exchange(signal_exchange, signal_segment)).for_live()
        summaries.append({'exchange': exchange, 'segment': segment,
                          'signal_exchange': signal_exchange, 'signal_segment': signal_segment,
                          'history_bars': program.counts,
                          'source_candles': program.sources, 'shared_features': len(program.features),
                          'comparisons': sum(len(group.rules) + (sum(len(part.rules) for part in
                              (group.setup.arm, *group.setup.steps, group.setup.invalidate) if part is not None)
                              if group.setup else 0) for group in program.groups),
                          'uses_live_ticks': any(g.tick_sensitive for g in program.groups),
                          'stateful_setups': sum(g.setup is not None for g in program.groups)})
        summaries[-1]['input_history_bars'] = {role: values[0] for role, values in program.market_inputs.items()}
        summaries[-1]['input_features'] = {role: len(values[2]) for role, values in program.market_inputs.items()}
    return {'markets': summaries, 'instrument_count': len(instruments),
            'checks': ['Expression types', 'Indicator parameters', 'Timeframe dependencies'],
            'note': 'Compilation only. Data availability, contract eligibility and funds are checked when starting work.'}

