"""Order-only broker synchronization; owned fills drive the local trading ledger."""
import logging
import re

from django.db import transaction
from django.utils import timezone

from live_trading.models import LiveOrder

logger = logging.getLogger(__name__)


def find_owned_order(credential, data):
    queryset = LiveOrder.objects.select_for_update(of=("self",)).filter(
        broker_credential=credential, user_id=credential.user_id
    ).select_related("instrument", "session__allocation")
    broker_id = str(data.get("broker_order_id") or "").strip()
    order = queryset.filter(broker_order_id=broker_id).first() if broker_id else None
    if order is None:
        tag = str(data.get("order_tag") or "")
        match = re.fullmatch(r"QN([1-9][0-9]*)", tag)
        if match:
            order = queryset.filter(pk=int(match[1])).first()
            if order and order.broker_order_id and order.broker_order_id != broker_id:
                return None
    if not order or not order.session_id or not order.allocation_id:
        return None
    if data.get("symbol") and data["symbol"] != order.instrument.sym_ticker:
        return None
    if data.get("side") and data["side"] != order.side:
        return None
    if data.get("quantity") and int(data["quantity"]) != order.quantity:
        return None
    return order


@transaction.atomic
def apply_order_observation(credential, data):
    from common.enums import ExecutionCommandType, ExecutionMode
    from execution.repository import enqueue

    order = find_owned_order(credential, data)
    if order is None:
        return None
    enqueue(ExecutionMode.LIVE, credential.pk, ExecutionCommandType.BROKER, {
        "identity": str(order.request_id), "broker_id": str(data["broker_order_id"]),
        "status": data["status"], "quantity": int(data["filled_quantity"]),
        "average": str(data["avg_fill_price"]),
        "at": data.get("broker_updated_at") or timezone.now().isoformat(),
        "updated_at": data.get("broker_updated_at"), "ordered_at": data.get("broker_ordered_at"),
        "exchange_order_id": data.get("exchange_order_id") or "",
        "error": data.get("rejection_reason") or "",
    })
    return order


def reconcile_orders(credential):
    """Poll owned order states through the same cumulative-fill writer as WebSocket."""
    from brokers.services import BrokerService
    rows = sorted(BrokerService.get_orderbook(credential),
                  key=lambda row: (row.get("broker_ordered_at") or "", row["broker_order_id"]))
    result = {"total_orders": len(rows), "matched": 0, "ignored": 0, "mismatched": 0, "errors": []}
    for row in rows:
        try:
            order = apply_order_observation(credential, row)
            key = "ignored" if order is None else "matched"
            result[key] += 1
        except Exception as exc:
            logger.exception("Order reconciliation failed credential=%s", credential.pk)
            result["errors"].append(type(exc).__name__)
    return result
