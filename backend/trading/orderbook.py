# backend/trading/orderbook.py
import os
import json
import time
from decimal import Decimal
import redis
from django.db import transaction
from django.utils import timezone
from .models import PaperOrder, PaperTrade, PaperPosition, PaperAccount

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

MULT = 1e8

def _order_member(order_id, ts=None):
    return json.dumps({"oid": str(order_id), "ts": int(ts or time.time() * 1000)})

def _price_score(price: float, side: str):
    """
    Score for sorted set:
    - bids: negative price (so highest price -> smallest negative -> zrange 0 gives best bid)
    - asks: positive price (lowest ask -> zrange 0)
    """
    if side == "BUY":
        return -int(price * MULT)
    return int(price * MULT)

def add_order_to_orderbook(order: PaperOrder):
    """
    Add order to appropriate orderbook zset and keep the exact member under order:member:<id>.
    If order already has mapping, re-use it (so partial fills keep same member).
    """
    sym = order.symbol
    price = float(order.price or 0.0)

    member = r.get(f"order:member:{order.id}")
    if not member:
        member = _order_member(order.id)
        r.set(f"order:member:{order.id}", member)

    if order.side == "BUY":
        score = _price_score(price, "BUY")
        r.zadd(f"orderbook:bids:{sym}", {member: score})
    else:
        score = _price_score(price, "SELL")
        r.zadd(f"orderbook:asks:{sym}", {member: score})
    # ensure pending set contains id
    r.sadd(f"orders:pending:{sym}", str(order.id))
    return member

def remove_order_from_orderbook_by_oid(symbol: str, order_id: int):
    """
    Remove orderbook member for given order id using stored mapping.
    """
    member = r.get(f"order:member:{order_id}")
    if not member:
        return False
    r.zrem(f"orderbook:bids:{symbol}", member)
    r.zrem(f"orderbook:asks:{symbol}", member)
    r.delete(f"order:member:{order_id}")
    r.srem(f"orders:pending:{symbol}", str(order_id))
    return True


def peek_best(side_key: str, symbol: str):
    key = f"orderbook:{side_key}:{symbol}"
    res = r.zrange(key, 0, 0, withscores=True)
    if not res:
        return None
    return res[0]  # (member_json, score)


def pop_best(side_key: str, symbol: str):
    """
    Pop best member from sorted set atomically (ZPOPMIN / ZPOPMAX not used because earlier we used sign trick).
    We'll use ZRANGE + ZREM in pipeline with optimistic assumption small contention.
    """
    key = f"orderbook:{side_key}:{symbol}"
    res = r.zrange(key, 0, 0)
    if not res:
        return None
    member = res[0]
    # remove member
    r.zrem(key, member)
    return member

def match_in_orderbook(incoming_order: PaperOrder):
    """
    Price-time matching using passive order's price as trade price.
    Supports partial fills. Does NOT update member (so original timestamp persists).
    Handles short/long updates via update_positions_and_accounts_after_trade().
    """
    symbol = incoming_order.symbol
    remaining = incoming_order.qty - incoming_order.filled_qty
    matched_total = 0

    while remaining > 0:
        if incoming_order.side == "BUY":
            best = peek_best("asks", symbol)
        else:
            best = peek_best("bids", symbol)

        if not best:
            break

        member_json, score = best
        try:
            member_obj = json.loads(member_json)
            opp_oid = int(member_obj["oid"])
        except Exception:
            # remove malformed
            r.zrem(f"orderbook:asks:{symbol}", member_json)
            r.zrem(f"orderbook:bids:{symbol}", member_json)
            continue

        try:
            with transaction.atomic():
                opp_order = PaperOrder.objects.select_for_update().get(id=opp_oid)
                if opp_order.status != PaperOrder.STATUS_PENDING:
                    # cleanup
                    remove_order_from_orderbook_by_oid(symbol, opp_oid)
                    continue

                # price check for incoming limit
                if incoming_order.order_type == PaperOrder.ORDER_LIMIT:
                    if incoming_order.side == "BUY" and incoming_order.price < opp_order.price:
                        break
                    if incoming_order.side == "SELL" and incoming_order.price > opp_order.price:
                        break

                avail = opp_order.qty - opp_order.filled_qty
                if avail <= 0:
                    remove_order_from_orderbook_by_oid(symbol, opp_oid)
                    continue

                match_qty = min(remaining, avail)
                trade_price = opp_order.price  # passive price

                # update passive
                opp_order.filled_qty += match_qty
                opp_order.status = PaperOrder.STATUS_FILLED if opp_order.filled_qty >= opp_order.qty else PaperOrder.STATUS_PARTIAL
                opp_order.save(update_fields=["filled_qty", "status", "updated_at"])

                # update incoming
                incoming_order.filled_qty += match_qty
                incoming_order.status = PaperOrder.STATUS_FILLED if incoming_order.filled_qty >= incoming_order.qty else PaperOrder.STATUS_PARTIAL
                incoming_order.save(update_fields=["filled_qty", "status", "updated_at"])

                # create trades
                PaperTrade.objects.create(order=opp_order, qty=match_qty, price=trade_price)
                PaperTrade.objects.create(order=incoming_order, qty=match_qty, price=trade_price)

                # update positions & accounts
                update_positions_and_accounts_after_trade(
                    buy_order=(incoming_order if incoming_order.side == "BUY" else opp_order),
                    sell_order=(opp_order if incoming_order.side == "BUY" else incoming_order),
                    qty=match_qty, price=Decimal(str(trade_price))
                )

                matched_total += match_qty
                remaining = incoming_order.qty - incoming_order.filled_qty

                # if passive filled fully, remove mapping / pending
                if opp_order.status == PaperOrder.STATUS_FILLED:
                    remove_order_from_orderbook_by_oid(symbol, opp_oid)
                # if incoming filled, we exit
                if incoming_order.status == PaperOrder.STATUS_FILLED:
                    r.srem(f"orders:pending:{symbol}", str(incoming_order.id))
                    break
        except PaperOrder.DoesNotExist:
            remove_order_from_orderbook_by_oid(symbol, opp_oid)
            continue
        except Exception:
            import logging
            logging.exception("Orderbook match error")
            break

    return {"matched": matched_total, "remaining": incoming_order.qty - incoming_order.filled_qty}

def update_positions_and_accounts_after_trade(buy_order: PaperOrder, sell_order: PaperOrder, qty: int, price: Decimal):
    """
    Handles both long and short position logic.
    - BUY increases long position or reduces short (closing).
    - SELL increases short position or reduces long (closing).
    """
    # Buyer updates
    buyer = buy_order.user
    seller = sell_order.user

    # Buyer's position
    bpos, _ = PaperPosition.objects.get_or_create(user=buyer, symbol=buy_order.symbol, defaults={"qty": 0, "avg_price": Decimal("0")})
    # Seller's position
    spos, _ = PaperPosition.objects.get_or_create(user=seller, symbol=sell_order.symbol, defaults={"qty": 0, "avg_price": Decimal("0")})

    # BUY side handling:
    # If buyer had negative qty (short), then a buy closes short first
    if bpos.qty < 0:
        close_qty = min(abs(bpos.qty), qty)
        pnl = (bpos.avg_price - price) * close_qty  # short PnL: enter price - exit price
        bpos.realized_pnl += pnl
        bpos.qty += close_qty  # less negative
        qty_remaining = qty - close_qty
        if qty_remaining > 0:
            # remaining buys open/increase long
            prev_qty = bpos.qty
            prev_avg = bpos.avg_price or Decimal("0")
            new_qty = prev_qty + qty_remaining
            bpos.avg_price = ((prev_avg * prev_qty) + (price * qty_remaining)) / new_qty if new_qty != 0 else Decimal("0")
            bpos.qty = new_qty
    else:
        # normal long increase
        prev_qty = bpos.qty
        prev_avg = bpos.avg_price or Decimal("0")
        new_qty = prev_qty + qty
        bpos.avg_price = ((prev_avg * prev_qty) + (price * qty)) / new_qty if new_qty != 0 else Decimal("0")
        bpos.qty = new_qty
    bpos.save()

    # SELL side handling:
    # If seller had long position, sell reduces it and realizes PnL
    if spos.qty > 0:
        close_qty = min(spos.qty, qty)
        pnl = (price - spos.avg_price) * close_qty
        spos.realized_pnl += pnl
        spos.qty -= close_qty
        qty_remaining_seller = qty - close_qty
        if qty_remaining_seller > 0:
            # remaining sells open/increase short (negative qty)
            spos.qty -= qty_remaining_seller
    else:
        # seller already short or zero -> increase short
        spos.qty -= qty
    spos.save()

    # Accounts (simplified cash movement)
    bacc, _ = PaperAccount.objects.get_or_create(user=buyer, defaults={"balance": Decimal("100000.00"), "equity": Decimal("100000.00"), "margin_used": Decimal("0")})
    sacc, _ = PaperAccount.objects.get_or_create(user=seller, defaults={"balance": Decimal("100000.00"), "equity": Decimal("100000.00"), "margin_used": Decimal("0")})
    # buyer pays cash, seller receives cash
    bacc.balance -= price * qty
    sacc.balance += price * qty
    bacc.equity = bacc.balance
    sacc.equity = sacc.balance
    bacc.save()
    sacc.save()


import uuid

def create_bracket_children(entry_order: PaperOrder, tp_price, sl_price):
    """
    Create two child LIMIT orders for TP and SL as BRACKET_CHILD,
    but do not activate them until entry_order is FILLED.
    Returns (tp_order, sl_order)
    """
    # ensure oco group
    entry_order.create_oco_group()
    oco = entry_order.oco_group

    # TP order: opposite side to entry
    tp_side = "SELL" if entry_order.side == "BUY" else "BUY"
    tp = PaperOrder.objects.create(
        user=entry_order.user, symbol=entry_order.symbol, side=tp_side,
        qty=entry_order.qty, order_type="LIMIT", price=tp_price,
        parent=entry_order, order_tag="TP", status="PENDING", oco_group=oco
    )
    # SL order: could be limit or market-on-trigger; here we create LIMIT SL child
    sl_side = tp_side
    sl = PaperOrder.objects.create(
        user=entry_order.user, symbol=entry_order.symbol, side=sl_side,
        qty=entry_order.qty, order_type="LIMIT", price=sl_price,
        parent=entry_order, order_tag="SL", status="PENDING", oco_group=oco
    )

    # store mapping in redis for quick OCO management
    r.sadd(f"oco:group:{oco}", tp.id, sl.id)

    return tp, sl

def activate_bracket_children(entry_order: PaperOrder):
    """
    Called when entry_order is FILLED. This will add child orders to the orderbook (if LIMIT)
    or set them pending to be matched by process_tick.
    """
    children = entry_order.children.all()
    for ch in children:
        # mark as active pending in redis
        r.sadd(f"orders:pending:{ch.symbol}", str(ch.id))
        # if limit child: add to orderbook
        if ch.order_type == "LIMIT":
            add_order_to_orderbook(ch)
        # else for SL-M etc, just leave as pending for process_tick to treat when triggered

def cancel_oco_siblings(filled_order: PaperOrder):
    """
    When a child of an oco_group is FILLED, cancel other siblings in group.
    """
    ocog = filled_order.oco_group
    if not ocog:
        return
    members = r.smembers(f"oco:group:{ocog}") or set()
    for mid in members:
        if str(mid) == str(filled_order.id):
            continue
        # attempt to remove and cancel
        try:
            mid_int = int(mid)
            # fetch order
            try:
                o = PaperOrder.objects.get(id=mid_int)
                if o.status == "PENDING":
                    # mark cancelled
                    o.status = "CANCELLED"
                    o.save()
                # cleanup orderbook and pending set
                remove_order_from_orderbook_by_oid(o.symbol, o.id)
                r.srem(f"oco:group:{ocog}", mid)
            except PaperOrder.DoesNotExist:
                r.srem(f"oco:group:{ocog}", mid)
                continue
        except Exception:
            continue
    # remove group key if empty
    if r.scard(f"oco:group:{ocog}") == 0:
        r.delete(f"oco:group:{ocog}")