"""Cold demand adapter: translate deployments and exposure into data requirements.

The data service receives symbol/depth facts, without interpreting strategy rules
or knowing order/session models. No tick worker calls this database adapter.
"""
import logging
import time
from decimal import Decimal

from django.conf import settings

from common.enums import ExecutionScope, ExecutionSessionStatus, OrderStatus, TerminalOrderStatus


logger = logging.getLogger(__name__)
_versions = {}
_retained = {}
_refresh_at = 0.0


def market_requirements():
    global _refresh_at
    from instruments.models import Instrument
    from live_trading.models import TradingSession, LivePosition, LiveOrder
    from paper_trading.models import PaperTradingSession, PaperPosition, PaperOrder
    from strategies.models import StrategyVersion
    from trading.models import Order, Position

    exposure = set(Position.objects.exclude(quantity=0).values_list('instrument_id', flat=True))
    owned = {}
    for scope, positions, orders, owner in ((ExecutionScope.PAPER, PaperPosition, PaperOrder, 'account_id'),
                                          (ExecutionScope.LIVE, LivePosition, LiveOrder, 'allocation_id')):
        rows = list(positions.objects.exclude(quantity=0).values_list(owner, 'route_id', 'leg_id', 'instrument_id'))
        rows.extend(orders.objects.exclude(status__in=(OrderStatus.FILLED, OrderStatus.CANCELLED,
            OrderStatus.REJECTED, OrderStatus.EXPIRED)).values_list(owner, 'route_id', 'leg_id', 'instrument_id'))
        for account, route, leg, instrument in rows:
            exposure.add(instrument)
            owned.setdefault((scope, account), {}).setdefault((route, leg), set()).add(instrument)
    exposure.update(Order.objects.filter(status=TerminalOrderStatus.OPEN).values_list('instrument_id', flat=True))
    versions, retained = set(), {}
    for scope, model, owner in ((ExecutionScope.PAPER, PaperTradingSession, 'account_id'),
                                (ExecutionScope.LIVE, TradingSession, 'allocation_id')):
        if scope in settings.EXECUTION_ENABLED_SCOPES:
            for account, requested, applied in model.objects.exclude(status=ExecutionSessionStatus.STOPPED).values_list(
                    owner, 'allocation__deployed_version_id', 'applied_version_id'):
                # Keep the committed version's signal data while a new version
                # is warming, awaiting admission, or rejected by the owner.
                versions.update((requested, applied))
                for version in (requested, applied):
                    for route, instruments in owned.get((scope, account), {}).items():
                        retained.setdefault(version, {}).setdefault(route, set()).update(instruments)
    versions.discard(None)
    for identity in _versions.keys() - versions:
        del _versions[identity]
        _retained.pop(identity, None)
    # A new fill or pending order changes which contract must remain available,
    # even when that contract has expired or disappeared from the current master.
    for identity in tuple(_versions):
        if _retained.get(identity) != retained.get(identity, {}):
            del _versions[identity]

    from .preparation import compile_markets
    if time.monotonic() >= _refresh_at:
        # Candidate catalogs are cold inputs, refreshed independently of ticks.
        for identity, compiled in tuple(_versions.items()):
            if any(program.selection is not None for program in compiled.programs.values()):
                del _versions[identity]
        _refresh_at = time.monotonic() + 60
    for version in StrategyVersion.objects.filter(pk__in=versions - _versions.keys()).only('pk', 'config_snapshot'):
        try:
            _versions[version.pk] = compile_markets(version.config_snapshot, version.pk,
                retained=retained.get(version.pk))
            _retained[version.pk] = retained.get(version.pk, {})
        except (ValueError, KeyError, TypeError):
            logger.exception('Invalid market requirements for strategy version=%s', version.pk)
    requirements, protected = {}, set()
    for instrument in Instrument.objects.filter(pk__in=exposure).only('sym_ticker'):
        requirements.setdefault(instrument.sym_ticker, {})
        protected.add(instrument.sym_ticker)
    from django.utils import timezone
    from marketdata.shared_memory import get_market_price
    observed, now = {}, timezone.now()

    def require(compiled, identity, projection):
        required = requirements.setdefault(compiled.instruments[identity].sym_ticker, {})
        for source, depth in projection.sources.items():
            required[source] = max(required.get(source, 0), depth)

    for version, compiled in _versions.items():
        # Keep every eligible symbol subscribed for in-memory selection. Only
        # current/nearby or owned contracts need historical feature preparation.
        for instrument in compiled.instruments.values():
            requirements.setdefault(instrument.sym_ticker, {})
        for identity, binding in compiled.bindings.items():
            program = compiled.programs[identity]
            signal = compiled.instruments[binding['signal']].sym_ticker
            protected.add(signal)
            require(compiled, binding['signal'], program.for_source('signal'))
            if program.selection is None:
                warm = {binding['trade']}
            else:
                warm = set(retained.get(version, {}).get(identity, ()))
                if signal not in observed:
                    observed[signal] = get_market_price(signal)
                spot = Decimal(str(observed[signal])) if observed[signal] is not None else Decimal('NaN')
                try:
                    warm.update(program.selection.warmup_candidates(spot, now.astimezone(program.calendar.zone).date()))
                except ValueError:
                    # No observed underlying/eligible strike: keep exposure
                    # prepared, never substitute a stored close or other strike.
                    pass
            for instrument in warm:
                protected.add(compiled.instruments[instrument].sym_ticker)
                require(compiled, instrument, program.for_source('trade'))
    return requirements, protected
