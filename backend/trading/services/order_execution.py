# backend/trading/services/order_execution.py
import os
import json
from decimal import Decimal
from datetime import datetime, timezone

import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from trading.models import PaperOrder, PaperTrade, PaperPosition, PaperAccount, AuditLog
from trading.orderbook import add_order_to_orderbook, remove_order_from_orderbook_by_oid, match_in_orderbook, activate_bracket_children, cancel_oco_siblings

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
channel_layer = get_channel_layer()

def _broadcast_user(user_id: int, payload: dict):
    try:
        async_to_sync(channel_layer.group_send)(f"user_{user_id}", {"type": "user.message", "payload": payload})
    except Exception:
        pass

def _create_audit(order: PaperOrder, action: str, performed_by=None, details=None):
    AuditLog.objects.create(order=order, action=action, performed_by=performed_by, details=details or {})

@transaction.atomic
def execute_market_fill(order: PaperOrder, fill_qty: int, fill_price: Decimal, performed_by=None):
    """
    Execute fill and handle both long and short position mechanics.
    """
    if fill_qty <= 0 or order.remaining_qty() <= 0:
        return None

    order = PaperOrder.objects.select_for_update().get(id=order.id)
    if order.status not in (PaperOrder.STATUS_PENDING, PaperOrder.STATUS_PARTIAL):
        return None

    prev_filled = order.filled_qty or 0
    new_filled_qty = prev_filled + fill_qty
    total_prev = (order.avg_fill_price or Decimal("0")) * prev_filled
    total_new = total_prev + (Decimal(fill_price) * fill_qty)
    order.filled_qty = new_filled_qty
    order.avg_fill_price = (total_new / new_filled_qty) if new_filled_qty else None
    order.status = PaperOrder.STATUS_FILLED if order.remaining_qty() == 0 else PaperOrder.STATUS_PARTIAL
    order.updated_at = datetime.now(timezone.utc)
    order.save(update_fields=["filled_qty", "avg_fill_price", "status", "updated_at"])

    trade = PaperTrade.objects.create(order=order, qty=fill_qty, price=fill_price)

    # Update positions with short support
    if order.side == "BUY":
        pos, _ = PaperPosition.objects.select_for_update().get_or_create(user=order.user, symbol=order.symbol, defaults={"qty": 0, "avg_price": Decimal("0")})
        if pos.qty < 0:
            # closing short first
            close_qty = min(abs(pos.qty), fill_qty)
            pnl = (pos.avg_price - Decimal(fill_price)) * close_qty
            pos.realized_pnl += pnl
            pos.qty += close_qty  # less negative
            remaining = fill_qty - close_qty
            if remaining > 0:
                prev_qty = pos.qty
                prev_avg = pos.avg_price or Decimal("0")
                new_qty = prev_qty + remaining
                pos.avg_price = ((prev_avg * prev_qty) + (Decimal(fill_price) * remaining)) / new_qty if new_qty != 0 else Decimal("0")
                pos.qty = new_qty
        else:
            prev_qty = pos.qty
            prev_avg = pos.avg_price or Decimal("0")
            new_qty = prev_qty + fill_qty
            pos.avg_price = ((prev_avg * prev_qty) + (Decimal(fill_price) * fill_qty)) / new_qty if new_qty != 0 else Decimal("0")
            pos.qty = new_qty
        pos.save()
    else:  # SELL
        pos, _ = PaperPosition.objects.select_for_update().get_or_create(user=order.user, symbol=order.symbol, defaults={"qty": 0, "avg_price": Decimal("0")})
        if pos.qty > 0:
            close_qty = min(pos.qty, fill_qty)
            pnl = (Decimal(fill_price) - pos.avg_price) * close_qty
            pos.realized_pnl += pnl
            pos.qty -= close_qty
            remaining = fill_qty - close_qty
            if remaining > 0:
                # remaining opens/increases short
                pos.qty -= remaining
        else:
            pos.qty -= fill_qty
        pos.save()

    acc, _ = PaperAccount.objects.select_for_update().get_or_create(user=order.user, defaults={"balance": Decimal("100000.00"), "equity": Decimal("100000.00"), "margin_used": Decimal("0")})
    if order.side == "BUY":
        acc.balance -= Decimal(fill_price) * fill_qty
    else:
        acc.balance += Decimal(fill_price) * fill_qty
    acc.equity = acc.balance
    acc.save()

    _create_audit(order, AuditLog.ACTION_EXECUTED, performed_by=performed_by, details={"fill_qty": fill_qty, "fill_price": str(fill_price)})
    _broadcast_user(order.user_id, {"type": "order_update", "order_id": order.id})
    _broadcast_user(order.user_id, {"type": "position_update", "symbol": order.symbol})
    _broadcast_user(order.user_id, {"type": "account_update", "balance": str(acc.balance), "equity": str(acc.equity)})

    if order.status == PaperOrder.STATUS_FILLED:
        if order.children.exists():
            activate_bracket_children(order)
        if order.oco_group:
            cancel_oco_siblings(order)

    return trade

def process_slm_triggers(symbol: str, ltp: Decimal, performed_by=None):
    """
    Find pending SL-M orders for symbol and execute at LTP when trigger condition met.
    """
    triggered = []
    try:
        pending_ids = set(r.smembers(f"orders:pending:{symbol}") or [])
    except Exception:
        pending_ids = set()

    if pending_ids:
        qs = PaperOrder.objects.filter(id__in=list(pending_ids), status=PaperOrder.STATUS_PENDING, is_slm=True)
    else:
        qs = PaperOrder.objects.filter(symbol=symbol, status=PaperOrder.STATUS_PENDING, is_slm=True)

    for order in qs.select_for_update():
        try:
            if order.stop_trigger_price is None:
                continue
            trig = Decimal(str(order.stop_trigger_price))
            if order.side == "BUY" and ltp >= trig:
                execute_market_fill(order, order.remaining_qty(), ltp, performed_by=performed_by)
                _create_audit(order, AuditLog.ACTION_TRIGGERED, performed_by=performed_by, details={"trigger_price": str(trig), "ltp": str(ltp)})
                triggered.append(order.id)
            elif order.side == "SELL" and ltp <= trig:
                execute_market_fill(order, order.remaining_qty(), ltp, performed_by=performed_by)
                _create_audit(order, AuditLog.ACTION_TRIGGERED, performed_by=performed_by, details={"trigger_price": str(trig), "ltp": str(ltp)})
                triggered.append(order.id)
        except Exception:
            continue
    return triggered
