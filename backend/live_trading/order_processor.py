"""Account-scoped, transactional broker observations shared by REST and WebSocket."""
import re
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from live_trading.models import BrokerAccountObservation, LiveOrder, LivePosition
from trading_domain.orders import OrderState, observe_order


def find_owned_order(credential, data):
    queryset = LiveOrder.objects.select_for_update(of=("self",)).filter(
        broker_credential=credential, user_id=credential.user_id
    ).select_related("instrument", "strategy_version", "session__allocation")
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


def record_observation(credential, kind, key, data, **fields):
    # Store normalized fields only: raw broker payloads may contain credentials.
    payload = {name: str(data[name]) for name in (
        "symbol", "side", "quantity", "filled_quantity", "avg_fill_price", "status", "product_type"
    ) if name in data}
    return BrokerAccountObservation.objects.update_or_create(
        credential=credential, kind=kind, broker_key=str(key), defaults={
            "symbol": data.get("symbol") or "", "payload": payload, **fields,
        }
    )[0]


@transaction.atomic
def apply_order_observation(credential, data):
    from brokers.models import BrokerCredential
    from live_trading.services import LiveExecutionService
    from strategy_engine.runtime import StrategyRuntimeState

    # All fills for one account serialize, including concurrent REST and WS.
    BrokerCredential.objects.select_for_update().get(pk=credential.pk)
    broker_id = str(data.get("broker_order_id") or "").strip()
    if not broker_id:
        raise ValueError("Broker order identifier is required")
    order = find_owned_order(credential, data)
    if order is None:
        record_observation(credential, "ORDER", broker_id, data, matched=False)
        return None
    previous = OrderState(order.quantity, order.filled_quantity, order.filled_value, order.status)
    transition = observe_order(previous, status=data.get("status") or "UNKNOWN",
                               filled=data.get("filled_quantity", previous.filled),
                               average=data.get("avg_fill_price", 0))
    if transition.error:
        order.reconciliation_status = "PENDING"
        order.reason = transition.error
    else:
        order.status = transition.state.status
        order.filled_quantity = transition.state.filled
        order.filled_value = transition.state.value
        order.pending_quantity = max(order.quantity - order.filled_quantity, 0)
        if order.filled_quantity:
            order.avg_fill_price = order.filled_value / Decimal(order.filled_quantity)
        order.reconciliation_status = "MATCHED"
    order.broker_order_id = broker_id
    order.exchange_order_id = data.get("exchange_order_id") or order.exchange_order_id
    order.reconciliation_attempts += 1
    order.last_reconciliation = timezone.now()
    if transition.fill_quantity:
        version = order.strategy_version
        if version is None:
            raise ValueError("An owned order must retain its deployed strategy snapshot")
        order.executed_at = order.executed_at or timezone.now()
        LiveExecutionService._apply_fill_to_position(
            order, transition.fill_quantity, transition.fill_price, version.config_snapshot
        )
    order.save(update_fields=["status", "reason", "filled_quantity", "filled_value", "pending_quantity",
                             "avg_fill_price", "broker_order_id", "exchange_order_id", "executed_at",
                             "reconciliation_status", "reconciliation_attempts", "last_reconciliation", "updated_at"])
    StrategyRuntimeState.reconcile_trade_state(
        "live", order.session_id, order.instrument_id,
        failed_reason=order.reason if order.status in {"REJECTED", "CANCELLED", "EXPIRED"} else None,
        settled_request_id=order.request_id,
    )
    BrokerAccountObservation.objects.filter(credential=credential, kind="ORDER", broker_key=broker_id).delete()
    return order


@transaction.atomic
def observe_account_position(credential, data):
    """Broker positions are account totals, never strategy positions."""
    from brokers.models import BrokerCredential
    BrokerCredential.objects.select_for_update().get(pk=credential.pk)
    symbol = data.get("symbol")
    if not symbol:
        raise ValueError("A normalized position symbol is required")
    product = data.get("product_type")
    positions = LivePosition.objects.filter(broker_credential=credential, instrument__sym_ticker=symbol)
    if product:
        positions = positions.filter(product_type=product)
    expected = sum(qty if side == "BUY" else -qty for qty, side in positions.values_list("quantity", "side"))
    quantity = int(data.get("quantity") or 0)
    observed = -abs(quantity) if data.get("side") == "SELL" else quantity
    observation = record_observation(credential, "POSITION", f"{symbol}:{product or 'ALL'}", data,
                                     expected_quantity=expected, observed_quantity=observed, matched=expected == observed)
    if expected != observed:
        from notifications.services import NotificationService
        NotificationService.notify(user=credential.user,
            title="Broker account position differs from strategy records",
            message=f"{symbol}: broker total {observed}, owned strategy total {expected}. Review account activity before attributing the difference to a strategy.",
            data={"module": "live", "credential_id": credential.pk, "observation_id": observation.pk, "symbol": symbol},
            dedupe_key=f"account-discrepancy:{observation.pk}:{expected}:{observed}:{timezone.localdate()}")
    return observation
