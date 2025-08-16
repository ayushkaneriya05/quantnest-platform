# backend/trading/tasks.py
import os
import json
from decimal import Decimal
from celery import shared_task
import redis
from django.db import transaction
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import PaperOrder, PaperTrade, PaperPosition, PaperAccount

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
channel_layer = get_channel_layer()

def should_fill_order(order: PaperOrder, tick: dict) -> bool:
    """
    Decide if the given order should be filled on the provided tick.
    Rules implemented:
     - MARKET: always fill
     - LIMIT BUY: fill if tick.last <= order.price
     - LIMIT SELL: fill if tick.last >= order.price
     - SL: treat as stop-limit if both trigger_price and price present
     - SL-M: trigger market when tick.last crosses trigger_price
    """
    ltp = Decimal(str(tick["last"]))
    if order.order_type == "MARKET":
        return True
    if order.order_type == "LIMIT":
        if order.side == "BUY" and ltp <= order.price:
            return True
        if order.side == "SELL" and ltp >= order.price:
            return True
    if order.order_type == "SL":
        # stop-limit: when trigger hit, execute limit order using order.price
        if order.trigger_price is None or order.price is None:
            return False
        if order.side == "BUY" and ltp >= order.trigger_price:
            # trigger hit (for buy stop) -> use limit price
            return ltp <= order.price
        if order.side == "SELL" and ltp <= order.trigger_price:
            return ltp >= order.price
    if order.order_type == "SL-M":
        if order.trigger_price is None:
            return False
        if order.side == "BUY" and ltp >= order.trigger_price:
            return True
        if order.side == "SELL" and ltp <= order.trigger_price:
            return True
    return False

def broadcast_user_update(user_id: int, payload: dict):
    """
    Helper to broadcast 'order_update'/'position_update'/'account_update' to user's group.
    """
    group = f"user_{user_id}"
    async_to_sync(channel_layer.group_send)(group, {"type": "user.message", "payload": payload})

# backend/trading/tasks.py
# ... keep imports above ...
from .orderbook import match_in_orderbook, add_order_to_orderbook, create_bracket_children, activate_bracket_children, cancel_oco_siblings

@shared_task(bind=True)
def process_tick(self, symbol: str, tick_json: str):
    """
    Handles a delayed tick:
    1. enqueues matching attempts for marketable orders and SL/SL-M triggers
    2. If orders are market orders or remaining quantity still marketable, attempt LTP fills
    """
    try:
        tick = json.loads(tick_json) if isinstance(tick_json, str) else tick_json
    except Exception:
        return {"error": "invalid tick_json"}

    pending_key = f"orders:pending:{symbol}"
    try:
        order_ids = r.smembers(pending_key) or set()
    except Exception:
        order_ids = set()

    results = {"symbol": symbol, "checked": 0, "matched": 0, "ltp_fills": 0}

    # For each pending order, check if it becomes marketable or trigger conditions reached.
    for oid in list(order_ids):
        results["checked"] += 1
        try:
            with transaction.atomic():
                order = PaperOrder.objects.select_for_update().get(id=int(oid))
                if order.status != "PENDING":
                    r.srem(pending_key, oid)
                    continue

                # Determine if this order should be considered now:
                # - LIMIT becomes marketable if LTP crosses price (we'll delegate matching to orderbook)
                # - SL/SL-M may trigger as well
                ltp = Decimal(str(tick["last"]))

                # For SL/SL-M we may convert into a market/limit on trigger:
                triggered = False
                if order.order_type == "SL":
                    if order.trigger_price is None:
                        continue
                    if order.side == "BUY" and ltp >= order.trigger_price:
                        # treat as limit (order.price expected)
                        triggered = True
                    if order.side == "SELL" and ltp <= order.trigger_price:
                        triggered = True
                elif order.order_type == "SL-M":
                    if order.trigger_price is None:
                        continue
                    if order.side == "BUY" and ltp >= order.trigger_price:
                        # convert to MARKET fill
                        order.order_type = "MARKET"
                        order.save()
                        triggered = True
                    if order.side == "SELL" and ltp <= order.trigger_price:
                        order.order_type = "MARKET"
                        order.save()
                        triggered = True

                # If LIMIT order and price is not crossing LTP, skip unless it's a passive order in book (handled elsewhere)
                marketable = False
                if order.order_type == "MARKET":
                    marketable = True
                elif order.order_type == "LIMIT":
                    if order.side == "BUY" and ltp <= order.price:
                        marketable = True
                    if order.side == "SELL" and ltp >= order.price:
                        marketable = True
                elif triggered:
                    marketable = True

                if not marketable:
                    continue

                # Now attempt to match in orderbook first (user-vs-user)
                match_res = match_in_orderbook(order)
                results["matched"] += match_res.get("matched", 0)
                remaining = order.qty - order.filled_qty

                # If remaining and it's a MARKET or SL-M converted to market, fill at LTP
                if remaining > 0 and order.order_type == "MARKET":
                    fill_qty = remaining
                    fill_price = ltp
                    # update order
                    order.filled_qty += fill_qty
                    order.avg_fill_price = ((order.avg_fill_price or Decimal("0")) * (order.filled_qty - fill_qty) + fill_price * fill_qty) / order.filled_qty
                    order.status = "FILLED" if order.filled_qty >= order.qty else "PARTIAL"
                    order.save()
                    if order.status == "FILLED":
                         # If this order is an ENTRY with children: activate children
                        if order.children.exists():
                            activate_bracket_children(order)
                        # If this order is a child (TP/SL) and has oco_group: cancel siblings
                        if order.oco_group: 
                            cancel_oco_siblings(order)
                    PaperTrade.objects.create(order=order, qty=fill_qty, price=fill_price)
                    # update position/account simple logic
                    # buyer / seller depending on side
                    if order.side == "BUY":
                        pos, _ = PaperPosition.objects.select_for_update().get_or_create(user=order.user, symbol=order.symbol, defaults={"qty":0,"avg_price":Decimal("0")})
                        prev_qty = pos.qty
                        prev_avg = pos.avg_price or Decimal("0")
                        new_qty = prev_qty + fill_qty
                        pos.avg_price = ((prev_avg * prev_qty) + (fill_price * fill_qty)) / new_qty if new_qty != 0 else Decimal("0")
                        pos.qty = new_qty
                        pos.save()
                    else:
                        pos, _ = PaperPosition.objects.select_for_update().get_or_create(user=order.user, symbol=order.symbol, defaults={"qty":0,"avg_price":Decimal("0")})
                        if pos.qty > 0:
                            close_qty = min(pos.qty, fill_qty)
                            pnl = (fill_price - pos.avg_price) * close_qty
                            pos.realized_pnl += pnl
                            pos.qty -= close_qty
                            pos.save()
                    acct, _ = PaperAccount.objects.select_for_update().get_or_create(user=order.user, defaults={"balance":Decimal("100000.00"),"equity":Decimal("100000.00"),"margin_used":Decimal("0")})
                    if order.side == "BUY":
                        acct.balance -= fill_price * fill_qty
                    else:
                        acct.balance += fill_price * fill_qty
                    acct.equity = acct.balance
                    acct.save()

                    results["ltp_fills"] += fill_qty

                    # cleanup pending set if fully filled
                    if order.status != "PENDING":
                        r.srem(pending_key, oid)

                # If after matching the order is still PENDING and limit-type, it should remain in the book
                if order.status == "PENDING" and order.order_type == "LIMIT":
                    # ensure it is in orderbook
                    # mapping and add helper will ensure idempotency
                    from .orderbook import add_order_to_orderbook
                    add_order_to_orderbook(order)

        except PaperOrder.DoesNotExist:
            r.srem(pending_key, oid)
            continue
        except Exception:
            import logging
            logging.exception("Error processing pending order %s", oid)
            continue

    return results
