"""Historical clock adapter for the same evaluator, matcher and account ledger.

OHLC candles do not contain a real tick path. This adapter explicitly assumes
open -> adverse extreme -> favourable extreme -> close for the strategy side.
The two extreme timestamps are synthetic. Orders fill on a later observation;
a decision using a completed candle can therefore only fill in the next bar.
Persist this policy in every report instead of presenting it as tick replay.
"""
from collections import Counter
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from heapq import merge
from uuid import NAMESPACE_URL, uuid5

from common.enums import ExecutionMode, ExecutionSessionStatus, OrderIntent, Side
from instruments.services import InstrumentResolver

from .compiler import FeatureGraph, compile_strategy
from .engine import EvaluationUnit
from .ledger import ACTIVE_STATUSES, accept_intent, acknowledge, apply_fill, cancel_order, position_view
from .matching import match_order, OrderBook
from .preparation import PreparedMarket
from .types import Account, ClosedTrade, Intent, Tick, ZERO

OHLC_POLICY = ('OHLC approximation: open, adverse extreme, favourable extreme, close; '
    'extreme times are synthetic, orders fill on the next observation, completed-candle '
    'signals fill no earlier than the next bar. This is not historical tick replay.')


class Replay:
    def __init__(self, *, identity: int, version: int, config: dict, markets: list[PreparedMarket],
                 start: datetime, end: datetime, capital: Decimal, profile: dict, slippage: Decimal):
        self.identity, self.start, self.end = identity, start, end
        self.account = Account((ExecutionMode.BACKTEST, identity), capital,
            versions={identity: version}, statuses={identity: ExecutionSessionStatus.RUNNING},
            profiles={identity: profile}, slippage={identity: slippage})
        self.units, self.graphs, self.markets = {}, {}, {}
        self.books = {}
        watches = {item['instrument_id']: item for item in config['watchlist_instruments']}
        for market in markets:
            instrument = market.contract.instrument_id
            key = ExecutionMode.BACKTEST, identity, instrument
            from copy import deepcopy
            local = deepcopy(config)
            _, side, sizing = InstrumentResolver.resolve(watches[instrument], config['entry_order_config']['entry_side'], config['position_sizing_rule'])
            local['entry_order_config']['entry_side'] = side
            program = compile_strategy(local, version, calendar=market.calendar)
            self.units[instrument] = EvaluationUnit(key, self.account.key, program)
            graph = FeatureGraph(market.calendar, capacity=max(program.counts.values()) + 8)
            graph.register(program)
            self.graphs[instrument], self.markets[instrument] = graph, market
            self.account.sizing[key] = sizing
            self.books[instrument] = OrderBook()
        self.trades: list[ClosedTrade] = []
        self.equity: list[tuple[datetime, Decimal]] = []
        self.last: dict[int, Tick] = {}
        self.diagnostics = Counter()
        self.sequence = 0

    def _events(self, market: PreparedMarket):
        """Merge already ordered streams; memory does not grow with all replay events."""
        instrument = market.contract.instrument_id
        program = self.units[instrument].program
        def completed(timeframe, bars):
            for bar in bars:
                yield bar.closed_at, 0, instrument, timeframe, bar
        def observations():
            long = program.entry_side == Side.BUY
            for bar in market.candles[program.base_timeframe]:
                if bar.opened_at < self.start or bar.closed_at > self.end:
                    continue
                span = bar.closed_at - bar.opened_at
                prices = (bar.open, bar.low if long else bar.high, bar.high if long else bar.low, bar.close)
                for index, price in enumerate(prices):
                    # Close precedes the next open at the same clock instant.
                    phase = 1 if index == 3 else 2
                    yield bar.opened_at + span * (index / 3), phase, instrument, '', (price, index == 3)
        return merge(*(completed(tf, bars) for tf, bars in market.candles.items()), observations(),
                     key=lambda item: item[:4])

    def _commit(self, transition) -> None:
        acknowledge(self.account, transition.revision)
        if transition.trade is not None:
            self.trades.append(transition.trade)
        unit = self.units[transition.order.unit[2]]
        unit.update_position(position_view(self.account, unit.key))
        self.books[unit.key[2]].put(self.account.orders[transition.order.identity])

    def _observe(self, instrument: int, at: datetime, price: float) -> None:
        self.sequence += 1
        market, unit = self.markets[instrument], self.units[instrument]
        tick = Tick(market.contract.symbol, self.sequence, at, at.timestamp(), price)
        self.last[instrument] = tick
        fills, _, more = self.books[instrument].match(tick)
        while more:
            batch, _, more = self.books[instrument].match(tick)
            fills.extend(batch)
        for fill in fills:
            order = self.account.orders[fill.order_id]
            # An overnight gap cannot turn yesterday's admitted entry into an
            # entry outside today's configured trading window.
            if order.intent == OrderIntent.ENTRY and not unit.program.allows_entry(at):
                self._commit(cancel_order(self.account, order.identity, reason='Entry window closed.'))
                continue
            self._commit(apply_fill(self.account, fill))
            self.diagnostics['fills'] += 1
        position = self.account.positions.get(unit.key)
        if position is not None:
            pnl = market.contract.value(Decimal(str(price)) - position.average, position.quantity)
            position.mae, position.mfe = max(position.mae, -pnl), max(position.mfe, pnl)
        intent = unit.evaluate(self.graphs[instrument], tick)
        if intent is not None:
            try:
                self._commit(accept_intent(self.account, intent, market.contract))
                self.diagnostics['accepted_intents'] += 1
            except ValueError:
                unit.update_position(position_view(self.account, unit.key))
                self.diagnostics['rejected_intents'] += 1

    def run(self):
        """Yield progress boundaries; callers perform cancellation/report I/O outside the kernel."""
        events = merge(*(self._events(market) for market in self.markets.values()), key=lambda item: item[:4])
        last_time = None
        for at, phase, instrument, timeframe, payload in events:
            if at > self.end:
                break
            if phase == 0:
                self.graphs[instrument].append(timeframe, payload)
                continue
            if at < self.start:
                continue
            if last_time is not None and at != last_time:
                yield last_time
            last_time = at
            price, closed = payload
            self._observe(instrument, at, price)
            if closed:
                value = self.account.balance + sum((position.contract.value(
                    Decimal(str(self.last[key[2]].price)) - position.average, position.quantity)
                    for key, position in self.account.positions.items()), ZERO)
                if self.equity and self.equity[-1][0] == at:
                    self.equity[-1] = at, value
                else:
                    self.equity.append((at, value))
        self.finish()
        if last_time is not None:
            yield last_time

    def finish(self) -> None:
        """Cancel unfilled orders, then explicitly mark residual positions closed at the last bar."""
        for order in tuple(self.account.working.values()):
            if order.status in ACTIVE_STATUSES:
                self._commit(cancel_order(self.account, order.identity, reason='End of historical data.'))
                self.diagnostics['unfilled_orders_at_end'] += 1
        for key, position in tuple(self.account.positions.items()):
            tick, unit = self.last[key[2]], self.units[key[2]]
            identity = str(uuid5(NAMESPACE_URL, f'quantnest:backtest:{self.identity}:{key[2]}:final'))
            intent = Intent(identity, self.account.key, key, unit.program.version, position.revision,
                tick.sequence, tick.event_time, Side.SELL if position.quantity > 0 else Side.BUY,
                'END_OF_BACKTEST', Decimal(str(tick.price)), intent=OrderIntent.EXIT)
            self._commit(accept_intent(self.account, intent, position.contract))
            fill = match_order(self.account.orders[identity], replace(tick, sequence=tick.sequence + 1))
            self._commit(apply_fill(self.account, fill))
        if self.equity:
            self.equity[-1] = self.equity[-1][0], self.account.balance
