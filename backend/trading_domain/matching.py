"""Indexed simulated order matching: O(log n + eligible orders) per price event."""
import heapq
from collections import deque
from decimal import Decimal


class IndexedOrderBook:
    def __init__(self):
        self.orders = {}
        self.heaps = {name: [] for name in ("buy_limit", "sell_limit", "buy_stop", "sell_stop")}
        self.market = deque()
        self.revisions = {}
        self._revision = 0

    def remove(self, identity):
        self.orders.pop(identity, None)
        self.revisions.pop(identity, None)

    def upsert(self, order):
        identity = int(order["id"])
        self.remove(identity)
        if order["status"] != "OPEN":
            return
        self._revision += 1
        self.revisions[identity] = self._revision
        self.orders[identity] = dict(order)
        self._index(identity)
        # Bound lazy tombstones after frequent order modifications/cancellations.
        if sum(len(heap) for heap in self.heaps.values()) + len(self.market) > max(1024, len(self.orders) * 3):
            self.heaps = {name: [] for name in self.heaps}
            self.market.clear()
            for current in self.orders:
                self._index(current)

    def _index(self, identity):
        order = self.orders[identity]
        revision = self.revisions[identity]
        if order["order_type"] == "MARKET":
            self.market.append((identity, revision))
            return
        buy = order["transaction_type"] == "BUY"
        stop = order["order_type"] in ("STOP", "STOP_LIMIT")
        price = Decimal(str(order["trigger_price"] if stop else order["price"]))
        name = ("buy_" if buy else "sell_") + ("stop" if stop else "limit")
        priority = price if buy == stop else -price
        heapq.heappush(self.heaps[name], (priority, revision, identity))

    def has_matches(self, price):
        price = Decimal(str(price))
        return bool(self.market) or any(self.heaps[name] and self.heaps[name][0][0] <= threshold
            for name, threshold in (("buy_stop", price), ("sell_stop", -price), ("buy_limit", -price), ("sell_limit", price)))

    def match(self, price, limit=256):
        price = Decimal(str(price))
        fills, activated = [], []
        work = 0
        while self.market and work < limit:
            work += 1
            identity, revision = self.market.popleft()
            if identity in self.orders and revision == self.revisions[identity]:
                fills.append(identity)
                self.remove(identity)
        for name, threshold in (("buy_stop", price), ("sell_stop", -price),
                                ("buy_limit", -price), ("sell_limit", price)):
            heap = self.heaps[name]
            while heap and heap[0][0] <= threshold and work < limit:
                work += 1
                _, revision, identity = heapq.heappop(heap)
                order = self.orders.get(identity)
                if order is None or revision != self.revisions[identity]:
                    continue
                if name.endswith("stop") and order["order_type"] == "STOP_LIMIT":
                    activated.append(identity)
                    order["order_type"] = "LIMIT"
                    order["trigger_price"] = None
                    self._index(identity)
                else:
                    fills.append(identity)
                    self.remove(identity)
        return fills, activated
