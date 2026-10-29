"""Pure matching shared by historical, Paper and Terminal simulation."""
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from collections import deque
import heapq

from common.enums import OrderStatus, OrderType, Side

from .types import ACTIVE_STATUSES, Fill, Order, Tick, ZERO


def match_order(order: Order, tick: Tick) -> Fill | None:
    """Use an eligible observation; preserve stop-limit activation independently of fills."""
    if order.status not in (OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL):
        return None
    if tick.event_time < order.eligible_at or not order.remaining:
        return None
    if tick.generation == order.generation and tick.sequence <= order.sequence:
        return None
    price = Decimal(str(tick.price))
    buy = order.side == Side.BUY
    if order.order_type in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT) and order.activated_at is None:
        if not (price >= order.trigger if buy else price <= order.trigger):
            return None
        order.activated_at = tick.event_time
    if order.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
        if not (price <= order.price if buy else price >= order.price):
            return None
    adjustment = price * order.slippage_pct / 100
    price = price + adjustment if buy else price - adjustment
    # Adverse rounding respects the contract tick; limit orders never exceed their limit.
    rounding = ROUND_CEILING if buy else ROUND_FLOOR
    price = (price / order.contract.tick_size).to_integral_value(rounding=rounding) * order.contract.tick_size
    if order.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
        price = min(price, order.price) if buy else max(price, order.price)
    if price <= ZERO:
        return None
    return Fill(order.identity, order.remaining, price, tick.event_time, Decimal(str(tick.price)))


class OrderBook:
    """Index one symbol's working orders; untouched limits cost no per-order work."""
    def __init__(self):
        self.orders, self.revisions = {}, {}
        self.heaps = {name: [] for name in ('buy_limit', 'sell_limit', 'buy_stop', 'sell_stop')}
        self.market, self.waiting = deque(), []
        self.revision, self.clock = 0, 0.0
        self.observation, self.deferred = None, []

    def remove(self, identity: str) -> None:
        self.orders.pop(identity, None)
        self.revisions.pop(identity, None)

    def put(self, order: Order) -> None:
        self.remove(order.identity)
        if order.status not in ACTIVE_STATUSES:
            return
        self.revision += 1
        self.orders[order.identity], self.revisions[order.identity] = order, self.revision
        self._index(order.identity)
        if sum(map(len, self.heaps.values())) + len(self.market) + len(self.waiting) > max(1024, len(self.orders) * 3):
            self.heaps = {key: [] for key in self.heaps}
            self.market.clear()
            self.waiting.clear()
            for identity in self.orders:
                self._index(identity)

    def _index(self, identity: str) -> None:
        order, revision = self.orders[identity], self.revisions[identity]
        if order.eligible_at.timestamp() > self.clock:
            heapq.heappush(self.waiting, (order.eligible_at.timestamp(), revision, identity))
            return
        stop = order.order_type in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT) and order.activated_at is None
        if order.order_type == OrderType.MARKET or order.order_type == OrderType.STOP_MARKET and not stop:
            self.market.append((revision, identity))
            return
        buy = order.side == Side.BUY
        threshold = order.trigger if stop else order.price
        name = ('buy_' if buy else 'sell_') + ('stop' if stop else 'limit')
        heapq.heappush(self.heaps[name], (threshold if buy == stop else -threshold, revision, identity))

    def match(self, tick: Tick, *, limit: int = 128) -> tuple[list[Fill], list[Order], bool]:
        stamp = tick.generation, tick.sequence
        if stamp != self.observation:
            self.observation = stamp
            for revision, identity in self.deferred:
                if self.revisions.get(identity) == revision:
                    self._index(identity)
            self.deferred.clear()
        self.clock = tick.event_time.timestamp()
        work, candidates, fills, activated = 0, [], [], []
        while self.waiting and self.waiting[0][0] <= self.clock and work < limit:
            _, revision, identity = heapq.heappop(self.waiting)
            work += 1
            if self.revisions.get(identity) == revision:
                self._index(identity)
        while self.market and work < limit:
            candidates.append(self.market.popleft())
            work += 1
        price = Decimal(str(tick.price))
        for name, threshold in (('buy_stop', price), ('sell_stop', -price), ('buy_limit', -price), ('sell_limit', price)):
            heap = self.heaps[name]
            while heap and heap[0][0] <= threshold and work < limit:
                _, revision, identity = heapq.heappop(heap)
                candidates.append((revision, identity))
                work += 1
        for revision, identity in candidates:
            if self.revisions.get(identity) != revision:
                continue
            order = self.orders[identity]
            before = order.activated_at
            fill = match_order(order, tick)
            if order.activated_at != before:
                activated.append(order)
            if fill is not None:
                fills.append(fill)
                self.remove(identity)
            elif tick.generation == order.generation and tick.sequence <= order.sequence:
                self.deferred.append((revision, identity))
            else:
                self._index(identity)
        more = bool(self.market or self.waiting and self.waiting[0][0] <= self.clock) or any(
            self.heaps[name] and self.heaps[name][0][0] <= threshold for name, threshold in
            (('buy_stop', price), ('sell_stop', -price), ('buy_limit', -price), ('sell_limit', price)))
        return fills, activated, more
