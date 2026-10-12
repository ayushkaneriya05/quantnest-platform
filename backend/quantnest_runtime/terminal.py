"""Partition-owned Terminal books. DB access occurs on commands and eligible fills."""
import json
import logging
import time

from django.conf import settings
from django.db import close_old_connections, transaction

from core.redis import runtime_redis
from quantnest_runtime.ownership import Lease, partition
from trading_domain.matching import IndexedOrderBook

logger = logging.getLogger(__name__)


def order_payload(order):
    return {"id": order.pk, "symbol": order.instrument.sym_ticker, "instrument_id": order.instrument_id,
            "order_type": order.order_type, "transaction_type": order.transaction_type,
            "quantity": order.quantity, "price": str(order.price) if order.price is not None else None,
            "trigger_price": str(order.trigger_price) if order.trigger_price is not None else None,
            "status": order.status}


def run_worker(index, stop):
    from marketdata.calendar import MarketSessionCalendar
    from marketdata.shared_memory import SharedMemoryManager
    from trading.models import Order
    from trading.services import TradingOrderService
    from decimal import Decimal
    from datetime import datetime, timezone, timedelta
    lease = Lease(f"terminal:{settings.EXECUTION_NODE_INDEX}:{index}")
    if not lease.acquire():
        raise RuntimeError("Terminal partition already owned")
    stream = "quantnest:terminal:commands"
    tail = runtime_redis().xrevrange(stream, count=1)
    cursor = tail[0][0] if tail else "0-0"
    books, markets, calendars, sequences, gaps = {}, {}, {}, {}, {}
    total = settings.ORDER_WORKERS * settings.EXECUTION_NODE_COUNT
    global_index = settings.EXECUTION_NODE_INDEX * settings.ORDER_WORKERS + index

    def apply(order):
        if partition(order.instrument_id, total) != global_index:
            return
        symbol = order.instrument.sym_ticker
        books.setdefault(symbol, IndexedOrderBook()).upsert(order_payload(order))
        if symbol not in calendars:
            calendar = MarketSessionCalendar.for_instrument(order.instrument)
            today = datetime.now(calendar.zone).date()
            calendar.load_holidays(today, today + timedelta(days=7))
            calendars[symbol] = calendar

    for order in Order.objects.filter(status="OPEN").select_related("instrument").iterator(chunk_size=1000):
        apply(order)
    last_renew = 0
    last_calendar = 0
    try:
        while not stop.is_set():
            close_old_connections()
            if time.monotonic() - last_renew >= 3:
                if not lease.renew():
                    raise RuntimeError("Terminal ownership lost")
                last_renew = time.monotonic()
                runtime_redis().set(f"quantnest:terminal:cursor:{global_index}", cursor, ex=30)
                runtime_redis().set(f"quantnest:health:terminal:{global_index}", str(time.time()), ex=15)
            if time.monotonic() - last_calendar >= 60:
                for calendar in calendars.values():
                    today = datetime.now(calendar.zone).date()
                    calendar.load_holidays(today, today + timedelta(days=14))
                last_calendar = time.monotonic()
            for _, messages in runtime_redis().xread({stream: cursor}, count=1000, block=50):
                for message_id, fields in messages:
                    payload = json.loads(fields["payload"])
                    # Read the committed row, so delayed commands cannot resurrect cancelled orders.
                    order = Order.objects.select_related("instrument").filter(pk=payload["id"]).first()
                    if order:
                        apply(order)
                    else:
                        for book in books.values():
                            book.remove(payload["id"])
                    cursor = message_id
            for symbol, book in tuple(books.items()):
                if not book.orders:
                    continue
                if symbol not in markets:
                    try:
                        markets[symbol] = SharedMemoryManager(symbol, "1m")
                        sequences[symbol] = markets[symbol].tick_counter
                        gaps[symbol] = markets[symbol].source_gap
                    except FileNotFoundError:
                        continue
                ticks, gap = markets[symbol].read_ticks(sequences[symbol], limit=1)
                if gap or gaps[symbol] != markets[symbol].source_gap:
                    gaps[symbol] = markets[symbol].source_gap
                    logger.error("Terminal tick history gap symbol=%s; awaiting fresh ticks", symbol)
                    sequences[symbol] = markets[symbol].tick_counter
                    continue
                calendar = calendars[symbol]
                for sequence, event_time, received, price, volume in ticks:
                    local = datetime.fromtimestamp(event_time, timezone.utc).astimezone(calendar.zone)
                    if not 0 <= time.time() - received <= 15 or not calendar.is_trading_day(local.date()):
                        sequences[symbol] = int(sequence)
                        continue
                    if not calendar.session_open(local.date()) <= local < calendar.session_close(local.date()):
                        sequences[symbol] = int(sequence)
                        continue
                    fills, activated = book.match(price, limit=settings.TERMINAL_MATCH_BATCH)
                    for identity in activated:
                        with transaction.atomic():
                            order = Order.objects.select_for_update().filter(pk=identity, status="OPEN").first()
                            if order and order.order_type == "STOP_LIMIT":
                                order.order_type, order.trigger_price = "LIMIT", None
                                order.save(update_fields=["order_type", "trigger_price"])
                    for identity in fills:
                        order = Order.objects.filter(pk=identity).first()
                        if not order:
                            continue
                        try:
                            TradingOrderService.execute_order(order, Decimal(str(price)))
                        except Exception:
                            logger.exception("Terminal fill failed order=%s; restoring committed order", identity)
                            order.refresh_from_db()
                            apply(order)
                    if not book.has_matches(price):
                        sequences[symbol] = int(sequence)
    finally:
        for market in markets.values():
            market.close()
        lease.release()
