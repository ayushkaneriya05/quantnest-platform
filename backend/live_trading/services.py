
import logging
import time
import uuid
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from brokers.models import BrokerCredential, BrokerFundsSnapshot, BrokerSession
from brokers.services import BrokerService
from common.enums import CapitalAllocationType, OrderStatus, OrderType, ProductType, Severity, Side, NotificationType
from marketdata.quote_store import QuoteStore
from notifications.services import NotificationService
from core.cache_api import cache_api

from strategy_engine.runtime import StrategyRuntimeState
from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, LiveTrade, SlippageRecord, TradingSession

logger = logging.getLogger(__name__)


def _publish_cache_after_commit(method_name, *args, **kwargs):
    callback = getattr(cache_api, method_name)
    transaction.on_commit(lambda: callback(*args, **kwargs))

class LiveExecutionService:
    """Service to handle Live Trading Strategy execution - broker-agnostic."""

    ACTIVE_ORDER_STATUSES = {OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL, "UNKNOWN"}
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
            inst_ids = InstrumentResolver.execution_instrument_ids(session)
            payload = {
                "action": action,
                "scope": scope,
                "session_id": str(session.id),
                "strategy_id": str(session.strategy_id),
                "instrument_ids": inst_ids
            }
            redis_client.xadd("execution_control", {"payload": json.dumps(payload)}, maxlen=10000, approximate=True)
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
    @transaction.atomic
    def create_allocation(user, strategy, credential, allocation_amount=None, allocation_percentage=None, deployed_version=None):
        from strategies.models import Strategy
        strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
        if strategy.user_id != user.id or credential.user_id != user.id:
            raise ValueError('Strategy and broker account must belong to the selected user.')
        if strategy.status != 'ACTIVE':
            raise ValueError('Live allocations can only be created for active strategies.')
        if not strategy.live_trading_enabled:
            raise ValueError('Live trading is disabled for this strategy.')
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
        from strategies.models import Strategy
        strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
        if strategy.status != 'ACTIVE':
            raise ValueError('Only active strategies can start live sessions.')
        if not strategy.live_trading_enabled:
            raise ValueError('Live trading is disabled for this strategy.')
        if allocation.strategy_id != strategy.id or allocation.user_id != user.id:
            raise ValueError('Live allocation does not belong to this strategy and user.')
        if allocation.broker_credential_id != broker_credential.id:
            raise ValueError('Live allocation does not belong to the selected broker account.')
    
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

        # Initialize funds in unified cache for live trading
        LiveExecutionService.sync_funds(broker_credential)

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
                LiveExecutionService._close_position(session=session, position=position)
        # Check if any positions failed to close
        has_open_positions = False
        if close_positions:
            has_open_positions = LivePosition.objects.filter(allocation=session.allocation, quantity__gt=0).exists()
            
        if has_open_positions:
            session.status = "STOPPING"
            session.error_message = "Positions failed to close during square-off. Manual operator review required."
            logger.warning(f"Session {session.id} marked STOPPING due to orphaned open positions.")
        else:
            session.status = "STOPPED"
            session.ended_at = timezone.now()
            session.error_message = ""
            
        session.save(update_fields=["status", "ended_at", "error_message", "updated_at"])

        if has_open_positions:
            # Keep a paused worker alive while broker positions remain open so
            LiveExecutionService._publish_execution_event("SESSION_PAUSE", session, "live")
        else:
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
        if session.strategy.status != 'ACTIVE' or not session.strategy.live_trading_enabled:
            raise ValueError('Activate the strategy and enable live trading before resuming this session.')
        was_stopped = session.status == "STOPPED"
        BrokerService.ensure_session(session.broker_credential)
        LiveExecutionService.sync_funds(session.broker_credential)

        session.status = "RUNNING"
        if was_stopped:
            session.started_at = timezone.now()
        session.ended_at = None
        session.error_message = ""
        update_fields = ["status", "ended_at", "error_message", "updated_at"]
        if was_stopped:
            update_fields.append("started_at")
        session.save(update_fields=update_fields)
        
        NotificationService.notify(
            user=session.user,
            title="Live Strategy Started" if was_stopped else "Live Strategy Resumed",
            message=f"Strategy '{session.strategy.name}' has been {'started' if was_stopped else 'resumed'}.",
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
        if not stats:
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
    def place_order(session, instrument, side, quantity, order_type=OrderType.MARKET, price=None, reason="", request_id=None, intent="ENTRY"):
        if str(order_type) != str(OrderType.MARKET):
            raise ValueError("Only MARKET orders are supported for live execution")
        if request_id:
            existing = LiveOrder.objects.filter(request_id=request_id).first()
            if existing:
                return existing
        try:
            return LiveExecutionService._place_order_internal(session, instrument, side, quantity, price, reason, request_id, intent)
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
    def _place_order_internal(session, instrument, side, quantity, price=None, reason="", request_id=None, intent="ENTRY"):
        broker_session = BrokerService.ensure_session(session.broker_credential)
        
        # Strategy entries already pass the worker's cached capital/risk gates.
        # Avoid a synchronous funds REST request on this order-dispatch path.
        # Keep the refresh fallback for direct/manual calls without a request ID.
        if request_id is None:
            from core.cache_view import cache_view
            funds_data = cache_view.get_funds(session.broker_credential_id)
            if not funds_data:
                LiveExecutionService.sync_funds(session.broker_credential)
        
        settings = getattr(session.broker_credential, 'order_settings', None)
        order_timeout = settings.order_timeout_seconds if settings else 30
        # Keep the signal-side quote as the slippage reference and avoid a
        # separate Redis quote read before sending a market order.
        signal_price = BrokerService.to_decimal(price) if price is not None else Decimal("0")
        expected_price = signal_price if signal_price > 0 else LiveExecutionService.resolve_market_price(instrument)

        LiveExecutionService._validate_auto_disable(session)

        order = LiveExecutionService._execute_market_order(
            session,
            session.allocation,
            instrument,
            side,
            quantity,
            expected_price,
            order_timeout,
            reason=reason,
            request_id=request_id,
            broker_session=broker_session,
            intent=intent,
        )
        return order

    @staticmethod
    def _execute_market_order(session, allocation, instrument, side, quantity, expected_price, order_timeout, reason="", request_id=None, broker_session=None, intent="ENTRY"):
        """Submit live market order to broker - optimized for MARKET orders."""
        quantity = int(quantity or 0)
        expected_price = Decimal(str(expected_price or 0))
        request_id = str(request_id or uuid.uuid4())
        capital_rejection = None
        required_capital = expected_price * quantity

        if quantity <= 0:
            capital_rejection = "Order quantity must be greater than zero"
        elif str(intent or "ENTRY").upper() != "EXIT":
            if expected_price <= 0:
                capital_rejection = "Live order has no valid reference price for capital check"
            else:
                from core.cache_view import cache_view
                funds = cache_view.get_session_funds("live", str(session.id)) or {}
                try:
                    allocation_available = Decimal(str(funds["allocation_available_capital"]))
                except (KeyError, TypeError, ValueError, InvalidOperation):
                    allocation_available = Decimal("0")
                if required_capital > allocation_available:
                    capital_rejection = (
                        "Insufficient cached allocation capital: "
                        f"required {required_capital}, available {allocation_available}"
                    )

        with transaction.atomic():
            if request_id:
                existing = LiveOrder.objects.select_for_update().filter(request_id=request_id).first()
                if existing:
                    return existing

            order = LiveOrder.objects.create(
                user=session.user,
                strategy=session.strategy,
                session=session,
                allocation=allocation,
                broker_credential=session.broker_credential,
                instrument=instrument,
                reason=str(reason or "")[:255],
                request_id=request_id,
                order_type=OrderType.MARKET,
                product_type=LiveExecutionService._resolve_product_type(instrument),
                side=side,
                price=expected_price,
                quantity=quantity,
                pending_quantity=0 if capital_rejection else quantity,
                status=OrderStatus.REJECTED if capital_rejection else "UNKNOWN",
                rejection_reason=capital_rejection or "",
                # Persist an ambiguous state before crossing the broker network
                # boundary. A worker crash here must never cause a duplicate submit.
                reconciliation_status="PENDING",
            )
            ExecutionLog.objects.create(
                order=order,
                event_type="REJECTED" if capital_rejection else "CREATED",
                message=capital_rejection or "Order record created, preparing for broker submission",
            )

        # The durable order now reserves this amount in the allocation. Keep
        # the worker-facing funds projection in sync without another DB read.
        if not capital_rejection and str(intent or "ENTRY").upper() != "EXIT":
            from core.cache_view import cache_view
            funds = cache_view.get_session_funds("live", str(session.id)) or {}
            try:
                available = Decimal(str(funds.get("allocation_available_capital", 0)))
                funds["allocation_available_capital"] = str(max(available - required_capital, Decimal("0")))
                if not cache_api.update_session_funds("live", str(session.id), funds):
                    logger.warning("Cached allocation capital was not updated after creating order %s", order.pk)
            except (TypeError, ValueError, InvalidOperation):
                logger.exception("Could not update cached allocation capital after creating order %s", order.pk)

        if capital_rejection:
            logger.warning("Live order %s rejected before broker submission: %s", order.id, capital_rejection)
            return order

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
                    "order_tag": f"QN{order.id}",
                },
                broker_session=broker_session,
            )
        except Exception as e:
            logger.exception("Broker order submission failed for order %s", order.id)
            # A transport exception is ambiguous: the broker may have accepted
            # the request before the response was lost. Keep it blocking until
            # WebSocket/REST reconciliation confirms a terminal outcome.
            with transaction.atomic():
                order = LiveOrder.objects.select_for_update().get(pk=order.pk)
                terminal = {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED}
                if order.status not in terminal:
                    order.status = "UNKNOWN"
                    order.rejection_reason = str(e)
                    order.reconciliation_status = "PENDING"
                    order.save(update_fields=["status", "rejection_reason", "reconciliation_status", "updated_at"])
                    ExecutionLog.objects.create(order=order, event_type="UNKNOWN", message=f"Submission outcome is unknown: {e}")
            return order

        latency_ms = int((time.perf_counter() - started_at) * 1000)

        # A WebSocket fill can arrive before this REST response. Merge against a
        # locked current row so a delayed REST acknowledgement cannot regress it.
        with transaction.atomic():
            order = LiveOrder.objects.select_for_update().get(pk=order.pk)
            order.broker_order_id = broker_result.get("broker_order_id") or order.broker_order_id
            order.exchange_order_id = broker_result.get("exchange_order_id") or order.exchange_order_id
            broker_status = broker_result.get("status") or "UNKNOWN"
            terminal = {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED}
            if order.status not in terminal and not (order.filled_quantity and broker_status in {OrderStatus.PENDING, OrderStatus.PLACED}):
                order.status = broker_status
            if order.status in terminal:
                order.pending_quantity = 0
            if order.status == OrderStatus.REJECTED:
                order.rejection_reason = broker_result.get("message") or order.rejection_reason
            order.save(update_fields=["status", "pending_quantity", "broker_order_id", "exchange_order_id", "rejection_reason", "updated_at"])

        if order.status == OrderStatus.PLACED:
            ExecutionLog.objects.create(
                order=order,
                event_type="PLACED",
                message=f"Broker order {order.broker_order_id or 'submitted'} placed via REST. Waiting for WebSocket confirmation.",
                latency_ms=max(int(latency_ms or 0), 0)
            )
        elif order.status == "UNKNOWN":
            order.reconciliation_status = "PENDING"
            order.save(update_fields=["status", "broker_order_id", "exchange_order_id", "rejection_reason", "reconciliation_status", "updated_at"])
            ExecutionLog.objects.create(
                order=order,
                event_type="UNKNOWN",
                message="Broker response did not contain a definitive order status.",
                latency_ms=max(int(latency_ms or 0), 0),
            )
        elif order.status == OrderStatus.REJECTED:
            ExecutionLog.objects.create(
                order=order,
                event_type="REJECTED",
                message=f"Broker order submission failed: {order.rejection_reason}",
                latency_ms=max(int(latency_ms or 0), 0)
            )
        return order

    @staticmethod
    @transaction.atomic
    def _apply_fill_to_position(order, filled_quantity=None, fill_price=None, strategy_config=None):
        opposite_side = Side.SELL if order.side == Side.BUY else Side.BUY
        opposite_position = LivePosition.objects.select_for_update().filter(allocation=order.allocation, instrument=order.instrument, side=opposite_side, quantity__gt=0).first()
        position = None

        fill_price = Decimal(str(fill_price or order.avg_fill_price or order.price or 0))
        remaining = int(filled_quantity if filled_quantity is not None else order.filled_quantity or 0)
        from core.cache_view import cache_view
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

            if order.session_id:
                current = cache_view.get_risk_metrics("live", order.session_id)
                pnl = float(pnl)
                current["daily_trades"] = int(current.get("daily_trades", 0) or 0) + 1
                current["daily_pnl"] = float(current.get("daily_pnl", 0.0) or 0.0) + pnl
                current["weekly_pnl"] = float(current.get("weekly_pnl", 0.0) or 0.0) + pnl
                current["monthly_pnl"] = float(current.get("monthly_pnl", 0.0) or 0.0) + pnl
                current["total_closed_trades"] = int(current.get("total_closed_trades", 0) or 0) + 1
                current["closed_trades"] = current["total_closed_trades"]
                current["last_exit_time"] = order.executed_at or timezone.now()
                
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
                
                _publish_cache_after_commit("update_risk_metrics", "live", order.session_id, current)

            if opposite_position.quantity > 0:
                opposite_position.save(update_fields=["quantity", "current_price", "unrealized_pnl", "updated_at"])
                if opposite_position.strategy_id:
                    StrategyRuntimeState.mark_open(
                        "live",
                        order.session_id or 0,
                        opposite_position.instrument_id,
                        side=opposite_position.side,
                        quantity=opposite_position.quantity,
                        avg_price=opposite_position.avg_price,
                        config=strategy_config,
                        opened_at=opposite_position.opened_at,
                        execution_instrument_id=opposite_position.instrument_id,
                    )
            else:
                if opposite_position.strategy_id:
                    StrategyRuntimeState.mark_closed("live", order.session_id or 0, opposite_position.instrument_id)
                if order.session_id:
                    _publish_cache_after_commit("remove_position", "live", str(order.session_id), str(opposite_position.id))
                opposite_position.delete()
            remaining -= closed_qty

        if remaining > 0:
            with transaction.atomic():
                position = LivePosition.objects.select_for_update().filter(allocation=order.allocation, instrument=order.instrument, side=order.side).first()

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

                trade_strategy_id = order.strategy.id if order.strategy else position.strategy_id
                if trade_strategy_id:
                    StrategyRuntimeState.mark_open(
                        "live",
                        order.session_id or 0,
                        position.instrument_id,
                        side=position.side,
                        quantity=position.quantity,
                        avg_price=position.avg_price,
                        config=strategy_config,
                        opened_at=position.opened_at,
                        execution_instrument_id=position.instrument_id,
                    )
                if order.session_id:
                    _publish_cache_after_commit("update_risk_metrics", "live", order.session_id, {"last_entry_time": order.executed_at or timezone.now()})

        # Update unified cache for live trading
        if order.session_id:
            # Update only the affected position in cache (no DB reload)
            if position and position.quantity > 0:
                _publish_cache_after_commit("update_position", "live", str(order.session_id), {
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

        LiveExecutionService._record_slippage(order, fill_price)


    @staticmethod
    def _calculate_slippage(order, actual_price, filled_quantity):
        """Return adverse-positive slippage against the signal reference price."""
        expected = Decimal(str(order.price or 0))
        actual = Decimal(str(actual_price or 0))
        quantity = max(int(filled_quantity or 0), 0)
        if expected <= 0 or actual <= 0 or quantity <= 0:
            return None
        adverse_per_unit = actual - expected if order.side == Side.BUY else expected - actual
        return {
            "expected_price": expected,
            "actual_price": actual,
            "slippage_pct": (adverse_per_unit / expected) * Decimal("100"),
            "slippage_amount": adverse_per_unit * quantity,
        }


    @staticmethod
    def _record_slippage(order, fallback_fill_price=None):
        """Upsert cumulative fill slippage, including partial-fill revisions."""
        actual_price = order.avg_fill_price or fallback_fill_price
        metrics = LiveExecutionService._calculate_slippage(order, actual_price, order.filled_quantity)
        if metrics is None:
            return None
        record, _ = SlippageRecord.objects.update_or_create(order=order, defaults=metrics)
        return record


    @classmethod
    def run_order_stream_consumer(cls, stop_event=None):
        """Consume durable live requests, acknowledging after a durable outcome."""
        from live_trading.models import TradingSession
        from instruments.models import Instrument
        from strategy_engine.order_queue import consume_orders, entry_is_allowed

        def handle(data):
            request_id = data["request_id"]
            existing = LiveOrder.objects.filter(request_id=request_id).first()
            if existing:
                return
            session = TradingSession.objects.select_related("broker_credential").get(id=data["session_id"])
            instrument = Instrument.objects.get(id=data["instrument_id"])
            try:
                if not entry_is_allowed(session.status, data.get("intent")):
                    raise ValueError(f"Live session is {session.status}; queued entry was not submitted")
                order = cls.place_order(
                    session=session, instrument=instrument, side=data["side"], quantity=data["qty"],
                    order_type=data["order_type"], price=data.get("target_price"), reason=data.get("reason") or "",
                    request_id=request_id, intent=data.get("intent") or "ENTRY",
                )
            except Exception as exc:
                # Failures before the broker boundary have no possible external
                # side effect. Persist a rejection so the stream can be acked.
                order, created = LiveOrder.objects.get_or_create(
                    request_id=request_id,
                    defaults={
                        "user": session.user,
                        "strategy": session.strategy,
                        "session": session,
                        "allocation": session.allocation,
                        "broker_credential": session.broker_credential,
                        "instrument": instrument,
                        "reason": str(data.get("reason") or "")[:255],
                        "order_type": data["order_type"],
                        "product_type": cls._resolve_product_type(instrument),
                        "side": data["side"],
                        "price": data.get("target_price"),
                        "quantity": max(int(data.get("qty") or 0), 0),
                        "status": OrderStatus.REJECTED,
                        "rejection_reason": str(exc),
                    },
                )
                if created:
                    ExecutionLog.objects.create(order=order, event_type="REJECTED", message=str(exc))
                logger.exception("Live request %s failed before a durable broker submission", request_id)
        def reconcile(data):
            StrategyRuntimeState.reconcile_trade_state("live", data["session_id"], data["instrument_id"], failed_reason=data.get("reason"))
        logger.info("LiveExecutionService Redis Stream consumer is ready")
        consume_orders("live", handle, stop_event=stop_event, after_durable=reconcile)

    @staticmethod
    def rebuild_runtime_state_from_db(session_id):
        """Initialize and recover runtime state from open live positions using centralized method."""
        from strategy_engine.runtime import StrategyRuntimeState
        return StrategyRuntimeState.rebuild_runtime_state_from_db("live", session_id)


    @staticmethod
    @transaction.atomic
    def _refresh_broker_allocation_health(credential):
        """Check if allocations exceed broker equity and update health flags for all allocations."""
        if not credential:
            return

        # Use unified cache for funds state
        from core.cache_view import cache_view
        funds_data = cache_view.get_funds(credential.id)
        broker_equity = BrokerService.to_decimal(funds_data.get("net_equity") or funds_data.get("cash_balance") or 0)

        # Get all allocations for this broker credential, ordered by creation time
        allocations = LiveStrategyAllocation.objects.filter(broker_credential=credential).exclude(session__status__iexact="STOPPED").order_by('created_at')
        
        stopped_allocations = LiveStrategyAllocation.objects.filter(broker_credential=credential, session__status__iexact="STOPPED").order_by('created_at')
        for allocation in stopped_allocations:
            allocation.is_over_allocated = False
            allocation.breach_reason = ""
            allocation.broker_equity_reference = broker_equity
            allocation.save(update_fields=["is_over_allocated", "breach_reason", "broker_equity_reference", "updated_at"])
        
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

        for session in TradingSession.objects.filter(broker_credential=credential, status__in=["RUNNING", "PAUSED", "STOPPING", "ERROR"]).select_related("allocation"):
            session_payload = dict(payload)
            session_payload["allocation_available_capital"] = str(session.allocation.available_capital if session.allocation else 0)
            cache_api.update_session_funds("live", str(session.id), session_payload)
        return payload

    
    @staticmethod
    def session_summary(user):
        """Return a read-only snapshot; broker I/O runs in the funds sync task."""
        sessions = TradingSession.objects.filter(user=user).select_related("strategy", "broker_credential")
        positions = LivePosition.objects.filter(user=user, quantity__gt=0)
        orders = LiveOrder.objects.filter(user=user)
        active_sessions = sessions.filter(status="RUNNING")
        today_orders = orders.filter(placed_at__date=timezone.localdate())
        active_credentials = list(BrokerCredential.objects.filter(user=user, is_active=True))
        latest_snapshots = BrokerFundsSnapshot.objects.filter(
            credential_id__in=[credential.id for credential in active_credentials]
        ).order_by("credential_id", "-snapshot_time", "-created_at").distinct("credential_id")
        snapshots_by_credential = {snapshot.credential_id: snapshot for snapshot in latest_snapshots}
        credential_ids = [credential.id for credential in active_credentials]
        allocations_by_credential = {}
        for allocation in LiveStrategyAllocation.objects.filter(user=user, broker_credential_id__in=credential_ids).select_related("strategy"):
            allocations_by_credential.setdefault(allocation.broker_credential_id, []).append(allocation)
        valid_credential_ids = set(BrokerSession.objects.filter(
            credential_id__in=credential_ids,
            is_valid=True,
            token_expiry__gt=timezone.now(),
        ).values_list("credential_id", flat=True).distinct())
        broker_summaries = []
        health_keys = [f"live_ws_health:{credential.id}" for credential in active_credentials]
        health_by_key = cache.get_many(health_keys)
        for credential in active_credentials:
            snapshot = snapshots_by_credential.get(credential.id)
            websocket_health = health_by_key.get(f"live_ws_health:{credential.id}") or {}
            websocket_status = websocket_health.get("status", "unknown")
            health_updated_at = parse_datetime(websocket_health.get("updated_at", ""))
            if websocket_status not in {"authentication_required", "unknown"} and (not health_updated_at or (timezone.now() - health_updated_at).total_seconds() > 90):
                websocket_status = "unknown"
            allocation_rows = allocations_by_credential.get(credential.id, [])
            session_valid = credential.id in valid_credential_ids

            is_over_allocated = any(row.is_over_allocated for row in allocation_rows)
            account_healthy = session_valid and snapshot is not None and not is_over_allocated

            broker_summaries.append(
                {
                    "credential_id": credential.id,
                    "broker_label": credential.label,
                    "broker_name": credential.broker_name,
                    "is_healthy": account_healthy,
                    "broker_session_valid": session_valid,
                    "funds_available": snapshot is not None,
                    "order_websocket_status": websocket_status,
                    "order_websocket_updated_at": websocket_health.get("updated_at"),
                    "available_margin": str(snapshot.available_margin) if snapshot else None,
                    "used_margin": str(snapshot.used_margin) if snapshot else None,
                    "net_equity": str(snapshot.net_equity) if snapshot else None,
                    "cash_balance": str(snapshot.cash_balance) if snapshot else None,
                    "funds_as_of": snapshot.snapshot_time.isoformat() if snapshot else None,
                    "allocations": [
                        {
                            "id": row.id,
                            "strategy_id": row.strategy_id,
                            "strategy_name": row.strategy.name,
                            "allocated_capital": str(row.allocated_capital),
                            "broker_equity_reference": str(row.broker_equity_reference),
                            "is_over_allocated": row.is_over_allocated,
                            "breach_reason": row.breach_reason,
                        }
                        for row in allocation_rows
                    ],
                }
            )

        closed_trades = LiveTrade.objects.filter(user=user)
        closed_trade_stats = closed_trades.aggregate(
            total=Count("id"),
            winning=Count("id", filter=Q(realized_pnl__gt=0)),
            losing=Count("id", filter=Q(realized_pnl__lt=0)),
            realized=Sum("realized_pnl"),
        )
        realized_pnl = closed_trade_stats["realized"] or Decimal("0")
        realized_today = LiveTrade.objects.filter(user=user, exit_time__date=timezone.localdate()).aggregate(s=Sum("realized_pnl"))["s"] or Decimal("0")
        todays_trades = LiveTrade.objects.filter(user=user, exit_time__date=timezone.localdate())
        avg_execution_latency = ExecutionLog.objects.filter(order__user=user, latency_ms__gt=0).aggregate(value=Avg("latency_ms"))["value"]
        avg_slippage = SlippageRecord.objects.filter(order__user=user).aggregate(value=Avg("slippage_pct"))["value"]
        order_counts = orders.aggregate(
            filled=Count("id", filter=Q(status=OrderStatus.FILLED)),
            partial=Count("id", filter=Q(status=OrderStatus.PARTIAL_FILL)),
            active=Count("id", filter=Q(status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES)),
            rejected=Count("id", filter=Q(status=OrderStatus.REJECTED)),
            cancelled=Count("id", filter=Q(status=OrderStatus.CANCELLED)),
            expired=Count("id", filter=Q(status=OrderStatus.EXPIRED)),
            unknown=Count("id", filter=Q(status="UNKNOWN")),
        )
        position_counts = positions.aggregate(
            unrealized=Sum("unrealized_pnl"),
            profitable=Count("id", filter=Q(unrealized_pnl__gt=0)),
            losing=Count("id", filter=Q(unrealized_pnl__lt=0)),
        )
        return {
            "generated_at": timezone.now().isoformat(),
            "running_sessions": active_sessions.count(),
            "paused_sessions": sessions.filter(status="PAUSED").count(),
            "error_sessions": sessions.filter(status="ERROR").count(),
            "open_positions": positions.count(),
            "open_orders": order_counts["active"],
            "rejected_orders": order_counts["rejected"],
            "total_orders": orders.count(),
            "filled_orders": order_counts["filled"],
            "partial_orders": order_counts["partial"],
            "active_orders": order_counts["active"],
            "cancelled_orders": order_counts["cancelled"],
            "expired_orders": order_counts["expired"],
            "unknown_orders": order_counts["unknown"],
            "profitable_positions": position_counts["profitable"],
            "losing_positions": position_counts["losing"],
            "total_closed_trades": closed_trade_stats["total"],
            "winning_closed_trades": closed_trade_stats["winning"],
            "losing_closed_trades": closed_trade_stats["losing"],
            "today_orders": today_orders.count(),
            "today_fills": today_orders.filter(status__in=LiveExecutionService.FILLED_ORDER_STATUSES).count(),
            "unrealized_pnl": str(position_counts["unrealized"] or Decimal("0")),
            "realized_pnl": str(realized_pnl),
            "realized_today": str(realized_today),
            "day_pnl": str(realized_today + (position_counts["unrealized"] or Decimal("0"))),
            "closed_trades_today": todays_trades.count(),
            "winning_trades_today": todays_trades.filter(realized_pnl__gt=0).count(),
            "avg_execution_latency_ms": avg_execution_latency,
            "avg_slippage_pct": avg_slippage,
            "active_brokers": sessions.filter(broker_credential__isnull=False).values("broker_credential").distinct().count(),
            "broker_accounts": broker_summaries,
        }

    @staticmethod
    @transaction.atomic
    def stop_all_sessions(user, close_positions=False):
        stopped = []
        sessions = TradingSession.objects.filter(user=user)
        if close_positions:
            sessions = sessions.filter(Q(status__in=["RUNNING", "PAUSED", "ERROR"]) | Q(status="STOPPED", allocation__positions__quantity__gt=0)).distinct()
        else:
            sessions = sessions.filter(status__in=["RUNNING", "PAUSED", "ERROR"])
        for session in sessions:
            stopped.append(LiveExecutionService.stop_session(session, close_positions=close_positions))
        return stopped
