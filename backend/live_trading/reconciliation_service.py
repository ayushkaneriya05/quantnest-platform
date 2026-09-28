"""
Broker Reconciliation Service
Fallback mechanism when WebSocket fails.
Reconciles DB state with broker REST API.
"""

import logging
from typing import Dict, Any, List
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class BrokerReconciliationService:
    """
    Fallback mechanism when WebSocket fails.
    Reconciles DB state with broker REST API.
    """
    
    def __init__(self, session):
        """
        Initialize reconciliation service.

        Args:
            session: TradingSession instance for the live strategy being reconciled.
        """
        self.session = session
        self.credential = getattr(session, "broker_credential", session)
        
    def reconcile_orders(self) -> Dict[str, Any]:
        """
        Reconcile orders via REST API.
        
        Returns:
            Dictionary with reconciliation results
        """
        from brokers.services import BrokerService
        from live_trading.models import LiveOrder
        from common.enums import OrderStatus
        
        results = {
            "total_orders": 0,
            "matched": 0,
            "mismatched": 0,
            "created": 0,
            "errors": []
        }
        
        if self.session is None:
            logger.error("BrokerReconciliationService requires a live TradingSession instance.")
            return results

        try:
            orderbook = BrokerService.get_orderbook(self.credential)
            if isinstance(orderbook, dict):
                orderbook = BrokerService.normalize_order_payload(self.credential, orderbook)

            if not isinstance(orderbook, list):
                logger.error(f"Invalid orderbook format from broker: {type(orderbook)}")
                return results

            results["total_orders"] = len(orderbook)

            for row in orderbook:
                broker_order_id = row.get("broker_order_id") or row.get("id") or row.get("orderid") or row.get("orderNumStatus")
                if not broker_order_id:
                    continue
                
                try:
                    order = LiveOrder.objects.filter(session=self.session, broker_order_id=broker_order_id).first()
                    if order is None:
                        row_tag = str(row.get("order_tag") or row.get("orderTag") or row.get("tag") or "")
                        if row_tag.startswith("QN"):
                            try:
                                order = LiveOrder.objects.filter(session=self.session, pk=int(row_tag[2:])).first()
                            except ValueError:
                                order = None
                    if order is None:
                        raise LiveOrder.DoesNotExist
                    with transaction.atomic():
                        order = LiveOrder.objects.select_for_update().get(pk=order.pk)
                        previous_filled_quantity = int(order.filled_quantity or 0)

                        broker_status = BrokerService._normalize_order_status(self.credential, row.get("status") or row.get("orderStatus") or row.get("orderNumStatus"))
                        filled_qty = max(int(row.get("filled_quantity") or row.get("filledQty") or 0), 0)
                        fill_price = row.get("avg_fill_price") or row.get("tradedPrice") or row.get("avgPrice") or row.get("price")
                        missing_fill_price = filled_qty > previous_filled_quantity and float(fill_price or 0) <= 0

                        if order.status != broker_status:
                            logger.warning("Order %s status mismatch: DB=%s, Broker=%s", broker_order_id, order.status, broker_status)
                            results["mismatched"] += 1
                        else:
                            results["matched"] += 1

                        order.status = "UNKNOWN" if missing_fill_price else broker_status
                        order.filled_quantity = previous_filled_quantity if missing_fill_price else max(previous_filled_quantity, filled_qty)
                        order.pending_quantity = max(int(order.quantity or 0) - order.filled_quantity, 0)
                        if fill_price:
                            if float(fill_price or 0) > 0:
                                order.avg_fill_price = fill_price
                        order.broker_order_id = str(broker_order_id)
                        order.reconciliation_status = "PENDING" if missing_fill_price else "MATCHED"
                        order.reconciliation_attempts += 1
                        order.last_reconciliation = timezone.now()
                        order.save(update_fields=[
                            "status", "filled_quantity", "pending_quantity", "avg_fill_price",
                            "reconciliation_status", "reconciliation_attempts", "last_reconciliation",
                            "broker_order_id", "updated_at",
                        ])

                        fill_delta = max(filled_qty - previous_filled_quantity, 0)
                        if fill_delta > 0 and float(fill_price or 0) > 0:
                            self._ensure_position_exists(order, fill_delta, fill_price)

                    from strategy_engine.runtime import StrategyRuntimeState
                    StrategyRuntimeState.reconcile_trade_state("live", self.session.id, order.instrument_id, failed_reason=(order.reason if broker_status in {OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED} else None))
                        
                except LiveOrder.DoesNotExist:
                    # External order not in our DB
                    logger.info(f"External order {broker_order_id} found in broker but not in DB")
                    self._create_external_order(row)
                    results["created"] += 1
                    
                except Exception as e:
                    logger.exception(f"Error reconciling order {broker_order_id}: {e}")
                    results["errors"].append(str(e))
                    
        except Exception as e:
            logger.exception(f"Error fetching orderbook for reconciliation: {e}")
            results["errors"].append(str(e))
        
        logger.info(f"Order reconciliation completed: {results}")
        return results
    
    def reconcile_positions(self) -> Dict[str, Any]:
        """
        Reconcile positions via REST API.
        
        Returns:
            Dictionary with reconciliation results
        """
        from brokers.services import BrokerService
        from live_trading.models import LivePosition
        from common.enums import Side
        
        results = {
            "total_positions": 0,
            "matched": 0,
            "mismatched": 0,
            "created": 0,
            "updated": 0,
            "errors": []
        }
        
        try:
            positions = BrokerService.get_positions(self.credential)
            if isinstance(positions, dict):
                positions = BrokerService.normalize_position_payload(self.credential, positions)
            
            if not isinstance(positions, list):
                logger.error(f"Invalid positions format from broker: {type(positions)}")
                return results
            
            results["total_positions"] = len(positions)
            
            for row in positions:
                symbol = row.get("symbol")
                if not symbol:
                    continue
                
                # Resolve instrument
                instrument = self._resolve_instrument(symbol)
                if not instrument:
                    logger.warning(f"Could not resolve instrument for symbol {symbol}")
                    continue
                
                # Determine side
                net_qty = int(row.get("quantity") or row.get("netQty") or row.get("net_qty") or row.get("qty") or 0)
                side_value = row.get("side")
                if str(side_value or "").strip().upper() in ("BUY", "B", "1"):
                    side = Side.BUY
                elif str(side_value or "").strip().upper() in ("SELL", "S", "-1"):
                    side = Side.SELL
                elif net_qty > 0:
                    side = Side.BUY
                elif net_qty < 0:
                    side = Side.SELL
                else:
                    logger.warning("Skipping broker position with unknown side for %s", instrument.sym_ticker)
                    continue
                if net_qty == 0:
                    continue  # Zero quantity position, skip
                
                try:
                    position = LivePosition.objects.get(allocation=self.session.allocation, broker_credential=self.credential, instrument=instrument, side=side)
                    
                    # Check for mismatch
                    if position.quantity != abs(net_qty):
                        logger.warning(
                            f"Position {instrument.sym_ticker} {side} quantity mismatch: "
                            f"DB={position.quantity}, Broker={abs(net_qty)}"
                        )
                        results["mismatched"] += 1
                    else:
                        results["matched"] += 1
                    
                    # Update position with broker state
                    position.quantity = abs(net_qty)
                    position.avg_price = row.get("avg_price") or row.get("avgPrice") or row.get("avg_price") or position.avg_price
                    position.current_price = row.get("current_price") or row.get("ltp") or position.current_price
                    position.unrealized_pnl = (
                        row.get("unrealized_pnl")
                        if row.get("unrealized_pnl") is not None
                        else row.get("unrealized_profit")
                        if row.get("unrealized_profit") is not None
                        else row.get("pl")
                        if row.get("pl") is not None
                        else 0
                    )
                    position.broker_position_id = row.get("broker_position_id") or row.get("id") or ""
                    position.sync_status = "SYNCED"
                    position.last_sync_attempt = timezone.now()
                    position.last_broker_sync = timezone.now()
                    position.sync_error = ""
                    
                    position.save(update_fields=[
                        "quantity", "avg_price", "current_price", "unrealized_pnl",
                        "broker_position_id", "sync_status", "last_sync_attempt",
                        "last_broker_sync", "sync_error", "updated_at"
                    ])
                    
                    results["updated"] += 1
                    
                except LivePosition.DoesNotExist:
                    # Position in broker but not in our DB
                    logger.info(f"External position found for {instrument.sym_ticker} {side}")
                    self._create_external_position(row, instrument, side)
                    results["created"] += 1
                    
                except Exception as e:
                    logger.exception(f"Error reconciling position {symbol}: {e}")
                    results["errors"].append(str(e))
                    
        except Exception as e:
            logger.exception(f"Error fetching positions for reconciliation: {e}")
            results["errors"].append(str(e))
        
        logger.info(f"Position reconciliation completed: {results}")
        return results
    
    def _ensure_position_exists(self, order, filled_quantity, fill_price):
        """
        Ensure position exists for a filled order.
        
        Args:
            order: LiveOrder instance
            filled_quantity: Filled quantity
            fill_price: Fill price
        """
        if float(fill_price or 0) <= 0:
            logger.warning("Deferring fill application for order %s because broker fill price is missing", order.broker_order_id)
            return

        from live_trading.services import LiveExecutionService
        
        LiveExecutionService._apply_fill_to_position(order, filled_quantity, fill_price, None)
        logger.info("Applied %s reconciled fill for order %s", filled_quantity, order.broker_order_id)
    
    def _create_external_order(self, row: Dict[str, Any]) -> None:
        """
        Create external order from broker data.
        
        Args:
            row: Broker order data
        """
        from live_trading.models import LiveOrder
        from common.enums import OrderType, ProductType
        
        session = self.session
        if not session:
            logger.warning(f"No active session available for credential {self.credential.id}, skipping external order")
            return

        # Resolve instrument
        instrument = self._resolve_instrument(row.get("symbol"))
        if not instrument:
            logger.warning(f"Could not resolve instrument for symbol {row.get('symbol')}")
            return
        
        broker_order_id = row.get("broker_order_id") or row.get("id") or row.get("orderid") or row.get("broker_order_id")
        from brokers.services import BrokerService
        broker_status = BrokerService._normalize_order_status(
            self.credential,
            row.get("status") or row.get("orderStatus") or row.get("orderNumStatus")
        )
        row_type = row.get("order_type") or row.get("type")
        if row_type in (1, "1", "LIMIT", "LIMIT_ORDER"):
            mapped_order_type = OrderType.LIMIT
        elif row_type in (2, "2", "MARKET", "MARKET_ORDER"):
            mapped_order_type = OrderType.MARKET
        else:
            mapped_order_type = OrderType.MARKET if row.get("price") in (None, 0, "0") else OrderType.LIMIT

        if not broker_order_id:
            logger.warning("Skipping broker order without an order ID during reconciliation")
            return

        # REST reconciliation and WebSocket delivery can discover the same
        # broker order concurrently. The DB uniqueness constraint is the final
        # guard; get_or_create keeps the normal repeated path idempotent.
        order, created = LiveOrder.objects.get_or_create(
            broker_credential=self.credential,
            broker_order_id=broker_order_id,
            defaults={
                "user": session.user,
                "strategy": session.strategy,
                "session": session,
                "allocation": session.allocation,
                "instrument": instrument,
                "order_type": mapped_order_type,
                "product_type": row.get("product_type") or row.get("productType") or ProductType.INTRADAY,
                "side": self._map_broker_side_to_internal(row.get("side")),
                "price": row.get("price") or row.get("limitPrice") or 0,
                "quantity": int(row.get("quantity") or row.get("qty") or 0),
                "exchange_order_id": row.get("exchange_order_id") or row.get("exchOrdId") or "",
                "status": broker_status,
                "filled_quantity": int(row.get("filled_quantity") or row.get("filledQty") or 0),
                "pending_quantity": int(row.get("pending_quantity") or row.get("remainingQuantity") or 0),
                "avg_fill_price": row.get("avg_fill_price") or row.get("tradedPrice") or row.get("avgPrice") or 0,
                "reconciliation_status": "MATCHED",
                "last_reconciliation": timezone.now(),
            },
        )

        logger.info("%s external order %s during reconciliation", "Created" if created else "Reused", broker_order_id)
    
    def _create_external_position(self, row: Dict[str, Any], instrument, side) -> None:
        """
        Create external position from broker data.
        
        Args:
            row: Broker position data
            instrument: Instrument instance
            side: Side string (BUY/SELL)
        """
        from live_trading.models import LivePosition
        
        session = self.session
        if not session:
            logger.warning(f"No active session available for credential {self.credential.id}, skipping external position")
            return

        net_qty = int(row.get("quantity") or row.get("netQty") or row.get("net_qty") or row.get("qty") or 0)

        # Create external position record
        LivePosition.objects.create(
            user=session.user,
            strategy=session.strategy,
            allocation=session.allocation,
            broker_credential=self.credential,
            instrument=instrument,
            product_type=row.get("product_type") or row.get("productType") or "INTRADAY",
            side=side,
            quantity=abs(net_qty),
            avg_price=row.get("avg_price") or row.get("avgPrice") or row.get("avg_price") or 0,
            current_price=row.get("current_price") or row.get("ltp") or 0,
            unrealized_pnl=(
                row.get("unrealized_pnl")
                if row.get("unrealized_pnl") is not None
                else row.get("unrealized_profit")
                if row.get("unrealized_profit") is not None
                else row.get("pl")
                if row.get("pl") is not None
                else 0
            ),
            broker_position_id=row.get("broker_position_id") or row.get("id") or "",
            sync_status="SYNCED",
            last_sync_attempt=timezone.now(),
            last_broker_sync=timezone.now()
        )
        
        logger.info(f"Created external position for {instrument.sym_ticker} {side}")
    
    def _resolve_instrument(self, symbol: str):
        """
        Resolve broker symbol to Instrument model.
        
        Args:
            symbol: Broker symbol (e.g., "NSE:SBIN-EQ")
            
        Returns:
            Instrument instance or None
        """
        from instruments.models import Instrument
        
        if not symbol:
            return None
        
        # Try exact match first
        instrument = Instrument.objects.filter(sym_ticker=symbol).first()
        if instrument:
            return instrument
        
        # Try to normalize symbol (remove exchange prefix)
        normalized = str(symbol).split(":")[-1]
        instrument = Instrument.objects.filter(symbol=normalized).first()
        if instrument:
            return instrument
        
        # Try case-insensitive match
        instrument = Instrument.objects.filter(symbol__iexact=normalized).first()
        return instrument
    
    def _map_broker_side_to_internal(self, broker_side: Any) -> str:
        """
        Map broker side value to internal Side.
        
        Args:
            broker_side: Broker side value
            
        Returns:
            Internal Side string (BUY or SELL)
        """
        from common.enums import Side
        
        normalized_side = str(broker_side).strip().upper() if broker_side is not None else ""
        if normalized_side in ("1", "BUY", "B"):
            return Side.BUY
        elif normalized_side in ("-1", "SELL", "S"):
            return Side.SELL
        else:
            logger.warning("Unknown broker side value: %r", broker_side)
            return None
