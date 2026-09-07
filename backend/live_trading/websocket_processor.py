"""
Live WebSocket State Processor
Processes WebSocket updates and maintains state consistency for live trading.
Replaces DB polling for live trading with real-time WebSocket updates.
"""

import logging
import threading
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction

from brokers.websocket.factory import BrokerWebSocketFactory
from core.unified_state_manager import UnifiedStateManager
from core.cache_api import cache_api

logger = logging.getLogger(__name__)


class LiveWebSocketProcessor:
    """
    Processes WebSocket updates and maintains state consistency.
    Replaces DB polling for live trading.
    CRITICAL: Only creates positions/trades on WebSocket confirmation.
    """
    
    # Fyers order status codes
    STATUS_CANCELLED = 1
    STATUS_FILLED = 2
    STATUS_TRANSIT = 4
    STATUS_REJECTED = 5
    STATUS_PENDING = 6
    
    def __init__(self, credential):
        """
        Initialize live WebSocket processor.
        
        Args:
            credential: BrokerCredential instance
        """
        self.credential = credential
        self.websocket = None
        self.state_manager = UnifiedStateManager("live")
        self.sync_lock = threading.Lock()
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
    def start(self) -> None:
        """
        Start WebSocket processing.
        
        Creates WebSocket connection, registers callbacks, and starts listening.
        """
        try:
            # Create WebSocket instance
            self.websocket = BrokerWebSocketFactory.create(self.credential)
            
            # Register state update callbacks
            self.websocket.on_order_update(self._handle_order_update)
            self.websocket.on_trade_update(self._handle_trade_update)
            self.websocket.on_position_update(self._handle_position_update)
            self.websocket.on_general_message(self._handle_general_message)
            
            # Connect and subscribe
            self.websocket.connect()
            self.websocket.subscribe(['orders', 'trades', 'positions'])
            
            self.is_running = True
            self.reconnect_attempts = 0
            logger.info(f"Live WebSocket processor started for credential {self.credential.id}")
            
        except Exception as e:
            logger.exception(f"Failed to start live WebSocket processor: {e}")
            raise
    
    def stop(self) -> None:
        """Stop WebSocket processing."""
        try:
            if self.websocket:
                self.websocket.disconnect()
            self.is_running = False
            logger.info(f"Live WebSocket processor stopped for credential {self.credential.id}")
        except Exception as e:
            logger.exception(f"Error stopping live WebSocket processor: {e}")
    
    def _handle_order_update(self, order_data: Dict[str, Any]) -> None:
        """
        Process order update with state consistency.
        
        Args:
            order_data: Normalized order data from WebSocket
        """
        with self.sync_lock:
            try:
                from live_trading.models import LiveOrder
                existing_order = LiveOrder.objects.filter(
                    broker_order_id=order_data.get("broker_order_id")
                ).only("filled_quantity").first()
                previous_filled_quantity = int(existing_order.filled_quantity or 0) if existing_order else 0

                # Update database
                self._sync_order_to_db(order_data)
                
                # Update unified cache (replaces old cache systems)
                order_dict = {
                    'id': order_data.get('id'),
                    'broker_order_id': order_data.get('broker_order_id'),
                    'exchange_order_id': order_data.get('exchange_order_id'),
                    'instrument_id': order_data.get('instrument_id'),
                    'symbol': order_data.get('symbol'),
                    'side': order_data.get('side'),
                    'quantity': order_data.get('quantity'),
                    'filled_quantity': order_data.get('filled_quantity'),
                    'pending_quantity': order_data.get('pending_quantity'),
                    'status': self._map_fyers_status_to_internal(order_data.get('status')),
                    'avg_fill_price': str(order_data.get('avg_fill_price', 0)),
                    'session_id': order_data.get('session_id'),
                }
                if order_dict['session_id']:
                    cache_api.update_order("live", str(order_dict['session_id']), order_dict)
                
                # CRITICAL: Only create position on FILLED status from WebSocket
                if order_data["status"] == self.STATUS_FILLED:
                    fill_delta = max(
                        int(order_data.get("filled_quantity") or 0) - previous_filled_quantity,
                        0,
                    )
                    if fill_delta > 0:
                        fill_data = dict(order_data)
                        fill_data["filled_quantity"] = fill_delta
                        self._apply_fill_to_position_from_websocket(fill_data)
                
                logger.debug(f"Processed order update: {order_data.get('broker_order_id')}")
                
            except Exception as e:
                logger.exception(f"Error handling order update: {e}")
    
    def _handle_trade_update(self, trade_data: Dict[str, Any]) -> None:
        """
        Process trade update without creating a second local trade.

        Position and realized-trade persistence is driven by the order fill
        delta path. Fyers can emit both order and trade events for one fill;
        creating a trade from both events would duplicate realized P&L.
        
        Args:
            trade_data: Normalized trade data from WebSocket
        """
        with self.sync_lock:
            try:
                logger.debug(
                    "Received broker trade update %s for order %s; order fill path is authoritative",
                    trade_data.get("trade_number"),
                    trade_data.get("order_number"),
                )
                
            except Exception as e:
                logger.exception(f"Error handling trade update: {e}")
    
    def _handle_position_update(self, position_data: Dict[str, Any]) -> None:
        """
        Process position update - sync LivePosition with broker state.
        
        Args:
            position_data: Normalized position data from WebSocket
        """
        with self.sync_lock:
            try:
                self._sync_position_to_db(position_data)
                
                # Update unified cache (replaces old cache systems)
                position_dict = {
                    'id': position_data.get('id'),
                    'instrument_id': position_data.get('instrument_id'),
                    'symbol': position_data.get('symbol'),
                    'side': position_data.get('side'),
                    'quantity': position_data.get('quantity'),
                    'avg_price': str(position_data.get('avg_price', 0)),
                    'current_price': str(position_data.get('current_price', 0)),
                    'unrealized_pnl': str(position_data.get('unrealized_pnl', 0)),
                    'session_id': position_data.get('session_id'),
                }
                if position_dict['session_id']:
                    cache_api.update_position("live", str(position_dict['session_id']), position_dict)
                
                logger.debug(f"Processed position update: {position_data.get('broker_position_id')}")
                
            except Exception as e:
                logger.exception(f"Error handling position update: {e}")
    
    def _handle_general_message(self, message: Dict[str, Any]) -> None:
        """
        Process general messages (login, eDIS, price alerts).
        
        Args:
            message: General message from WebSocket
        """
        logger.debug(f"Received general message: {message}")
    
    def _sync_order_to_db(self, order_data: Dict[str, Any]) -> None:
        """
        Sync order to database with conflict resolution.
        
        Args:
            order_data: Normalized order data from WebSocket
        """
        from live_trading.models import LiveOrder
        from common.enums import OrderStatus
        
        broker_order_id = order_data.get("broker_order_id")
        if not broker_order_id:
            logger.warning("Order data missing broker_order_id")
            return
        
        try:
            order = LiveOrder.objects.select_for_update().get(broker_order_id=broker_order_id)
            
            # Update existing order
            order.status = self._map_fyers_status_to_internal(order_data["status"])
            order.filled_quantity = order_data["filled_quantity"]
            order.pending_quantity = order_data["pending_quantity"]
            order.avg_fill_price = order_data["avg_fill_price"] if order_data["avg_fill_price"] > 0 else order.avg_fill_price
            order.exchange_order_id = order_data["exchange_order_id"]
            
            # Update reconciliation status
            order.reconciliation_status = "MATCHED"
            order.reconciliation_attempts += 1
            order.last_reconciliation = timezone.now()
            
            order.save(update_fields=[
                "status", "filled_quantity", "pending_quantity",
                "avg_fill_price", "exchange_order_id",
                "reconciliation_status", "reconciliation_attempts", "last_reconciliation", "updated_at"
            ])
            
            logger.info(f"Synced order {broker_order_id} to status {order.status}")
            
        except LiveOrder.DoesNotExist:
            # New order from broker (not placed by us)
            logger.warning(f"Order {broker_order_id} not found in our DB, might be external order")
            self._create_external_order(order_data)
    
    def _create_external_order(self, order_data: Dict[str, Any]) -> None:
        """
        Create external order not placed by our system.
        
        Args:
            order_data: Normalized order data from WebSocket
        """
        from live_trading.models import LiveOrder, TradingSession
        from common.enums import OrderStatus, Side
        
        # Try to find a session for this credential
        session = TradingSession.objects.filter(
            broker_credential=self.credential,
            status__in=["RUNNING", "PAUSED"]
        ).first()
        
        if not session:
            logger.warning(f"No active session found for credential {self.credential.id}, skipping external order")
            return
        
        # Resolve instrument
        instrument = self._resolve_instrument(order_data.get("symbol"))
        if not instrument:
            logger.warning(f"Could not resolve instrument for symbol {order_data.get('symbol')}")
            return
        
        # Create external order record
        LiveOrder.objects.create(
            user=session.user,
            strategy=session.strategy,
            session=session,
            allocation=session.allocation,
            broker_credential=self.credential,
            instrument=instrument,
            order_type="MARKET",
            product_type=order_data.get("product_type", "INTRADAY"),
            side=self._map_fyers_side_to_internal(order_data["side"]),
            price=order_data.get("limit_price", 0),
            quantity=order_data["quantity"],
            broker_order_id=order_data["broker_order_id"],
            exchange_order_id=order_data["exchange_order_id"],
            status=self._map_fyers_status_to_internal(order_data["status"]),
            filled_quantity=order_data["filled_quantity"],
            pending_quantity=order_data["pending_quantity"],
            avg_fill_price=order_data["avg_fill_price"],
            reconciliation_status="MATCHED",
            last_reconciliation=timezone.now()
        )
        
        logger.info(f"Created external order {order_data['broker_order_id']}")
    
    def _create_trade_from_websocket(self, trade_data: Dict[str, Any]) -> None:
        """
        Create LiveTrade record based on WebSocket trade data.
        
        In professional trading systems, each fill from the broker should create a trade record.
        For Fyers, trades come via WebSocket with unique trade_number.
        
        Args:
            trade_data: Normalized trade data from WebSocket
        """
        from live_trading.models import LiveTrade, LiveOrder, LivePosition
        from common.enums import Side
        from decimal import Decimal
        
        broker_order_id = trade_data.get("order_number")
        if not broker_order_id:
            logger.warning("Trade data missing order_number")
            return
        
        # Find the associated order
        try:
            order = LiveOrder.objects.get(broker_order_id=broker_order_id)
        except LiveOrder.DoesNotExist:
            logger.warning(f"Order {broker_order_id} not found for trade {trade_data.get('trade_number')}")
            return
        
        # Resolve instrument
        instrument = self._resolve_instrument(trade_data.get("symbol"))
        if not instrument:
            logger.warning(f"Could not resolve instrument for symbol {trade_data.get('symbol')}")
            return
        
        # Check if this trade already exists (prevent duplicates)
        trade_number = trade_data.get("trade_number")
        if LiveTrade.objects.filter(
            broker_credential=self.credential,
            instrument=instrument,
            exit_order=order
        ).exists():
            logger.debug(f"Trade {trade_number} already exists for order {broker_order_id}")
            return
        
        # For MARKET orders, fills are typically immediate and full
        # Create trade record for the fill
        try:
            # Check if this trade closed a position (opposite side)
            opposite_side = Side.SELL if order.side == Side.BUY else Side.BUY
            opposite_position = LivePosition.objects.filter(
                allocation=order.allocation,
                instrument=instrument,
                side=opposite_side,
                quantity__gt=0
            ).first()
            
            if opposite_position:
                # This trade closed a position - create complete trade record
                closed_qty = min(opposite_position.quantity, trade_data["quantity"])
                pnl = (
                    (trade_data["trade_price"] - opposite_position.avg_price) * closed_qty
                    if opposite_position.side == Side.BUY
                    else (opposite_position.avg_price - trade_data["trade_price"]) * closed_qty
                )
                
                LiveTrade.objects.create(
                    user=order.user,
                    strategy=opposite_position.strategy,
                    allocation=opposite_position.allocation,
                    broker_credential=order.broker_credential,
                    instrument=instrument,
                    side=opposite_position.side,
                    quantity=closed_qty,
                    entry_price=opposite_position.avg_price,
                    entry_time=opposite_position.opened_at,
                    exit_price=trade_data["trade_price"],
                    exit_time=timezone.now(),
                    exit_order=order,
                    exit_reason="WebSocket trade update",
                    gross_pnl=pnl,
                    realized_pnl=pnl,
                    holding_duration_seconds=int((timezone.now() - opposite_position.opened_at).total_seconds()),
                )
                
                logger.info(f"Created trade {trade_number} for closed position (qty: {closed_qty})")
                
            else:
                # This trade added to an existing position - log for analytics
                logger.info(f"Trade {trade_number} added to position (qty: {trade_data['quantity']})")
                
        except Exception as e:
            logger.exception(f"Error creating trade from WebSocket: {e}")
    
    def _sync_position_to_db(self, position_data: Dict[str, Any]) -> None:
        """
        Sync position to database with broker state.
        
        Args:
            position_data: Normalized position data from WebSocket
        """
        from live_trading.models import LivePosition
        from common.enums import Side
        
        instrument = self._resolve_instrument(position_data.get("symbol"))
        if not instrument:
            logger.warning(f"Could not resolve instrument for symbol {position_data.get('symbol')}")
            return
        
        side = self._map_fyers_side_to_internal(position_data["side"])
        
        try:
            position = LivePosition.objects.select_for_update().get(
                broker_credential=self.credential,
                instrument=instrument,
                side=side
            )
            
            # Update existing position
            position.quantity = position_data["quantity"]
            position.avg_price = position_data["avg_price"]
            position.current_price = position_data["current_price"]
            position.unrealized_pnl = position_data["unrealized_pnl"]
            position.broker_position_id = position_data["broker_position_id"]
            position.sync_status = "SYNCED"
            position.last_sync_attempt = timezone.now()
            position.last_broker_sync = timezone.now()
            position.sync_error = ""
            
            position.save(update_fields=[
                "quantity", "avg_price", "current_price", "unrealized_pnl",
                "broker_position_id", "sync_status", "last_sync_attempt",
                "last_broker_sync", "sync_error", "updated_at"
            ])
            
            logger.info(f"Synced position {position.id} with broker state")
            
        except LivePosition.DoesNotExist:
            # Position in broker but not in our DB - could be external position
            logger.warning(f"Position not found in DB for {instrument.sym_ticker} {side}, might be external")
    
    def _apply_fill_to_position_from_websocket(self, order_data: Dict[str, Any]) -> None:
        """
        Apply fill to position based on WebSocket confirmation.
        CRITICAL: This is where position/trade creation happens for live trading.
        
        Args:
            order_data: Normalized order data from WebSocket
        """
        from live_trading.models import LiveOrder, LivePosition
        from live_trading.services import LiveExecutionService
        from common.enums import Side, OrderStatus
        
        broker_order_id = order_data.get("broker_order_id")
        if not broker_order_id:
            return
        
        try:
            order = LiveOrder.objects.select_for_update().get(broker_order_id=broker_order_id)
            
            filled_quantity = order_data["filled_quantity"]
            fill_price = order_data["avg_fill_price"]
            
            if filled_quantity > 0 and fill_price > 0:
                # Fetch strategy config for correct protection levels
                strategy_config = None
                if order.allocation and order.allocation.deployed_version:
                    strategy_config = order.allocation.deployed_version.config_snapshot
                else:
                    logger.error("No deployed version found for allocation")
                    raise ValueError("Strategy must have a deployed version for execution")
                
                # Call the existing position application logic
                # This will create/update positions and trades
                LiveExecutionService._apply_fill_to_position(
                    order,
                    filled_quantity,
                    fill_price,
                    strategy_config  # Pass strategy config for correct protection levels
                )
                
                # Update position sync status
                if order.allocation:
                    LivePosition.objects.filter(
                        allocation=order.allocation,
                        instrument=order.instrument,
                        side=order.side
                    ).update(
                        sync_status="SYNCED",
                        last_sync_attempt=timezone.now(),
                        last_broker_sync=timezone.now()
                    )
                
                # Update unified cache with position changes
                # The positions will be reloaded from DB after the fill application
                if order.allocation and order.allocation.session_id:
                    # Reload positions from DB and update cache
                    from live_trading.models import LivePosition
                    positions = LivePosition.objects.filter(
                        allocation=order.allocation,
                        quantity__gt=0
                    ).select_related('instrument')
                    
                    for position in positions:
                        position_dict = {
                            'id': str(position.id),
                            'instrument_id': position.instrument_id,
                            'symbol': position.instrument.sym_ticker if position.instrument else '',
                            'side': position.side,
                            'quantity': position.quantity,
                            'avg_price': str(position.avg_price),
                            'current_price': str(position.current_price),
                            'unrealized_pnl': str(position.unrealized_pnl),
                            'session_id': str(order.allocation.session_id),
                        }
                        cache_api.update_position("live", str(order.allocation.session_id), position_dict)
                
                logger.info(f"Applied fill from WebSocket to position for order {broker_order_id}")
                
        except LiveOrder.DoesNotExist:
            logger.warning(f"Order {broker_order_id} not found for fill application")
        except Exception as e:
            logger.exception(f"Error applying fill from WebSocket: {e}")
    
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
    
    def _map_fyers_status_to_internal(self, fyers_status: int) -> str:
        """
        Map Fyers status code to internal OrderStatus.
        
        Args:
            fyers_status: Fyers status code
            
        Returns:
            Internal OrderStatus string
        """
        from common.enums import OrderStatus
        
        status_map = {
            self.STATUS_CANCELLED: OrderStatus.CANCELLED,
            self.STATUS_FILLED: OrderStatus.FILLED,
            self.STATUS_TRANSIT: OrderStatus.PLACED,
            self.STATUS_REJECTED: OrderStatus.REJECTED,
            self.STATUS_PENDING: OrderStatus.PENDING,
        }
        
        return status_map.get(fyers_status, OrderStatus.PENDING)
    
    def _map_fyers_side_to_internal(self, fyers_side: Any) -> str:
        """
        Map Fyers side value to internal Side.
        
        Args:
            fyers_side: Fyers side value (1 or -1)
            
        Returns:
            Internal Side string (BUY or SELL)
        """
        from common.enums import Side
        
        if fyers_side in (1, '1'):
            return Side.BUY
        elif fyers_side in (-1, '-1'):
            return Side.SELL
        else:
            logger.warning(f"Unknown Fyers side value: {fyers_side}, defaulting to BUY")
            return Side.BUY
