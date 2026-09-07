
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from brokers.models import BrokerCredential
from brokers.services import BrokerService
from common.enums import CapitalAllocationType, OrderStatus, OrderType, ProductType, Severity, Side, NotificationType
from marketdata.quote_store import QuoteStore
from notifications.services import NotificationService
from core.cache_api import cache_api
from core.cache_view import cache_view

from strategy_engine.runtime import StrategyRuntimeState
from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, LiveTrade, SlippageRecord, TradingSession

logger = logging.getLogger(__name__)

class LiveExecutionService:
    """Service to handle Live Trading Strategy execution - broker-agnostic."""

    ACTIVE_ORDER_STATUSES = {OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL}
    FILLED_ORDER_STATUSES = {OrderStatus.PARTIAL_FILL, OrderStatus.FILLED}
    TERMINAL_ORDER_STATUSES = {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED}

    @staticmethod
    def _publish_execution_event(action: str, session, scope: str = "live"):
        from django.core.cache import cache
        import json
        
        try:
            if hasattr(cache, 'client'):
                redis_client = cache.client.get_client()
            else:
                import redis
                from django.conf import settings
                redis_url = getattr(settings, 'CHANNEL_REDIS_URL', 'redis://localhost:6379/0')
                redis_client = redis.from_url(redis_url)
                
            from instruments.services import InstrumentResolver
            inst_ids = InstrumentResolver.execution_instrument_ids(session.strategy)
            payload = {
                "action": action,
                "scope": scope,
                "session_id": str(session.id),
                "strategy_id": str(session.strategy_id),
                "instrument_ids": inst_ids
            }
            redis_client.publish("execution_control", json.dumps(payload))
        except Exception as e:
            logger.error(f"Failed to publish execution event {action} for {session.id}: {e}")

    @staticmethod
    @transaction.atomic
    def update_allocation(allocation, allocation_amount=None, allocation_percentage=None):
        """Update live strategy allocation - matches paper trading allocation logic."""
        from common.enums import CapitalAllocationType
        
        if not allocation:
            raise ValueError("Allocation not found")

        funds = LiveExecutionService.sync_funds(allocation.broker_credential)
        broker_equity = BrokerService.to_decimal(
            funds.get("net_equity") or funds.get("cash_balance") or 0
        )
        
        if allocation_amount is not None:
            allocation.allocation_type = CapitalAllocationType.FIXED
            allocation.allocated_capital = Decimal(str(allocation_amount))
            allocation.allocated_percentage = Decimal("0")
        elif allocation_percentage is not None:
            allocation.allocation_type = CapitalAllocationType.PERCENTAGE
            allocation.allocated_percentage = Decimal(str(allocation_percentage))
            # Calculate allocated capital from broker equity
            allocation.allocated_capital = broker_equity * (Decimal(str(allocation_percentage)) / Decimal("100"))
        else:
            raise ValueError("Either allocation_amount or allocation_percentage must be provided")

        existing = list(
            LiveStrategyAllocation.objects.filter(user=allocation.user, broker_credential=allocation.broker_credential).exclude(strategy=allocation.strategy)
        )
        total_other = sum((Decimal(str(item.allocated_capital or 0)) for item in existing), Decimal("0"))
        if broker_equity > 0 and total_other + allocation.allocated_capital > broker_equity:
            raise ValueError(
                f"Live allocation exceeds broker equity. Requested={allocation.allocated_capital}, already allocated={total_other}, broker equity={broker_equity}"
            )

        allocation.broker_equity_reference = allocation.allocated_capital
        allocation.is_over_allocated = False
        allocation.breach_reason = ""
        allocation.save(update_fields=[
            "allocation_type", "allocated_capital", "allocated_percentage",
            "broker_equity_reference", "is_over_allocated", "breach_reason", "updated_at"
        ])
        
        NotificationService.notify(
            user=allocation.user,
            title="Live Allocation Updated",
            message=f"Allocation for '{allocation.strategy.name}' has been updated to {allocation.allocated_capital}.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.INFO,
            strategy=allocation.strategy,
            data={"allocation_id": str(allocation.id), "module": "live"}
        )
        
        return allocation
        
    
    @staticmethod
    def create_allocation(user, strategy, credential, allocation_amount=None, allocation_percentage=None, deployed_version=None):
        existing_allocation = LiveStrategyAllocation.objects.filter(
            user=user,
            strategy=strategy,
            broker_credential=credential,
        ).first()
        if existing_allocation:
            raise ValueError(
                "A live allocation already exists for this strategy and broker. "
                "Update the existing allocation instead."
            )

        # Use unified cache for funds state
        from core.cache_view import cache_view
        funds_data = cache_view.get_funds(credential)
        broker_equity = BrokerService.to_decimal(
            funds_data.get("net_equity") or funds_data.get("available_margin") or funds_data.get("cash_balance") or 0
        )

        allocation_type = CapitalAllocationType.FIXED
        allocated_capital = None
        allocated_percentage = None

        if allocation_percentage not in (None, "", 0, "0"):
            allocation_type = CapitalAllocationType.PERCENTAGE
            allocated_percentage = Decimal(str(allocation_percentage))
            if broker_equity <= 0:
                raise ValueError("Broker equity is unavailable, cannot create percentage allocation")
            allocated_capital = (allocated_percentage / Decimal("100")) * broker_equity
        elif allocation_amount not in (None, "", 0, "0"):
            allocation_type = CapitalAllocationType.FIXED
            allocated_capital = Decimal(str(allocation_amount))
            allocated_percentage = Decimal("0")
        else:
            raise ValueError("Live deployment requires a broker capital allocation amount or percentage")

        existing = list(
            LiveStrategyAllocation.objects.filter(user=user, broker_credential=credential).exclude(strategy=strategy)
        )
        total_other = sum((Decimal(str(item.allocated_capital or 0)) for item in existing), Decimal("0"))
        if broker_equity > 0 and total_other + allocated_capital > broker_equity:
            raise ValueError(
                f"Live allocation exceeds broker equity. Requested={allocated_capital}, already allocated={total_other}, broker equity={broker_equity}"
            )

        allocation = LiveStrategyAllocation.objects.create(
            user=user,
            strategy=strategy,
            broker_credential=credential,
            allocation_type=allocation_type,
            allocated_capital=allocated_capital,
            allocated_percentage=allocated_percentage or Decimal("0"),
            broker_equity_reference=broker_equity,
            deployed_version=deployed_version,
        )
        return allocation

    @staticmethod
    def _resolve_product_type(instrument):
        if getattr(instrument, 'instrument_type', '') in ('STOCK', 'INDEX'):
            return ProductType.CNC
        return ProductType.MARGIN

    
    @staticmethod
    @transaction.atomic
    def deploy_session(user, strategy, allocation, broker_credential):
    
        session, _ = TradingSession.objects.update_or_create(
            allocation=allocation,
            defaults={
                "user": user,
                "strategy": strategy,
                "broker_credential": broker_credential,
                "status": "RUNNING",
                "started_at": timezone.now(),
                "ended_at": None,
                "error_message": "",
            },
        )

        # Initialize risk metrics for live session
        from core.cache_api import cache_api
        cache_api.update_risk_metrics("live", str(session.id), {
            "daily_trades": 0,
            "daily_pnl": 0.0,
            "weekly_pnl": 0.0,
            "monthly_pnl": 0.0,
            "total_closed_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
        })

        # Initialize funds in unified cache for live trading
        funds_data = cache_view.get_funds(broker_credential.id)
        if not funds_data:
            # Sync funds if not in cache
            LiveExecutionService.sync_funds(broker_credential)
            funds_data = cache_view.get_funds(broker_credential.id)
        
        # Update funds in unified cache
        cache_api.update_funds(broker_credential.id, funds_data)

        # Rebuild runtime state from database for session recovery
        LiveExecutionService.rebuild_runtime_state_from_db(str(session.id))

        LiveExecutionService._publish_execution_event("SESSION_START", session, "live")

        NotificationService.notify(
            user=user,
            title="Live Strategy Deployed",
            message=f"Strategy '{strategy.name}' has been deployed to live trading.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.INFO,
            strategy=strategy,
            data={"session_id": str(session.id), "module": "live"}
        )
        return session

    @staticmethod
    @transaction.atomic
    def pause_session(session):
        session.status = "PAUSED"
        session.error_message = ""
        session.save(update_fields=["status", "error_message", "updated_at"])

        NotificationService.notify(
            user=session.user,
            title="Live Strategy Paused",
            message=f"Strategy '{session.strategy.name}' has been paused.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.WARNING,
            strategy=session.strategy,
            data={"session_id": str(session.id), "module": "live"}
        )
        LiveExecutionService._publish_execution_event("SESSION_PAUSE", session, "live")
        return session


    @staticmethod
    @transaction.atomic
    def stop_session(session, close_positions=False):
        if close_positions:
            position_query = LivePosition.objects.filter(allocation=session.allocation)
            for position in position_query:
                LiveExecutionService._close_position(
                    session=session,
                    position=position
                )
        # Check if any positions failed to close
        has_open_positions = False
        if close_positions:
            has_open_positions = LivePosition.objects.filter(
                allocation=session.allocation,
                quantity__gt=0
            ).exists()
            
        if has_open_positions:
            session.status = "STOPPING"
            session.error_message = "Positions failed to close during square-off. Manual operator review required."
            logger.warning(f"Session {session.id} marked STOPPING due to orphaned open positions.")
        else:
            session.status = "STOPPED"
            session.ended_at = timezone.now()
            session.error_message = ""
            
        session.save(update_fields=["status", "ended_at", "error_message", "updated_at"])

        LiveExecutionService._publish_execution_event("SESSION_STOP", session, "live")
        NotificationService.notify(
            user=session.user,
            title="Live Session Stopped",
            message=f"Live session for '{session.strategy.name}' has been completely stopped" + (" and positions squared off." if close_positions else "."),
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.CRITICAL,
            strategy=session.strategy,
            data={"session_id": str(session.id), "module": "live"}
        )
        return session

    @staticmethod
    @transaction.atomic
    def resume_session(session):
        BrokerService.ensure_session(session.broker_credential)
        session.status = "RUNNING"
        session.error_message = ""
        session.save(update_fields=["status", "error_message", "updated_at"])
        
        NotificationService.notify(
            user=session.user,
            title="Live Strategy Resumed",
            message=f"Strategy '{session.strategy.name}' has been resumed.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.INFO,
            strategy=session.strategy,
            data={"session_id": str(session.id), "module": "live"}
        )
        LiveExecutionService._publish_execution_event("SESSION_START", session, "live")
        return session
    
    def _close_position(self, session, position):
        """Close a live position by placing an opposite market order."""
        if not position or position.quantity <= 0:
            return
        close_side = Side.SELL if position.side == Side.BUY else Side.BUY
       
        LiveExecutionService._execute_market_order(
            session,
            session.allocation,
            position.instrument,
            close_side,
            position.quantity,
            None,
            0,
        )

    @staticmethod
    def resolve_market_price(instrument, fallback_price=None):
        """Resolve market price for instrument - matches paper trading naming."""
        quote = QuoteStore.get_latest(instrument.sym_ticker)
        if quote and quote.get("price") is not None:
            return Decimal(str(quote["price"]))
        return Decimal(str(fallback_price or instrument.previous_close or 0))


    @staticmethod
    def _validate_auto_disable(session, raise_on_trigger=True):
        """Validate auto-disable rules - matches paper trading naming."""
        from risk_management.auto_disable import AutoDisableGate
        from core.cache_view import cache_view
        from django.db.models import Count, Sum

        # Get current risk metrics from unified cache
        stats = cache_view.get_risk_metrics("live", session.id)
        if not stats or not stats.get("daily_trades"):
            # If cache miss, initialize with database query
            from live_trading.models import LiveTrade
            from django.utils import timezone
            
            allocation = session.allocation
            if allocation:
                trades = LiveTrade.objects.filter(allocation=allocation).aggregate(
                    total_trades=Count('id'),
                    total_pnl=Sum('realized_pnl')
                )
                stats = {
                    "daily_trades": trades['total_trades'] or 0,
                    "daily_pnl": float(trades['total_pnl'] or 0),
                    "win_rate": 0.0,
                    "consecutive_losses": 0,
                    "consecutive_wins": 0,
                }
                cache_api.update_risk_metrics("live", session.id, stats)
        
        allocation = session.allocation
        capital = allocation.allocated_capital if allocation else Decimal("0")
        match = AutoDisableGate.evaluate(session, stats, capital)
        if match:
            LiveExecutionService._publish_execution_event("SESSION_PAUSE", session, "live")
        if match and raise_on_trigger:
            raise ValueError(f"Strategy auto-disable triggered: {match.get('message', 'Strategy auto-disable triggered')}")
        return bool(match)


    @staticmethod
    def place_order(session, instrument, side, quantity, order_type=OrderType.MARKET, price=None):
        if str(order_type) != str(OrderType.MARKET):
            raise ValueError("Only MARKET orders are supported for live execution")
        try:
            return LiveExecutionService._place_order_internal(session, instrument, side, quantity, price)
        except Exception as e:
            logger.exception("Live order placement failed")
            NotificationService.notify(
                user=session.user,
                title="Live Order Placement Failed",
                message=f"Failed to place order for {instrument.symbol}: {str(e)}",
                notification_type=NotificationType.STRATEGY_ERROR,
                severity=Severity.CRITICAL,
                strategy=session.strategy,
                data={"symbol": instrument.symbol, "module": "live", "error": str(e)}
            )
            raise e

    @staticmethod
    def _place_order_internal(session, instrument, side, quantity, price=None):
        BrokerService.ensure_session(session.broker_credential)
        
        # Ensure WebSocket processor is running for this credential
        from live_trading.websocket_manager import _websocket_manager
        _websocket_manager.start_processor(session.broker_credential_id)
        
        # Use unified cache for funds state
        from core.cache_view import cache_view
        funds_data = cache_view.get_funds(session.broker_credential_id)
        if not funds_data:
            LiveExecutionService.sync_funds(session.broker_credential)
        
        settings = getattr(session.broker_credential, 'order_settings', None)
        order_timeout = settings.order_timeout_seconds if settings else 30
        expected_price = LiveExecutionService.resolve_market_price(instrument, fallback_price=price)

        LiveExecutionService._validate_auto_disable(session)

        order = LiveExecutionService._execute_market_order(
            session,
            session.allocation,
            instrument,
            side,
            quantity,
            expected_price,
            order_timeout,
        )
        return order

    @staticmethod
    def _execute_market_order(session, allocation, instrument, side, quantity, expected_price, order_timeout):
        """Submit live market order to broker - optimized for MARKET orders."""
        strategy_config = None
        if allocation and allocation.deployed_version:
            strategy_config = allocation.deployed_version.config_snapshot
        else:
            logger.error("No deployed version found for allocation")
            raise ValueError("Strategy must have a deployed version for execution")

        # Create order record
        order = LiveOrder.objects.create(
            user=session.user,
            strategy=session.strategy,
            session=session,
            allocation=allocation,
            broker_credential=session.broker_credential,
            instrument=instrument,
            order_type=OrderType.MARKET,
            product_type=LiveExecutionService._resolve_product_type(instrument),
            side=side,
            price=expected_price,
            quantity=int(quantity),
            status=OrderStatus.PENDING,
        )
        ExecutionLog.objects.create(
            order=order,
            event_type="CREATED",
            message="Order record created, preparing for broker submission"
        )

        # Submit to broker
        import time
        started_at = time.perf_counter()
        
        try:
            broker_result = BrokerService.place_order(
                session.broker_credential,
                {
                    "instrument": instrument.sym_ticker,
                    "side": side,
                    "quantity": int(quantity),
                    "order_type": OrderType.MARKET,
                    "product_type": order.product_type,
                    "validity": "DAY",
                    "tag": f"QN_{order.id}",
                },
            )
        except Exception as e:
            logger.exception("Broker order submission failed for order %s", order.id)
            order.status = OrderStatus.REJECTED
            order.rejection_reason = str(e)
            order.save(update_fields=["status", "rejection_reason", "updated_at"])
            ExecutionLog.objects.create(order=order, event_type="REJECTED", message=str(e))
            return order

        latency_ms = int((time.perf_counter() - started_at) * 1000)

        # CRITICAL: Only update broker IDs from REST response, keep status as PENDING
        # Position/trade creation will happen via WebSocket confirmation
        order.broker_order_id = broker_result.get("broker_order_id", "")
        order.exchange_order_id = broker_result.get("exchange_order_id", "")
        # Keep status as PENDING - WebSocket will update to FILLED when confirmed
        # order.status = broker_status  # REMOVED: Don't update status from REST
        # order.filled_quantity = filled_quantity  # REMOVED: Don't update from REST
        # order.pending_quantity = max(int(quantity) - filled_quantity, 0)  # REMOVED
        # order.avg_fill_price = fill_price if filled_quantity else None  # REMOVED
        order.rejection_reason = broker_result.get("message") or ""
        # order.executed_at = timezone.now() if broker_status in LiveExecutionService.FILLED_ORDER_STATUSES else None  # REMOVED
        order.save(update_fields=["broker_order_id", "exchange_order_id", "rejection_reason", "updated_at"])

        ExecutionLog.objects.create(
            order=order,
            event_type="PLACED",
            message=f"Broker order {order.broker_order_id or 'submitted'} placed via REST. Waiting for WebSocket confirmation.",
            latency_ms=max(int(latency_ms or 0), 0)
        )

        # CRITICAL: REMOVED - Position/trade creation moved to WebSocket
        # if broker_status in LiveExecutionService.FILLED_ORDER_STATUSES and filled_quantity > 0:
        #     LiveExecutionService._apply_fill_to_position(order, filled_quantity, fill_price, strategy_config)
        return order

    @staticmethod
    def _get_base_instrument(strategy, execution_instrument):
        watches = strategy.watchlist_instruments.all()
        for w in watches:
            if w.instrument_id == execution_instrument.id:
                return w.instrument
        for w in watches:
            routes = w.execution_routes.all()
            for r in routes:
                if r.target_instrument_id == execution_instrument.id:
                    return w.instrument
            if execution_instrument.instrument_type in ['OPTION', 'FUTURE']:
                if execution_instrument.underlying_symbol == w.instrument.symbol:
                    return w.instrument
                for r in routes:
                    if r.target_underlying_instrument and execution_instrument.underlying_symbol == r.target_underlying_instrument.symbol:
                        return w.instrument
        return execution_instrument

    @staticmethod
    @transaction.atomic
    def _apply_fill_to_position(order, filled_quantity=None, fill_price=None, strategy_config=None):
        opposite_side = Side.SELL if order.side == Side.BUY else Side.BUY
        opposite_position = LivePosition.objects.select_for_update().filter(
            allocation=order.allocation,
            instrument=order.instrument,
            side=opposite_side,
            quantity__gt=0,
        ).first()
        position = None

        fill_price = Decimal(str(fill_price or order.avg_fill_price or order.price or 0))
        remaining = int(filled_quantity if filled_quantity is not None else order.filled_quantity or 0)

        if opposite_position:
            closed_qty = min(opposite_position.quantity, remaining)
            pnl = (
                (fill_price - opposite_position.avg_price) * closed_qty
                if opposite_position.side == Side.BUY
                else (opposite_position.avg_price - fill_price) * closed_qty
            )
            LiveTrade.objects.create(
                user=order.user,
                strategy=opposite_position.strategy,
                allocation=opposite_position.allocation,
                broker_credential=order.broker_credential,
                instrument=order.instrument,
                side=opposite_position.side,
                quantity=closed_qty,
                entry_price=opposite_position.avg_price,
                entry_time=opposite_position.opened_at,
                exit_price=fill_price,
                exit_time=timezone.now(),
                realized_pnl=pnl,
            )
            opposite_position.quantity -= closed_qty
            opposite_position.current_price = fill_price
            opposite_position.unrealized_pnl = Decimal("0")

            # Update unified cache risk metrics with trade result
            from core.cache_view import cache_view
            from core.cache_api import cache_api
            if order.session_id:
                current = cache_view.get_risk_metrics("live", order.session_id)
                pnl = float(pnl)
                current["daily_trades"] = int(current.get("daily_trades", 0) or 0) + 1
                current["daily_pnl"] = float(current.get("daily_pnl", 0.0) or 0.0) + pnl
                current["weekly_pnl"] = float(current.get("weekly_pnl", 0.0) or 0.0) + pnl
                current["monthly_pnl"] = float(current.get("monthly_pnl", 0.0) or 0.0) + pnl
                current["total_closed_trades"] = int(current.get("total_closed_trades", 0) or 0) + 1
                current["closed_trades"] = current["total_closed_trades"]
                
                if pnl < 0:
                    current["consecutive_losses"] = current.get("consecutive_losses", 0) + 1
                    current["consecutive_wins"] = 0
                    current["losing_trades"] = int(current.get("losing_trades", 0) or 0) + 1
                elif pnl > 0:
                    current["consecutive_wins"] = current.get("consecutive_wins", 0) + 1
                    current["consecutive_losses"] = 0
                    current["winning_trades"] = int(current.get("winning_trades", 0) or 0) + 1
                
                total_closed = int(current.get("total_closed_trades", 0) or 0)
                wins = int(current.get("winning_trades", 0) or 0)
                current["win_rate"] = (wins / total_closed) * 100 if total_closed else 0.0
                
                cache_api.update_risk_metrics("live", order.session_id, current)

            if opposite_position.quantity > 0:
                opposite_position.save(update_fields=["quantity", "current_price", "unrealized_pnl", "updated_at"])
                if opposite_position.strategy_id:
                    base_inst = LiveExecutionService._get_base_instrument(opposite_position.strategy, opposite_position.instrument)
                    StrategyRuntimeState.mark_open(
                        "live",
                        order.session_id or 0,
                        base_inst.id,
                        side=opposite_position.side,
                        quantity=opposite_position.quantity,
                        avg_price=opposite_position.avg_price,
                        config=strategy_config,
                        opened_at=opposite_position.opened_at,
                        execution_instrument_id=opposite_position.instrument_id,
                    )
            else:
                if opposite_position.strategy_id:
                    StrategyRuntimeState.mark_closed(
                        "live",
                        order.session_id or 0,
                        LiveExecutionService._get_base_instrument(order.strategy, opposite_position.instrument).id,
                    )
                if order.session_id:
                    cache_api.remove_position(
                        "live", str(order.session_id), str(opposite_position.id)
                    )
                opposite_position.delete()
            remaining -= closed_qty

        if remaining > 0:
            with transaction.atomic():
                position = LivePosition.objects.select_for_update().filter(
                    allocation=order.allocation,
                    instrument=order.instrument,
                    side=order.side,
                ).first()

                if not position:
                    position = LivePosition.objects.create(
                        user=order.user,
                        strategy=order.strategy,
                        broker_credential=order.broker_credential,
                        instrument=order.instrument,
                        side=order.side,
                        allocation=order.allocation,
                        product_type=order.product_type,
                        quantity=remaining,
                        avg_price=fill_price,
                        current_price=fill_price,
                        last_broker_sync=timezone.now(),
                    )
                else:
                    total_qty = position.quantity + remaining
                    position.avg_price = ((position.avg_price * position.quantity) + (fill_price * remaining)) / total_qty
                    position.quantity = total_qty
                    position.current_price = fill_price
                    position.allocation = order.allocation
                    position.last_broker_sync = timezone.now()
                    position.save(update_fields=["allocation", "avg_price", "quantity", "current_price", "last_broker_sync", "updated_at"])

                trade_state = {}
                trade_strategy_id = order.strategy.id if order.strategy else position.strategy_id
                if trade_strategy_id:
                    base_inst = LiveExecutionService._get_base_instrument(position.strategy, position.instrument)
                    StrategyRuntimeState.mark_open(
                        "live",
                        order.session_id or 0,
                        base_inst.id,
                        side=position.side,
                        quantity=position.quantity,
                        avg_price=position.avg_price,
                        config=strategy_config,
                        opened_at=position.opened_at,
                        execution_instrument_id=position.instrument_id,
                    )

        # Update unified cache for live trading
        from core.cache_api import cache_api
        if order.session_id:
            # Update only the affected position in cache (no DB reload)
            if position and position.quantity > 0:
                cache_api.update_position("live", str(order.session_id), {
                    'id': str(position.id),
                    'instrument_id': position.instrument_id,
                    'symbol': position.instrument.sym_ticker if position.instrument else '',
                    'side': position.side,
                    'quantity': position.quantity,
                    'avg_price': str(position.avg_price),
                    'current_price': str(position.current_price),
                    'unrealized_pnl': str(position.unrealized_pnl),
                    'session_id': str(order.session_id),
                })


    @classmethod
    def run_zmq_subscriber(cls):
        """
        Runs continuously in a background process/thread, listening to the StrategyOrderRouter 
        ZeroMQ publisher for any 'LIVE' scope OrderRequests.
        """
        import zmq
        import json
        from strategy_engine.router import OrderRequest
        from live_trading.models import TradingSession
        from instruments.models import Instrument
        
        context = zmq.Context.instance()
        socket = context.socket(zmq.SUB)
        socket.bind("tcp://127.0.0.1:5555")
        socket.setsockopt_string(zmq.SUBSCRIBE, "LIVE")
        
        logger.info("LiveExecutionService ZMQ Subscriber listening for LIVE orders...")
        
        while True:
            req = None
            try:
                topic, message = socket.recv_multipart()
                data = json.loads(message.decode('utf-8'))
                req = OrderRequest(**data)
                
                # Rehydrate objects
                session = TradingSession.objects.select_related('broker_credential').get(id=req.session_id)
                instrument = Instrument.objects.get(id=req.instrument_id)
                
                cls.place_order(
                    session=session,
                    instrument=instrument,
                    side=req.side,
                    quantity=req.qty,
                    order_type=req.order_type,
                    price=req.target_price,
                )
                logger.info(f"ZMQ order placed: {req.side} {req.qty} {instrument.sym_ticker} reason={getattr(req, 'reason', 'N/A')}")
            except Exception as e:
                session_id = getattr(req, "session_id", "unknown")
                logger.error(f"ZMQ Subscriber Error for session {session_id}: {e}", exc_info=True)
                # Revert phase to prevent permanent state lock
                try:
                    if req is None:
                        continue
                    state = StrategyRuntimeState.trade_state("live", req.session_id, req.instrument_id)
                    if state.get("phase") in (StrategyRuntimeState.ENTRY_PENDING, StrategyRuntimeState.EXIT_PENDING):
                        revert_phase = StrategyRuntimeState.OPEN if state.get("quantity", 0) > 0 else StrategyRuntimeState.CLOSED
                        StrategyRuntimeState.update_trade_state("live", req.session_id, req.instrument_id, {"phase": revert_phase})
                        logger.info(f"Reverted phase to {revert_phase} for session {req.session_id} instrument {req.instrument_id}")
                except Exception:
                    logger.exception("Failed to revert trade phase after ZMQ error")

    @staticmethod
    def rebuild_runtime_state_from_db(session_id):
        """Initialize and recover runtime state from open live positions using centralized method."""
        from strategy_engine.runtime import StrategyRuntimeState
        return StrategyRuntimeState.rebuild_runtime_state_from_db("live", session_id)

        if recovered > 0:
            logger.info("Recovered %s missing runtime states from live DB positions.", recovered)


    @staticmethod
    def _resolve_instrument_from_broker_symbol(symbol):
        """Resolve broker symbol to Instrument model - needed for sync."""
        if not symbol:
            return None
        from instruments.models import Instrument
        instrument = Instrument.objects.filter(sym_ticker=symbol).first()
        if instrument:
            return instrument
        normalized = str(symbol).split(":")[-1]
        return (
            Instrument.objects.filter(symbol=normalized).first()
            or Instrument.objects.filter(symbol__iexact=normalized).first()
        )

    @staticmethod
    @transaction.atomic
    def _refresh_broker_allocation_health(credential):
        """Check if allocations exceed broker equity and update health flags for all allocations."""
        if not credential:
            return

        # Use unified cache for funds state
        from core.cache_view import cache_view
        funds_data = cache_view.get_funds(credential.id)
        broker_equity = BrokerService.to_decimal(
            funds_data.get("net_equity") or funds_data.get("cash_balance") or 0
        )

        # Get all allocations for this broker credential, ordered by creation time
        allocations = LiveStrategyAllocation.objects.filter(broker_credential=credential).order_by('created_at')
        
        cumulative_allocated = Decimal("0")
        
        for allocation in allocations:
            was_over_allocated = allocation.is_over_allocated
            allocation_capital = Decimal(str(allocation.allocated_capital or 0))
            
            # Check if this allocation pushes the cumulative total over broker equity
            if broker_equity > 0 and cumulative_allocated + allocation_capital > broker_equity:
                allocation.is_over_allocated = True
                allocation.breach_reason = (
                    f"Cumulative allocation ({cumulative_allocated + allocation_capital}) exceeds broker equity ({broker_equity}). "
                    f"This allocation: {allocation_capital}, previous allocations: {cumulative_allocated}"
                )
            else:
                allocation.is_over_allocated = False
                allocation.breach_reason = ""

            allocation.broker_equity_reference = broker_equity
            allocation.save(update_fields=["is_over_allocated", "breach_reason", "broker_equity_reference", "updated_at"])
            
            cumulative_allocated += allocation_capital

            # Send notification if newly over-allocated
            if allocation.is_over_allocated and not was_over_allocated:
                try:
                    NotificationService.notify(
                        user=allocation.user,
                        title="Live Allocation Over-allocated",
                        message=f"Allocation for '{allocation.strategy.name}' exceeds broker equity. {allocation.breach_reason}",
                        notification_type=NotificationType.RISK_ALERT,
                        severity=Severity.CRITICAL,
                        strategy=allocation.strategy,
                        data={
                            "allocation_id": str(allocation.id),
                            "broker_credential_id": str(credential.id),
                            "cumulative_allocated": str(cumulative_allocated),
                            "broker_equity": str(broker_equity),
                            "module": "live"
                        }
                    )
                except Exception:
                    logger.exception("Failed dispatching over-allocation notification for allocation %s", allocation.id)
        
    
    @staticmethod
    def sync_funds(credential):
        """Fetch fresh funds and cache - uses BrokerService abstraction."""
        funds_payload = BrokerService.get_funds(credential)
        snapshot = BrokerService.record_funds_snapshot(credential, funds_payload)
        payload = {
            "snapshot_id": snapshot.id,
            "cash_balance": str(snapshot.cash_balance),
            "available_margin": str(snapshot.available_margin),
            "used_margin": str(snapshot.used_margin),
            "collateral": str(snapshot.collateral),
            "withdrawable_balance": str(snapshot.withdrawable_balance),
            "net_equity": str(snapshot.net_equity),
            "realized_pnl": str(snapshot.realized_pnl),
            "unrealized_pnl": str(snapshot.unrealized_pnl),
            "snapshot_time": snapshot.snapshot_time.isoformat(),
        }
        # Update unified cache
        cache_api.update_funds(credential.id, payload)
        return payload

    
    @staticmethod
    def session_summary(user):
        """Simplified session summary - broker is source of truth for funds."""
        sessions = TradingSession.objects.filter(user=user).select_related("strategy", "broker_credential")
        positions = LivePosition.objects.filter(user=user)
        orders = LiveOrder.objects.filter(user=user)
        active_sessions = sessions.filter(status="RUNNING")
        open_orders = orders.filter(status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES)
        today_orders = orders.filter(placed_at__date=timezone.localdate())
        active_credentials = BrokerCredential.objects.filter(user=user, is_active=True)
        broker_summaries = []
        for credential in active_credentials:
            # Fetch fresh funds from broker
            funds_data = BrokerService.get_funds(credential)
            funds_payload = funds_data if isinstance(funds_data, dict) else {}
            
            allocation_rows = list(
                LiveStrategyAllocation.objects.filter(user=user, broker_credential=credential)
                .select_related("strategy")
            )
            session = credential.sessions.filter(is_valid=True, token_expiry__gt=timezone.now()).first()
            session_valid = session is not None

            is_over_allocated = any(row.is_over_allocated for row in allocation_rows)
            account_healthy = session_valid and not is_over_allocated

            broker_summaries.append(
                {
                    "broker_label": credential.label,
                    "is_healthy": account_healthy,
                    "broker_session_valid": session_valid,
                    "available_margin": str(BrokerService.to_decimal(funds_payload.get("available_margin"))),
                    "used_margin": str(BrokerService.to_decimal(funds_payload.get("used_margin"))),
                    "net_equity": str(BrokerService.to_decimal(funds_payload.get("net_equity"))),
                    "cash_balance": str(BrokerService.to_decimal(funds_payload.get("cash_balance"))),
                    "allocations": [
                        {
                            "id": row.id,
                            "strategy_id": row.strategy_id,
                            "allocated_capital": str(row.allocated_capital),
                            "broker_equity_reference": str(row.broker_equity_reference),
                            "is_over_allocated": row.is_over_allocated,
                            "breach_reason": row.breach_reason,
                        }
                        for row in allocation_rows
                    ],
                }
            )

        return {
            "running_sessions": active_sessions.count(),
            "paused_sessions": sessions.filter(status="PAUSED").count(),
            "error_sessions": sessions.filter(status="ERROR").count(),
            "open_positions": positions.count(),
            "open_orders": open_orders.count(),
            "today_orders": today_orders.count(),
            "today_fills": today_orders.filter(status__in=LiveExecutionService.FILLED_ORDER_STATUSES).count(),
            "unrealized_pnl": str(positions.aggregate(s=Sum("unrealized_pnl"))["s"] or Decimal("0")),
            "realized_pnl": str(
                LiveTrade.objects.filter(allocation__user=user).aggregate(s=Sum("realized_pnl"))["s"]
                or Decimal("0")
            ),
            "day_pnl": str(
                (positions.aggregate(s=Sum("unrealized_pnl"))["s"] or Decimal("0"))
                + (LiveTrade.objects.filter(allocation__user=user).aggregate(s=Sum("realized_pnl"))["s"] or Decimal("0"))
            ),
            "active_brokers": sessions.filter(broker_credential__isnull=False).values("broker_credential").distinct().count(),
            "broker_accounts": broker_summaries,
        }

    @staticmethod
    @transaction.atomic
    def stop_all_sessions(user, close_positions=False):
        stopped = []
        for session in TradingSession.objects.filter(user=user).exclude(status="STOPPED"):
            stopped.append(LiveExecutionService.stop_session(session, close_positions=close_positions))
        return stopped
