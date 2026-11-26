"""Optional starting attachments; tools can discover further owned resources."""
import json

from backtesting.models import BacktestRun
from backtesting.services import backtest_configuration
from common.enums import CandleTimeframe
from django.shortcuts import get_object_or_404
from instruments.models import Instrument
from rest_framework.exceptions import ValidationError
from strategies.models import Strategy
from strategies.services import StrategySnapshotService

from .models import ResearchRun

CONTEXT_FIELDS = ('strategy_id', 'backtest_ids', 'instrument_ids', 'timeframe', 'watchlist_id',
                  'screen', 'source_run_id', 'execution_review')
SAVED_CONTEXT_FIELDS = (*CONTEXT_FIELDS, 'watchlist_name', 'instruments', 'execution_evidence')


def selected_instruments(ids):
    """Identity comes from the catalog; eligibility/data coverage belongs to each use."""
    ids = list(dict.fromkeys(ids))
    rows = Instrument.objects.filter(pk__in=ids).values(
        'id', 'symbol', 'name', 'sym_ticker', 'exchange', 'instrument_type', 'segment',
        'lot_size', 'expiry_date', 'strike_price', 'option_type', 'is_active')
    by_id = {row['id']: row for row in rows}
    if set(ids) - by_id.keys():
        raise ValidationError('An instrument is missing from the instrument catalog.')
    return [by_id[identity] for identity in ids]


def resolve_context(user, data, saved=None):
    context = {**(saved or {}), **{key: data[key] for key in CONTEXT_FIELDS if key in data}}
    review = context.get('execution_review')
    if review:
        if data.get('refresh') or not context.get('execution_evidence') or review != (saved or {}).get('execution_review'):
            from analytics.services import execution_review_context
            context['execution_review'], context['execution_evidence'] = execution_review_context(user, review)
    else:
        context.pop('execution_evidence', None)
    snapshot = None
    if context.get('strategy_id'):
        strategy = get_object_or_404(Strategy, pk=context['strategy_id'], user=user)
        snapshot = StrategySnapshotService._serialize_strategy(strategy)
    ids = list(dict.fromkeys(context.get('backtest_ids', [])))
    backtests = list(BacktestRun.objects.filter(pk__in=ids, user=user, status='COMPLETED'))
    if len(backtests) != len(ids):
        raise ValidationError('Attach only your completed backtests.')
    context['backtest_ids'] = ids
    context['backtests'] = [{'id': item.pk, 'name': item.name, 'snapshot': backtest_configuration(item)} for item in backtests]
    snapshot = snapshot or (context['backtests'][0]['snapshot'] if len(backtests) == 1 else None)
    context['strategy_snapshot'] = snapshot
    instruments = context.get('instrument_ids', [])
    context.pop('watchlist_name', None)
    if context.get('watchlist_id'):
        from trading.models import Watchlist
        watchlist = get_object_or_404(Watchlist, pk=context['watchlist_id'], user=user)
        context['watchlist_name'] = watchlist.name
        instruments = list(watchlist.instruments.values_list('pk', flat=True))
    elif not instruments and snapshot:
        instruments = list(dict.fromkeys(identity for watch in snapshot.get('watchlist_instruments', [])
            for identity in (watch.get('instrument_id'), watch.get('signal_instrument_id'), watch.get('target_underlying_id')) if identity))
    context['instruments'] = selected_instruments(instruments)
    context['instrument_ids'] = [item['id'] for item in context['instruments']]
    timeframe = context.get('timeframe') or (snapshot or {}).get('time_rule', {}).get('candle_timeframe') or CandleTimeframe.D1
    if timeframe not in CandleTimeframe.values:
        raise ValidationError('Select a supported research timeframe.')
    context['timeframe'] = timeframe
    if context.get('source_run_id'):
        get_object_or_404(ResearchRun, pk=context['source_run_id'], user=user, status=ResearchRun.Status.COMPLETED)
    return context


def service_payload(run):
    """Send recent context within the transport budget; older turns stay searchable."""
    from django.conf import settings
    from django.core import signing
    from .tool_registry import compact_evidence, tool_definitions

    history, size = [], 0
    previous = run.session.runs.filter(status=ResearchRun.Status.COMPLETED).exclude(pk=run.pk).order_by('-id')
    for item in previous.iterator():
        turn = {'run_id': item.pk, 'prompt': item.prompt, 'answer': item.result.get('answer', ''),
                'as_of': item.as_of.isoformat(), 'draft_evidence_id': item.result.get('draft_evidence_id'),
                'evidence': [{'evidence_id': value['evidence_id'], 'tool': value['tool']} for value in item.evidence]}
        size += len(json.dumps(turn))
        if size > settings.RESEARCH_CONTEXT_CHARACTERS:
            break
        history.append(turn)
    keys = ('instrument_ids', 'timeframe', 'strategy_id', 'backtest_ids', 'watchlist_id', 'watchlist_name')
    context = {key: run.request[key] for key in keys if key in run.request}
    instruments = run.request.get('instruments', [])
    # Metadata is a preview, not a universe cap. analyze_market pages the entire
    # accepted ID list, and earlier draft artifacts are retrieved only if needed.
    context.update(instruments=instruments[:25], instrument_count=len(instruments))
    if run.request.get('draft_context'):
        context['draft_context'] = {key: run.request['draft_context'][key] for key in ('run_id', 'evidence_id')}
    context.update(has_strategy_snapshot=bool(run.request.get('strategy_snapshot')),
        backtests=[{'id': item['id'], 'name': item['name']} for item in run.request.get('backtests', [])],
        recorded_evidence=[compact_evidence(item) for item in run.evidence],
        earlier_turns_available=previous.count() > len(history))
    return {'prompt': run.prompt,
            'run_token': signing.dumps({'run_id': run.pk, 'user_id': run.user_id}, salt='research-run'),
            'as_of': run.as_of.isoformat(),
            'deadline': run.started_at.timestamp() + settings.RESEARCH_TIMEOUT_SECONDS,
            'tools': tool_definitions(run), 'context': context, 'history': list(reversed(history))}
