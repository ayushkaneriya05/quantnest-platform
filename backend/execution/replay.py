"""Historical clock adapter for the same evaluator, matcher and account ledger.

OHLC candles do not contain a real tick path. This adapter explicitly assumes
open -> adverse extreme -> favourable extreme -> close for the strategy side.
The two extreme timestamps are synthetic. Market orders execute at the traded
quote available when the signal fires, with configured slippage/tick rounding.
The replay never waits for another OHLC landmark to price a generated order.
"""
from collections import Counter
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from heapq import merge
from itertools import groupby
from uuid import NAMESPACE_URL, uuid5

from common.enums import ExecutionMode, ExecutionSessionStatus, OrderIntent, OrderType, Side
from instruments.services import InstrumentResolver

from .compiler import FeatureGraph, compile_strategy
from .engine import EvaluationUnit
from .ledger import accept_intent, acknowledge, apply_fill, position_view, reject_order
from .matching import match_order
from .preparation import PreparedMarket
from .types import Account, ClosedTrade, Contract, Intent, Tick, ZERO, route_key

class Replay:
    def __init__(self, *, identity: int, version: int, config: dict, markets: list[PreparedMarket],
                 start: datetime, end: datetime, capital: Decimal, profile: dict, slippage: Decimal,
                 selections=None):
        self.identity, self.start, self.end = identity, start, end
        self.account = Account((ExecutionMode.BACKTEST, identity), capital,
            versions={identity: version}, statuses={identity: ExecutionSessionStatus.RUNNING},
            profiles={identity: profile}, slippage={identity: slippage})
        self.units, self.graphs = {}, {}
        self.markets = {market.instrument_id: market for market in markets}
        self.bindings, self.listeners = {}, {}
        self.selection_days = {}
        self.base_timeframe = config['time_rule']['candle_timeframe']
        self.entry_side = config['entry_order_config']['entry_side']
        for watch in config['watchlist_instruments']:
            instrument = watch['instrument_id']
            sizing = InstrumentResolver.sizing_for(watch, config['position_sizing_rule'])
            binding = InstrumentResolver.input_bindings(watch)
            selection, candidates = None, {}
            if 'contract_selection' in watch:
                selection, candidates = (selections or {}).get((watch['route_id'], watch['leg_id']), (None, {}))
                if selection is None or not candidates:
                    raise ValueError('Automatic replay requires its reviewed historical contract catalog.')
                instrument = next(iter(candidates))
                binding['trade'] = instrument
            if any(source not in self.markets for source in binding.values()):
                raise ValueError('Historical replay needs both signal and traded-contract data.')
            if self.markets[instrument].contract is None:
                raise ValueError('The traded instrument needs qualified financial contract terms.')
            key = route_key(ExecutionMode.BACKTEST, identity, watch)
            program = compile_strategy(config, version, calendar=self.markets[instrument].calendar,
                signal_calendar=self.markets[binding['signal']].calendar)
            program = replace(program, binding=(binding['signal'], instrument), selection=selection, candidates=candidates)
            self.units[key] = EvaluationUnit(key, self.account.key, program)
            self.bindings[key] = binding
            sources = binding if selection is None else {'signal': binding['signal'], **{str(key): key for key in candidates}}
            for role, source in sources.items():
                if source not in self.markets or selection is not None and role != 'signal' and self.markets[source].contract is None:
                    raise ValueError('Every automatic candidate needs prepared history and contract terms.')
                self.listeners.setdefault(source, set()).add(key)
                projection = program if binding['signal'] == instrument else program.for_source('signal' if role == 'signal' else 'trade')
                capacity = max(projection.counts.values()) + 8
                graph = self.graphs.setdefault(source, FeatureGraph(self.markets[source].calendar, capacity=capacity))
                graph.capacity = max(graph.capacity, capacity)
                graph.register(projection)
            self.account.sizing[key] = sizing
        self.symbol_graphs = {self.markets[key].symbol: graph for key, graph in self.graphs.items()}
        self.trades: list[ClosedTrade] = []
        self.settlements = []
        self.equity: list[tuple[datetime, Decimal]] = []
        self.last: dict[int, Tick] = {}
        self.diagnostics = Counter()
        self.sequence = 0

    def _events(self, market: PreparedMarket):
        """Merge already ordered streams; memory does not grow with all replay events."""
        instrument = market.instrument_id
        def completed(timeframe, bars):
            for bar in bars:
                yield bar.closed_at, 0, instrument, timeframe, bar
        def observations():
            long = self.entry_side == Side.BUY
            for bar in market.candles[self.base_timeframe]:
                if bar.opened_at < self.start or bar.closed_at > self.end:
                    continue
                span = bar.closed_at - bar.opened_at
                prices = (bar.open, bar.low if long else bar.high, bar.high if long else bar.low, bar.close)
                for index, price in enumerate(prices):
                    # Close precedes the next open at the same clock instant.
                    phase = 1 if index == 3 else 2
                    yield bar.opened_at + span * (index / 3), phase, instrument, '', (price, index == 3)
        settlement_events = ((price.available_at, 3, instrument, '', price) for price in market.settlements)
        def expiration():
            if market.contract is not None and market.contract.expiry is not None:
                cutoff = market.calendar.session_close(market.contract.expiry)
                if self.start <= cutoff <= self.end:
                    yield cutoff, 4, instrument, '', None
        return merge(*(completed(tf, bars) for tf, bars in market.candles.items()), observations(), settlement_events, expiration(),
                     key=lambda item: (item[0].timestamp(), *item[1:4]))

    def _commit(self, transition) -> None:
        acknowledge(self.account, transition.revision)
        if transition.trade is not None:
            self.trades.append(transition.trade)
        unit = self.units[transition.order.unit]
        unit.update_position(position_view(self.account, unit.key))

    def _execute(self, intent: Intent, contract: Contract) -> bool:
        """Admit and fill once at the signal's traded quote, never a future price."""
        if intent.order_type != OrderType.MARKET:
            raise ValueError('Historical strategy execution requires a market order.')
        try:
            admitted = accept_intent(self.account, intent, contract)
        except ValueError:
            self.units[intent.unit].update_position(position_view(self.account, intent.unit))
            self.diagnostics['rejected_intents'] += 1
            return False
        self._commit(admitted)
        self.diagnostics['accepted_intents'] += 1
        # This is a local execution event at the same price/time. Its later
        # sequence satisfies the shared matcher without changing live matching
        # or manufacturing a new market observation for the rule evaluator.
        quote = Tick(contract.symbol, intent.sequence + 1, intent.at,
                     float(intent.reference_price), generation=intent.generation)
        fill = match_order(self.account.orders[intent.identity], quote)
        if fill is None:
            self._commit(reject_order(self.account, intent.identity,
                'The signal quote cannot produce a valid tick-rounded execution price.'))
            self.diagnostics['rejected_fills'] += 1
            return False
        position = self.account.positions.get(intent.unit)
        if position is not None:
            # Include the closing execution before apply_fill removes exposure.
            position.mark_excursion(fill.price)
        transition = apply_fill(self.account, fill)
        self._commit(transition)
        self.diagnostics['fills' if transition.fill is not None else 'rejected_fills'] += 1
        position = self.account.positions.get(intent.unit)
        if transition.fill is not None and position is not None:
            # An adverse entry adjustment is already an excursion at this quote.
            position.mark_excursion(intent.reference_price)
        return transition.fill is not None

    def _observe(self, instrument: int, at: datetime, price: float) -> None:
        self.sequence += 1
        market = self.markets[instrument]
        tick = Tick(market.symbol, self.sequence, at, price)
        self.last[instrument] = tick
        observed_price = Decimal(str(price))
        for position in self.account.positions.values():
            if position.contract.instrument_id == instrument:
                position.mark_excursion(observed_price)
        for target in sorted(self.listeners.get(instrument, ())):
            unit, binding = self.units[target], self.bindings[target]
            if unit.program.selection is not None:
                day = at.astimezone(unit.program.calendar.zone).date()
                if (instrument not in binding.values() and self.selection_days.get(target) == day):
                    # Preserve every candidate's quote for a later ATM change,
                    # but an unrelated premium tick cannot change selection.
                    # The first event of a new date still checks expiry rollover.
                    unit.route_quotes[tick.symbol] = tick
                    continue
                self.selection_days[target] = day
                intent = unit.evaluate_selected(self.symbol_graphs, tick, self.markets[binding['signal']].symbol)
                binding['trade'] = unit.program.binding[1]
            elif binding['signal'] == binding['trade']:
                intent = unit.evaluate(self.graphs[instrument], tick)
            else:
                role = next(role for role, source in binding.items() if source == instrument)
                intent = unit.evaluate_sources({role: self.graphs[source] for role, source in binding.items()}, tick, role)
            if intent is not None:
                self._execute(intent, self.markets[binding['trade']].contract)

    def _stage_quotes(self, observations: list[tuple]) -> None:
        """Publish one simultaneous price snapshot before evaluating any route.

        An underlying high and option high at the same replay phase are both
        available. Instrument ID ordering must not fill an option at the prior
        phase's low. No later clock or next-bar opening is exposed here.
        """
        for offset, (at, _, instrument, _, payload) in enumerate(observations, 1):
            tick = Tick(self.markets[instrument].symbol, self.sequence + offset, at, payload[0])
            self.last[instrument] = tick
            for key in self.listeners.get(instrument, ()):
                unit, binding = self.units[key], self.bindings[key]
                if unit.program.selection is not None:
                    unit.route_quotes[tick.symbol] = tick
                elif binding['signal'] != binding['trade']:
                    for role, source in binding.items():
                        if source == instrument:
                            unit.source_quotes[role] = tick

    def record_equity(self, at: datetime) -> None:
        value = self.account.balance + sum((position.unsettled_pnl(
            Decimal(str(self.last[position.contract.instrument_id].price))) for position in self.account.positions.values()), ZERO)
        if self.equity and self.equity[-1][0] == at:
            self.equity[-1] = at, value
        else:
            self.equity.append((at, value))

    def run(self):
        """Yield progress boundaries; callers perform cancellation/report I/O outside the kernel."""
        # Normalize comparison keys once per event. Repeated mixed-timezone
        # datetime comparisons inside a large merge otherwise dominate replay.
        events = merge(*(self._events(market) for market in self.markets.values()),
            key=lambda item: (item[0].timestamp(), *item[1:4]))
        last_time, equity_due = None, False
        for _, simultaneous in groupby(events, key=lambda item: (item[0].timestamp(), item[1])):
            batch = list(simultaneous)
            at, phase = batch[0][:2]
            if at > self.end:
                break
            if phase == 0:
                for _, _, instrument, timeframe, payload in batch:
                    self.graphs[instrument].append(timeframe, payload)
                continue
            if last_time is not None and at != last_time:
                # All simultaneous contract observations contribute to one
                # equity mark. Recalculating after every candidate close only
                # overwrote the same row and multiplied portfolio work.
                if equity_due:
                    self.record_equity(last_time)
                equity_due = False
                yield last_time
            last_time = at
            if phase == 3:
                from .settlements import apply_settlement
                for _, _, instrument, _, payload in batch:
                    for key, unit in self.units.items():
                        if self.bindings[key]['trade'] != instrument:
                            continue
                        position = self.account.positions.get(unit.key)
                        # Publication can occur after the next session starts. A
                        # new cycle did not own units at yesterday's cutoff.
                        if position is not None and position.opened_at <= payload.effective_at:
                            result = apply_settlement(self.account, unit.key, payload, now=at,
                                quantity=position.quantity, opened_at=position.opened_at)
                            if result is not None:
                                self.settlements.append(result)
                                acknowledge(self.account, self.account.revision)
                                if result.trade is not None:
                                    self.trades.append(result.trade)
                                unit.update_position(position_view(self.account, unit.key))
                equity_due = True
                continue
            if phase == 4:
                # Prefer a sourced final settlement; otherwise explicitly
                # simulate liquidation at the last observed contract price.
                from common.enums import SettlementKind
                for _, _, instrument, _, _ in batch:
                    official = any(row.kind == SettlementKind.FINAL for row in self.markets[instrument].settlements)
                    if not official:
                        for key, position in tuple(self.account.positions.items()):
                            if position.contract.instrument_id == instrument:
                                self._close_position(key, 'SIMULATED_EXPIRY_CLOSE', at=at)
                equity_due = True
                continue
            if at < self.start:
                continue
            self._stage_quotes(batch)
            for _, _, instrument, _, (price, closed) in batch:
                self._observe(instrument, at, price)
                if closed:
                    equity_due = True
        if equity_due:
            self.record_equity(last_time)
        self.finish()
        if last_time is not None:
            yield last_time

    def finish(self) -> None:
        """Explicitly close residual positions at the last observed contract quote."""
        for key in tuple(self.account.positions):
            self._close_position(key, 'END_OF_BACKTEST')
        if self.equity:
            self.equity[-1] = self.equity[-1][0], self.account.balance

    def _close_position(self, key, reason, *, at=None):
        """Declared simulation liquidation, using this owned contract's price."""
        position, unit = self.account.positions[key], self.units[key]
        tick = self.last[position.contract.instrument_id]
        if at is not None:
            tick = replace(tick, event_time=at)
        identity = str(uuid5(NAMESPACE_URL, f'quantnest:backtest:{self.identity}:{key}:{reason}:{tick.event_time}'))
        intent = Intent(identity, self.account.key, key, unit.program.version, position.revision,
            tick.sequence, tick.event_time, Side.SELL if position.quantity > 0 else Side.BUY,
            reason, Decimal(str(tick.price)), intent=OrderIntent.EXIT, binding=position.binding)
        if not self._execute(intent, position.contract):
            raise ValueError(f'Unable to close residual {position.contract.symbol} at its last quote.')
