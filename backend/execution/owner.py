"""Single writer of one account's financial state, independent of rule workers."""
from dataclasses import replace
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from common.enums import ExecutionMode, OrderIntent, OrderStatus, Side
from execution.order_reports import OrderState, observe_order

from .ledger import (ACTIVE_STATUSES, accept_intent, apply_fill, cancel_order, hold_until_commit,
    order_transition, position_view, reject_order)
from .matching import OrderBook
from .types import Account, Contract, Fill, Intent, Order, Tick, Transition, ZERO


class AccountOwner:
    def __init__(self, account: Account):
        self.account = account
        self.books: dict[str, OrderBook] = {}
        self.exit_rejections = {}
        self.programs, self.calendars, self.contracts = {}, {}, {}
        for order in account.working.values():
            self.index(order)

    def index(self, order: Order) -> None:
        self.account.index_order(order)
        if not self.account.live:
            self.books.setdefault(order.contract.symbol, OrderBook()).put(order)

    def accept(self, intent: Intent, contract: Contract) -> Transition:
        calendar = self.calendars[contract.symbol]
        intent = replace(intent, at=intent.at.astimezone(calendar.zone))
        if not calendar.is_open(intent.at):
            raise ValueError('This exchange segment is closed.')
        program = self.programs.get(intent.unit)
        if intent.intent == OrderIntent.ENTRY and program is not None and not program.allows_entry(intent.at):
            raise ValueError('This strategy entry window is closed.')
        result = accept_intent(self.account, intent, contract)
        self.index(self.account.orders[intent.identity])
        return result

    def protective_exit(self, intent: Intent, contract: Contract) -> Transition | None:
        """A failed automatic close is an order rejection, not a worker crash.

        Rejections belong to the position revision, so an expired contract or
        oversized position produces one visible rejection rather than one per tick.
        """
        stamp = intent.position_revision, intent.version, intent.reason
        if self.exit_rejections.get(intent.unit) == stamp:
            return None
        try:
            return self.accept(intent, contract)
        except ValueError as exc:
            self.exit_rejections[intent.unit] = stamp
            order = Order(intent.identity, intent.unit, contract, intent.side,
                abs(self.account.positions[intent.unit].quantity), intent.at, intent.reason,
                intent=OrderIntent.EXIT, reduce_only=True, version=intent.version,
                manual=intent.manual, status=OrderStatus.REJECTED, error=str(exc),
                reference_price=intent.reference_price)
            self.account.orders[order.identity] = order
            return order_transition(self.account, order)

    def observe(self, tick: Tick) -> tuple[list[Transition], bool]:
        """Matching consumes observed ticks; broker accounts consume reports instead."""
        results = []
        for position in self.account.positions.values():
            if position.contract.symbol != tick.symbol:
                continue
            value = position.contract.value(Decimal(str(tick.price)) - position.average, position.quantity)
            position.mae, position.mfe = max(position.mae, -value), max(position.mfe, value)
            position.peak = (max(position.peak, tick.price) if position.quantity > 0
                             else min(position.peak or tick.price, tick.price))
        if not self.calendars[tick.symbol].is_open(tick.event_time):
            return results, False
        for key, position in tuple(self.account.positions.items()):
            if (position.contract.symbol != tick.symbol or not self.account.close_on_stop.get(key[1])
                    or position_view(self.account, key).pending):
                continue
            identity = str(uuid5(NAMESPACE_URL, f'quantnest:stop:{key}:{position.revision}:{tick.generation}:{tick.sequence}'))
            intent = Intent(identity, self.account.key, key, self.account.versions[key[1]], position.revision,
                tick.sequence, tick.event_time, Side.SELL if position.quantity > 0 else Side.BUY,
                'SESSION_STOP', Decimal(str(tick.price)), intent=OrderIntent.EXIT, generation=tick.generation)
            result = self.protective_exit(intent, position.contract)
            if result is not None:
                results.append(result)
        if self.account.live:
            return results, False
        # Terminal protection uses the same owner and simulator as manual orders.
        # A stop/target creates one full close; it cannot reverse a stale position.
        if self.account.key[0] == ExecutionMode.TERMINAL:
            for key, position in tuple(self.account.positions.items()):
                if position.contract.symbol != tick.symbol:
                    continue
                price, long = Decimal(str(tick.price)), position.quantity > 0
                stop = position.stop_loss is not None and (price <= position.stop_loss if long else price >= position.stop_loss)
                target = position.take_profit is not None and (price >= position.take_profit if long else price <= position.take_profit)
                if not (stop or target):
                    continue
                working = [order for order in self.account.working.values() if order.unit == key]
                if any(order.reason in ('STOP_LOSS', 'TARGET') and order.reduce_only for order in working):
                    continue
                # Protection replaces working manual orders before matching this
                # observation. A pending add or limit exit cannot block a stop.
                for order in working:
                    results.append(cancel_order(self.account, order.identity, reason='Position protection triggered.'))
                    self.index(order)
                identity = str(uuid5(NAMESPACE_URL, f'quantnest:protection:{key}:{position.revision}:{tick.generation}:{tick.sequence}'))
                intent = Intent(identity, self.account.key, key, 0, position.revision,
                    tick.sequence, tick.event_time, Side.SELL if long else Side.BUY,
                    'STOP_LOSS' if stop else 'TARGET', price, intent=OrderIntent.EXIT,
                    quantity=abs(position.quantity), manual=True, generation=tick.generation)
                result = self.protective_exit(intent, position.contract)
                if result is not None:
                    results.append(result)
        book = self.books.get(tick.symbol)
        if book is None:
            return results, False
        fills, activated, more = book.match(tick)
        filled_ids = {fill.order_id for fill in fills}
        results.extend(order_transition(self.account, order) for order in activated if order.identity not in filled_ids)
        for fill in fills:
            order = self.account.orders[fill.order_id]
            program = self.programs.get(order.unit)
            if order.intent == OrderIntent.ENTRY and program is not None and not program.allows_entry(tick.event_time):
                results.append(cancel_order(self.account, order.identity, reason='Entry window closed.'))
                continue
            try:
                order.contract.validate(fill.quantity, (), tick.event_time.astimezone(self.calendars[tick.symbol].zone))
                results.append(apply_fill(self.account, fill))
            except ValueError as exc:
                results.append(reject_order(self.account, order.identity, str(exc)))
            self.index(order)
        return results, more

    def broker_observation(self, identity: str, *, broker_id: str, status: str,
                           quantity: int, average: Decimal, at, error='', ordered_at=None,
                           exchange_order_id='', updated_at=None) -> Transition:
        """Normalize a cumulative report before applying its incremental fill once."""
        order = self.account.orders[identity]
        if broker_id and order.broker_id and order.broker_id != broker_id:
            raise ValueError('Broker identity differs from the owned order.')
        previous = OrderState(order.quantity, order.filled, order.filled_value, order.status)
        change = observe_order(previous, status=status, filled=quantity, average=average)
        if change.error:
            raise ValueError(change.error)
        # Validate/apply the fill before accepting report metadata. A rejected
        # observation must leave the owned order untouched for reconciliation.
        result = None
        if change.fill_quantity:
            result = apply_fill(self.account, Fill(identity, change.fill_quantity, change.fill_price, at))
        order.broker_id = broker_id or order.broker_id
        if ordered_at is not None:
            order.broker_ordered_at = ordered_at
        if updated_at is not None and (order.broker_updated_at is None or updated_at > order.broker_updated_at):
            order.broker_updated_at = updated_at
        order.exchange_order_id = exchange_order_id or order.exchange_order_id
        order.error = error
        order.status = change.state.status
        self.account.index_order(order)
        if order.status not in ACTIVE_STATUSES:
            released = order.reserved
            order.reserved = ZERO
        else:
            released = ZERO
        # The fill and terminal broker status are a single persisted revision.
        if result is not None:
            from copy import deepcopy
            hold_until_commit(self.account, result.revision, released)
            return replace(result, order=deepcopy(order))
        result = order_transition(self.account, order)
        hold_until_commit(self.account, result.revision, released)
        return result
