"""Read-only AI capabilities: market analysis, saved reports, metadata and draft validation.

Handlers return evidence. They never perform persistent user actions; actions.py
owns changes after explicit confirmation. tool_registry.py owns dispatch/accounting.
"""

from backtesting.models import BacktestRun
from backtesting.services import backtest_configuration
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.forms.models import model_to_dict
from rest_framework.exceptions import ValidationError

from .evaluation import market_rows
from .models import ResearchRun
from .validation import (
    json_data,
    validate_draft,
)

# Builder metadata is loaded only when needed.


def handle_get_rule_schema(run, arguments):
    from common.enums import OperandType
    from strategies.specification import studio_specification, choice_metadata

    operands = arguments.get("operand_types", [])
    if (
        set(arguments) - {"operand_types"}
        or not isinstance(operands, list)
        or any(value not in OperandType.values for value in operands)
    ):
        raise ValidationError("Choose supported operand types.")
    specification = studio_specification(operand_types=operands)
    data = {'StrategyStudio': specification, **choice_metadata(specification)}
    return {"data": data}


# Completed-candle market research.


def handle_market(run, arguments):
    from .resources import market_instruments
    from .evaluation import analysis_configuration
    from copy import copy
    from django.utils.dateparse import parse_datetime
    ids = market_instruments(run, arguments)
    page, size = arguments.get('page', 1), arguments.get('page_size', 25)
    start = (page - 1) * size
    observation = copy(run)
    if arguments.get('as_of'):
        from django.utils import timezone
        observed_at = parse_datetime(arguments['as_of'])
        if observed_at is None or timezone.is_naive(observed_at) or observed_at > run.as_of:
            raise ValidationError('Use a timezone-aware observation time no later than this request.')
        observation.as_of = observed_at
    config = analysis_configuration(arguments, run.request.get('timeframe', '1D'))
    data = market_rows(observation, config, comparison=arguments.get('mode', 'analyze') != 'screen',
        instrument_ids=ids[start:start + size], charts=True)
    data.update(page=page, universe_count=len(ids),
                next_page=page + 1 if start + size < len(ids) else None)
    return {'data': data}


# Saved strategy, backtest and execution reviews.


def handle_get_strategy_snapshot(run, arguments):
    from django.shortcuts import get_object_or_404
    from strategies.models import Strategy
    from strategies.services import StrategySnapshotService
    identity = arguments.get('strategy_id', run.request.get('strategy_id'))
    if not identity:
        raise ValidationError('Find a strategy or attach one to read its definition.')
    strategy = get_object_or_404(Strategy, pk=identity, user_id=run.user_id)
    if arguments.get('version_number'):
        version = get_object_or_404(strategy.versions, version_number=arguments['version_number'])
        data = version.config_snapshot
    elif identity == run.request.get('strategy_id') and run.request.get('strategy_snapshot'):
        data = run.request['strategy_snapshot']
    else:
        data = StrategySnapshotService._serialize_strategy(strategy)
    return {'data': data}


def get_backtest_report(run, backtest_id):
    backtest = (
        BacktestRun.objects.select_related("metrics")
        .filter(pk=backtest_id, user_id=run.user_id)
        .first()
    )
    if not backtest:
        raise ValidationError('Choose one of your own backtests.')
    if backtest.status != 'COMPLETED' or not hasattr(backtest, 'metrics'):
        return {'backtest_id': backtest.pk, 'name': backtest.name, 'status': backtest.status,
                'message': 'Performance metrics are available only after successful completion.'}
    trades = backtest.trades.all()
    totals = trades.aggregate(trades=Count("id"), net_pnl=Sum("net_pnl"), gross_pnl=Sum("gross_pnl"))
    totals = {key: value if value is not None else 0 for key, value in totals.items()}
    monthly = list(
        trades.annotate(month=TruncMonth("exit_time"))
        .values("month")
        .annotate(trades=Count("id"), net_pnl=Sum("net_pnl"))
        .order_by("month")
    )
    instruments = list(
        trades.values("instrument__symbol")
        .annotate(trades=Count("id"), net_pnl=Sum("net_pnl"))
        .order_by("instrument__symbol")
    )
    exits = list(
        trades.values("exit_reason").annotate(trades=Count("id"), net_pnl=Sum("net_pnl")).order_by("exit_reason")
    )
    trade_fields = ("id", "instrument__symbol", "net_pnl", "entry_time", "exit_time", "exit_reason")
    winners = trades.filter(net_pnl__gt=0).order_by("-net_pnl").values(*trade_fields)[:10]
    losers = trades.filter(net_pnl__lt=0).order_by("net_pnl").values(*trade_fields)[:10]
    return json_data(
        {
            "backtest_id": backtest.pk,
            "name": backtest.name,
            "start_date": backtest.start_date,
            "end_date": backtest.end_date,
            "initial_capital": backtest.initial_capital,
            "slippage_pct": backtest.slippage_pct,
            "include_charges": backtest.include_charges,
            "charge_profile_id": backtest.charge_profile_id,
            "snapshot": backtest_configuration(backtest),
            "metrics": model_to_dict(backtest.metrics, exclude=["id", "run"]),
            "data_quality": {key: value for key, value in backtest.data_quality.items() if key != 'accepted_workload'},
            "totals": totals,
            "diagnostics": backtest.diagnostics or None,
            "monthly": monthly,
            "instruments": instruments,
            "exit_reasons": exits,
            "largest_winners": list(winners),
            "largest_losers": list(losers),
            "assumptions": [
                "Candle replay uses simulated observations; fills follow the saved execution configuration.",
                "Historical results do not establish out-of-sample performance.",
            ],
        }
    )


def handle_get_backtest_reports(run, arguments):
    ids = arguments.get('backtest_ids', run.request.get('backtest_ids', []))
    if not ids:
        raise ValidationError('Find owned backtests or attach them to review results.')
    page, size = arguments.get('page', 1), arguments.get('page_size', 25)
    start = (page - 1) * size
    reports = [get_backtest_report(run, value) for value in ids[start:start + size]]
    completed = [item for item in reports if 'snapshot' in item]
    keys = ('start_date', 'end_date', 'initial_capital', 'slippage_pct', 'include_charges', 'charge_profile_id', 'snapshot')
    differences = [key for key in keys if any(item[key] != completed[0][key] for item in completed[1:])] if completed else []
    return {'data': {'reports': reports, 'differences': differences, 'page': page,
                     'next_page': page + 1 if start + size < len(ids) else None}}


def handle_get_execution_review(run, arguments):
    if arguments.get('review'):
        from analytics.services import execution_review_context
        _, data = execution_review_context(run.user, arguments['review'])
    else:
        data = run.request.get('execution_evidence')
    if not data:
        raise ValidationError('Specify execution filters or attach a journal/report context.')
    return {'data': data, 'source_as_of': data['as_of']}


def handle_get_conversation_evidence(run, arguments):
    from django.db.models import Q
    previous = ResearchRun.objects.filter(user_id=run.user_id, session_id=run.session_id,
                                          status='COMPLETED', pk__lt=run.pk)
    if arguments.get('run_id') or arguments.get('evidence_id'):
        if not arguments.get('run_id') or not arguments.get('evidence_id'):
            raise ValidationError('Provide both run_id and evidence_id for an artifact.')
        record = previous.filter(pk=arguments['run_id']).first()
        if record is None:
            raise ValidationError('This earlier turn does not belong to the current conversation.')
        item = next((value for value in record.evidence if value['evidence_id'] == arguments['evidence_id']), None)
        if item is None:
            raise ValidationError('Evidence was not recorded for this turn.')
        from .evidence import hydrate_evidence
        item = hydrate_evidence(item)
        return {**item, 'reused': True, 'source_run_id': item.get('source_run_id', record.pk),
                'source_as_of': item.get('source_as_of', record.as_of.isoformat())}
    query = arguments.get('query', '').strip()
    if query:
        previous = previous.filter(Q(prompt__icontains=query) | Q(result__answer__icontains=query))
    page = arguments.get('page', 1)
    records = list(previous.order_by('-pk')[(page - 1) * 10:page * 10 + 1])
    return {'data': {'turns': [{'run_id': value.pk, 'prompt': value.prompt,
              'answer': value.result.get('answer', ''), 'as_of': value.as_of,
              'evidence': [{'evidence_id': item['evidence_id'], 'tool': item['tool']} for item in value.evidence]}
              for value in records[:10]], 'next_page': page + 1 if len(records) > 10 else None}}


def handle_validate_strategy_draft(run, arguments):
    return {'data': {'valid': True, 'draft': validate_draft(arguments['draft'])}}


def handle_research_web(run, arguments):
    import httpx
    from django.conf import settings
    from django.utils import timezone
    try:
        response = httpx.post(f'{settings.RESEARCH_SERVICE_URL.rstrip("/")}/web-research',
            json=arguments, headers={'X-Research-Service-Token': settings.RESEARCH_SERVICE_TOKEN},
            timeout=httpx.Timeout(min(settings.RESEARCH_TIMEOUT_SECONDS, 120), connect=10))
        if response.is_error:
            detail = response.json().get('detail')
            message = detail if isinstance(detail, str) else 'Web retrieval could not start. Use valid public HTTP/HTTPS URLs and check provider availability.'
            return {'data': {'summary': message,
                             'sources': [], 'grounded': False, 'available': False},
                    'provider_usage': {'requests': 1, 'total_tokens': 0, 'complete': False},
                    'source_as_of': timezone.now().isoformat()}
        result = response.json()
    except httpx.RequestError:
        return {'data': {'summary': 'The web research provider could not be reached. Continue with available evidence.',
                         'sources': [], 'grounded': False, 'available': False},
                'provider_usage': {'requests': 1, 'total_tokens': 0, 'complete': False},
                'source_as_of': timezone.now().isoformat()}
    return {'data': result['data'], 'provider_usage': result['usage'], 'source_as_of': timezone.now().isoformat()}
