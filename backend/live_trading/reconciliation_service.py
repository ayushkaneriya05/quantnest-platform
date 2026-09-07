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
    
    def __init__(self, credential):
        """
        Initialize reconciliation service.
        
        Args:
            credential: BrokerCredential instance
        """
        self.credential = credential
        
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
        
        try:
            orderbook = BrokerService.get_orderbook(self.credential)
            
            if not isinstance(orderbook, list):
                logger.error(f"Invalid orderbook format from broker: {type(orderbook)}")
                return results
            
            results["total_orders"] = len(orderbook)
            
            for row in orderbook:
                broker_order_id = row.get("id") or row.get("orderid") or row.get("broker_order_id")
                if not broker_order_id:
                    continue
                
                try:
                    order = LiveOrder.objects.get(broker_order_id=broker_order_id)
                    previous_filled_quantity = int(order.filled_quantity or 0)
                    
                    # Update order with REST data
                    broker_status = BrokerService._normalize_order_status(
                        self.credential,
                        row.get("status") or row.get("orderStatus") or row.get("orderNumStatus")
                    )
                    
                    filled_qty = max(int(row.get("filledQty") or row.get("filled_quantity") or 0), 0)
                    fill_price = row.get("tradedPrice") or row.get("avgPrice") or row.get("avg_fill_price")
                    
                    # Check for mismatch
                    if order.status != broker_status:
                        logger.warning(
                            f"Order {broker_order_id} status mismatch: "
                            f"DB={order.status}, Broker={broker_status}"
                        )
                        results["mismatched"] += 1
                    else:
                        results["matched"] += 1
                    
                    # Update order
                    order.status = broker_status
                    order.filled_quantity = filled_qty
                    order.pending_quantity = max(int(order.quantity or 0) - filled_qty, 0)
                    if fill_price:
                        order.avg_fill_price = fill_price
                    
                    order.reconciliation_status = "MATCHED"
                    order.reconciliation_attempts += 1
                    order.last_reconciliation = timezone.now()
                    
                    order.save(update_fields=[
                        "status", "filled_quantity", "pending_quantity",
                        "avg_fill_price", "reconciliation_status",
                        "reconciliation_attempts", "last_reconciliation", "updated_at"
                    ])
                    
                    # If order is FILLED and we missed WebSocket, ensure position exists
                    if broker_status == OrderStatus.FILLED and filled_qty > 0:
                        fill_delta = max(filled_qty - previous_filled_quantity, 0)
                        if fill_delta > 0:
                            self._ensure_position_exists(order, fill_delta, fill_price)
                        
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
                net_qty = row.get("netQty") or row.get("net_qty") or 0
                if net_qty > 0:
                    side = Side.BUY
                elif net_qty < 0:
                    side = Side.SELL
                else:
                    continue  # Zero quantity position, skip
                
                try:
                    position = LivePosition.objects.get(
                        broker_credential=self.credential,
                        instrument=instrument,
                        side=side
                    )
                    
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
                    position.avg_price = row.get("avgPrice") or row.get("avg_price") or position.avg_price
                    position.current_price = row.get("ltp") or position.current_price
                    position.unrealized_pnl = row.get("pl") or row.get("unrealized_profit") or 0
                    position.broker_position_id = row.get("id") or ""
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
        from live_trading.models import LivePosition
        from live_trading.services import LiveExecutionService
        
        try:
            # Call the existing position application logic
            LiveExecutionService._apply_fill_to_position(
                order,
                filled_quantity,
                fill_price,
                None
            )
            
            logger.info(f"Ensured position exists for filled order {order.broker_order_id}")
            
        except Exception as e:
            logger.exception(f"Error ensuring position exists for order {order.broker_order_id}: {e}")
    
    def _create_external_order(self, row: Dict[str, Any]) -> None:
        """
        Create external order from broker data.
        
        Args:
            row: Broker order data
        """
        from live_trading.models import LiveOrder, TradingSession
        from common.enums import OrderStatus, Side, OrderType, ProductType
        
        # Try to find a session for this credential
        session = TradingSession.objects.filter(
            broker_credential=self.credential,
            status__in=["RUNNING", "PAUSED"]
        ).first()
        
        if not session:
            logger.warning(f"No active session found for credential {self.credential.id}, skipping external order")
            return
        
        # Resolve instrument
        instrument = self._resolve_instrument(row.get("symbol"))
        if not instrument:
            logger.warning(f"Could not resolve instrument for symbol {row.get('symbol')}")
            return
        
        broker_order_id = row.get("id") or row.get("orderid") or row.get("broker_order_id")
        from brokers.services import BrokerService
        broker_status = BrokerService._normalize_order_status(
            self.credential,
            row.get("status") or row.get("orderStatus") or row.get("orderNumStatus")
        )
        
        # Create external order record
        LiveOrder.objects.create(
            user=session.user,
            strategy=session.strategy,
            session=session,
            allocation=session.allocation,
            broker_credential=self.credential,
            instrument=instrument,
            order_type=OrderType.MARKET,
            product_type=row.get("productType") or ProductType.INTRADAY,
            side=self._map_broker_side_to_internal(row.get("side")),
            price=row.get("limitPrice") or 0,
            quantity=int(row.get("qty") or 0),
            broker_order_id=broker_order_id,
            exchange_order_id=row.get("exchOrdId") or row.get("exchange_order_id") or "",
            status=broker_status,
            filled_quantity=int(row.get("filledQty") or row.get("filled_quantity") or 0),
            pending_quantity=int(row.get("remainingQuantity") or 0),
            avg_fill_price=row.get("tradedPrice") or 0,
            reconciliation_status="MATCHED",
            last_reconciliation=timezone.now()
        )
        
        logger.info(f"Created external order {broker_order_id}")
    
    def _create_external_position(self, row: Dict[str, Any], instrument, side) -> None:
        """
        Create external position from broker data.
        
        Args:
            row: Broker position data
            instrument: Instrument instance
            side: Side string (BUY/SELL)
        """
        from live_trading.models import LivePosition, TradingSession
        
        # Try to find a session for this credential
        session = TradingSession.objects.filter(
            broker_credential=self.credential,
            status__in=["RUNNING", "PAUSED"]
        ).first()
        
        if not session:
            logger.warning(f"No active session found for credential {self.credential.id}, skipping external position")
            return
        
        net_qty = row.get("netQty") or row.get("net_qty") or 0
        
        # Create external position record
        LivePosition.objects.create(
            user=session.user,
            strategy=session.strategy,
            allocation=session.allocation,
            broker_credential=self.credential,
            instrument=instrument,
            product_type=row.get("productType") or "INTRADAY",
            side=side,
            quantity=abs(net_qty),
            avg_price=row.get("avgPrice") or row.get("avg_price") or 0,
            current_price=row.get("ltp") or 0,
            unrealized_pnl=row.get("pl") or row.get("unrealized_profit") or 0,
            broker_position_id=row.get("id") or "",
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
        
        if broker_side in (1, '1', 'BUY', 'buy'):
            return Side.BUY
        elif broker_side in (-1, '-1', 'SELL', 'sell'):
            return Side.SELL
        else:
            logger.warning(f"Unknown broker side value: {broker_side}, defaulting to BUY")
            return Side.BUY
