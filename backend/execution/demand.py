"""Cold demand adapter: translate deployments and exposure into data requirements.

The data service receives symbol/depth facts, without interpreting strategy rules
or knowing order/session models. No tick worker calls this database adapter.
"""
import logging

from django.conf import settings

from common.enums import ExecutionScope, ExecutionSessionStatus, OrderStatus, TerminalOrderStatus

from .compiler import strategy_requirements

logger = logging.getLogger(__name__)
_versions = {}


def market_requirements():
    from instruments.models import Instrument
    from instruments.services import InstrumentResolver
    from live_trading.models import TradingSession, LivePosition, LiveOrder
    from paper_trading.models import PaperTradingSession, PaperPosition, PaperOrder
    from strategies.models import StrategyVersion
    from trading.models import Order, Position
    from marketdata.calendar import MarketSessionCalendar

    exposure = set()
    for model in (Position, PaperPosition, LivePosition):
        exposure.update(model.objects.exclude(quantity=0).values_list('instrument_id', flat=True))
    exposure.update(Order.objects.filter(status=TerminalOrderStatus.OPEN).values_list('instrument_id', flat=True))
    for model in (PaperOrder, LiveOrder):
        exposure.update(model.objects.exclude(status__in=(OrderStatus.FILLED, OrderStatus.CANCELLED,
            OrderStatus.REJECTED, OrderStatus.EXPIRED)).values_list('instrument_id', flat=True))
    versions = set()
    for scope, model in ((ExecutionScope.PAPER, PaperTradingSession), (ExecutionScope.LIVE, TradingSession)):
        if scope in settings.EXECUTION_ENABLED_SCOPES:
            versions.update(model.objects.exclude(status=ExecutionSessionStatus.STOPPED).values_list(
                'allocation__deployed_version_id', flat=True))
    versions.discard(None)
    for identity in _versions.keys() - versions:
        del _versions[identity]
    for version in StrategyVersion.objects.filter(pk__in=versions - _versions.keys()).only('pk', 'config_snapshot'):
        config = version.config_snapshot
        try:
            ids = {InstrumentResolver.resolve(watch, config['entry_order_config']['entry_side'],
                config['position_sizing_rule'])[0] for watch in config['watchlist_instruments']}
            _versions[version.pk] = ids, config
        except (ValueError, KeyError, TypeError):
            # Existing exposure below still receives ticks if a saved version
            # cannot be prepared. Other deployments keep their subscriptions.
            logger.exception('Invalid market requirements for strategy version=%s', version.pk)
    history = {}
    for version_id, (ids, _) in _versions.items():
        for identity in ids:
            history.setdefault(identity, []).append(version_id)
    requirements, protected, calendars, depths = {}, set(), {}, {}
    for instrument in Instrument.objects.filter(pk__in=exposure | history.keys()).only('pk', 'sym_ticker', 'exchange', 'segment'):
        required = requirements.setdefault(instrument.sym_ticker, {})
        if instrument.pk in exposure:
            protected.add(instrument.sym_ticker)
        market = instrument.exchange, instrument.segment
        for version_id in history.get(instrument.pk, ()):
            if market not in calendars:
                calendars[market] = MarketSessionCalendar.for_instrument(instrument)
            key = version_id, market
            if key not in depths:
                try:
                    depths[key] = strategy_requirements(_versions[version_id][1], calendars[market])[2]
                except (ValueError, KeyError, TypeError):
                    logger.exception('Invalid history requirements for strategy version=%s', version_id)
                    depths[key] = {}
            for source, depth in depths[key].items():
                required[source] = max(required.get(source, 0), depth)
    return requirements, protected
