"""Account reconciliation uses the same reducer as the order WebSocket."""
import logging

logger = logging.getLogger(__name__)


class BrokerReconciliationService:
    def __init__(self, credential):
        self.credential = credential

    def reconcile_orders(self):
        from brokers.services import BrokerService
        from live_trading.order_processor import apply_order_observation
        rows = BrokerService.get_orderbook(self.credential)
        if isinstance(rows, dict):
            rows = BrokerService.normalize_order_payload(self.credential, rows)
        if not isinstance(rows, list):
            raise ValueError("Broker orderbook must be normalized to a list")
        results = {"total_orders": len(rows), "matched": 0, "external": 0, "mismatched": 0, "errors": []}
        for row in rows:
            try:
                order = apply_order_observation(self.credential, row)
                key = "external" if order is None else "matched" if order.reconciliation_status == "MATCHED" else "mismatched"
                results[key] += 1
            except Exception as exc:
                logger.exception("Order reconciliation failed credential=%s", self.credential.pk)
                results["errors"].append(type(exc).__name__)
        return results

    def reconcile_positions(self):
        from brokers.services import BrokerService
        from live_trading.order_processor import observe_account_position
        rows = BrokerService.get_positions(self.credential)
        if isinstance(rows, dict):
            rows = BrokerService.normalize_position_payload(self.credential, rows)
        if not isinstance(rows, list):
            raise ValueError("Broker positions must be normalized to a list")
        results = {"total_positions": len(rows), "matched": 0, "mismatched": 0, "errors": []}
        observed = set()
        for row in rows:
            try:
                observation = observe_account_position(self.credential, row)
                observed.add((row["symbol"], row.get("product_type") or None))
                results["matched" if observation.matched else "mismatched"] += 1
            except Exception as exc:
                logger.exception("Position reconciliation failed credential=%s", self.credential.pk)
                results["errors"].append(type(exc).__name__)
        # Missing broker rows also matter: compare against zero without changing ownership.
        from live_trading.models import LivePosition
        for symbol, product in LivePosition.objects.filter(
            broker_credential=self.credential, quantity__gt=0
        ).values_list("instrument__sym_ticker", "product_type").distinct():
            if (symbol, product) not in observed and (symbol, None) not in observed:
                observation = observe_account_position(self.credential, {
                    "symbol": symbol, "product_type": product, "quantity": 0,
                })
                results["matched" if observation.matched else "mismatched"] += 1
        return results
