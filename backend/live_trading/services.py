
import logging
from decimal import Decimal

from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from brokers.models import BrokerCredential, OrderReconciliation
from brokers.services import BrokerService
from common.enums import CapitalAllocationType, OrderStatus, OrderType, ProductType, Severity, Side, StrategyStatus, NotificationType
from marketdata.quote_store import QuoteStore
from marketdata.streaming import MarketDataStreamer
from notifications.services import NotificationService

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from strategy_engine.runtime import StrategyRuntimeState
from .cache import LiveBrokerStateCache
from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, LiveTrade, SlippageRecord, TradingSession, LivePortfolio

logger = logging.getLogger(__name__)

class LivePortfolioService:
    @staticmethod
    def get_or_create_portfolio(user):
        portfolio, _ = LivePortfolio.objects.get_or_create(
            user=user,
            defaults={
                "name": "Live Portfolio",
                "initial_capital": Decimal("0"),
                "current_capital": Decimal("0"),
                "peak_value": Decimal("0"),
            },
        )
        return portfolio

    @staticmethod
    def calculate_invested_value(portfolio):
        from live_trading.models import LivePosition
        live_positions = LivePosition.objects.filter(user=portfolio.user)
        return sum((Decimal(str(pos.avg_price)) * pos.quantity for pos in live_positions), Decimal("0"))

    @staticmethod
    def calculate_unrealized_pnl(portfolio):
        from live_trading.models import LivePosition
        live_positions = LivePosition.objects.filter(user=portfolio.user)
        return sum((Decimal(str(pos.unrealized_pnl or 0)) for pos in live_positions), Decimal("0"))

    @staticmethod
    def _live_allocation_utilized(allocation):
        from live_trading.models import LivePosition
        positions = LivePosition.objects.filter(
            user=allocation.user,
            strategy=allocation.strategy,
            broker_credential=allocation.broker_credential,
        )
        return sum((Decimal(str(pos.avg_price)) * pos.quantity for pos in positions), Decimal("0"))


class LiveExecutionService:
    """Service to handle Live Trading Strategy execution."""

    # Dedicated thread pool for async broker API network calls.
    # Prevents slow broker API responses from blocking tick evaluation.

    ORDERBOOK_SYNC_TTL_SECONDS = 2
    BROKER_STATE_STALE_SECONDS = 8
    ACTIVE_ORDER_STATUSES = {OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL}
    FILLED_ORDER_STATUSES = {OrderStatus.PARTIAL_FILL, OrderStatus.FILLED}
    TERMINAL_ORDER_STATUSES = {OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED}

    @staticmethod
    def _execution_config_for_order(order):
        if not getattr(order, "strategy_id", None):
            return {}
        allocation = getattr(order, "allocation", None)
        if allocation and allocation.deployed_version_id:
            return allocation.deployed_version.config_snapshot
        allocation = LiveStrategyAllocation.objects.filter(
            user=order.user,
            strategy=order.strategy,
            broker_credential=order.broker_credential,
        ).select_related("deployed_version").first()
        if allocation and allocation.deployed_version_id:
            return allocation.deployed_version.config_snapshot
        return order.strategy.to_execution_dict()

    @staticmethod
    def _update_routing_cache(session, add=True):
        """
        Triggers the market data ingestion daemon to immediately refresh its
        routing cache (tracked symbols) via Celery without blocking the UI.
        """
        try:
            from marketdata.tasks import refresh_live_market_subscriptions
            refresh_live_market_subscriptions.delay()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Failed to trigger routing cache update: %s", e)

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
    def _broadcast_update(user_id, event_type, data):
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}_live",
                {
                    "type": "live_update",
                    "message": {
                        "event_type": event_type,
                        "data": data,
                    }
                }
            )

    @staticmethod
    def _session_sync_cache_key(session_id):
        return f"live_trading:orderbook_sync:{session_id}"

    @staticmethod
    def _to_decimal(value, default=Decimal("0")):
        try:
            if value in (None, "", "null"):
                return Decimal(str(default))
            return Decimal(str(value))
        except Exception:
            return Decimal(str(default))

    @staticmethod
    def _is_state_stale(state_wrapper, max_age_seconds=None):
        max_age_seconds = max_age_seconds or LiveExecutionService.BROKER_STATE_STALE_SECONDS
        updated_at = (state_wrapper or {}).get("updated_at")
        if not updated_at:
            return True
        try:
            ts = timezone.datetime.fromisoformat(updated_at)
            if timezone.is_naive(ts):
                ts = timezone.make_aware(ts, timezone.get_current_timezone())
            return (timezone.now() - ts).total_seconds() > max_age_seconds
        except Exception:
            return True

    @staticmethod
    def _alert_stale_pending_orders(user, credential, reason, max_age_minutes=5):
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(minutes=max_age_minutes)
        stale_orders = LiveOrder.objects.filter(
            user=user,
            broker_credential=credential,
            status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES,
            placed_at__lte=cutoff,
        ).select_related("strategy", "instrument")
        for order in stale_orders:
            message = (
                f"Broker API unreachable or stale for more than {max_age_minutes} minutes. "
                f"Pending order {order.id} for {order.instrument.symbol} may need manual review. {reason}"
            )
            LiveExecutionService._create_execution_log(
                order,
                "WARNING",
                message=message,
                user_id=user.id,
                broker_credential_id=credential.id,
            )
            try:
                NotificationService.notify(
                    user,
                    title="Broker API outage warning",
                    message=message,
                    severity=Severity.CRITICAL,
                    strategy=order.strategy,
                    data={
                        "order_id": order.id,
                        "broker_credential_id": credential.id,
                        "broker_unreachable": True,
                        "age_minutes": max_age_minutes,
                    },
                )
            except Exception:
                logger.exception("Failed dispatching stale pending order alert for order %s", order.id)

    @staticmethod
    def _auto_cancel_stale_pending_orders(user, credential, reason, max_age_minutes=5):
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(minutes=max_age_minutes)
        stale_orders = LiveOrder.objects.filter(
            user=user,
            broker_credential=credential,
            status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES,
            placed_at__lte=cutoff,
        ).select_related("strategy", "instrument")

        cancelled = 0
        for order in stale_orders:
            if order.status not in LiveExecutionService.ACTIVE_ORDER_STATUSES:
                continue

            order.status = OrderStatus.CANCELLED
            order.rejection_reason = (
                reason or f"Broker API unreachable for > {max_age_minutes} mins"
            )
            order.cancelled_at = timezone.now()
            order.save(update_fields=["status", "rejection_reason", "cancelled_at", "updated_at"])

            LiveExecutionService._restore_trade_phase_after_unsuccessful_order(order, OrderStatus.CANCELLED)
            LiveExecutionService._create_execution_log(
                order,
                "CANCELLED",
                message=f"Auto-cancelled stale pending order after {max_age_minutes} mins due to broker outage: {reason}",
                user_id=user.id,
                broker_credential_id=credential.id,
            )
            cancelled += 1

        return cancelled

    @staticmethod
    def _resolve_instrument_from_broker_symbol(symbol):
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
    def _normalize_broker_position_rows(payload):
        rows = payload.get("netPositions") or payload.get("data") or payload.get("positions") or []
        rows = rows if isinstance(rows, list) else []
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = row.get("symbol") or row.get("tradingsymbol") or row.get("ticker")
            quantity = int(row.get("netqty") or row.get("netQty") or row.get("quantity") or row.get("qty") or 0)
            if not symbol or quantity == 0:
                continue
            avg_price = LiveExecutionService._to_decimal(row.get("avgPrice") or row.get("averageprice") or row.get("avg_price"))
            ltp = LiveExecutionService._to_decimal(row.get("ltp") or row.get("current_price") or row.get("last_price") or avg_price)
            side = Side.BUY if quantity > 0 else Side.SELL
            abs_qty = abs(quantity)
            normalized.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "quantity": abs_qty,
                    "avg_price": avg_price,
                    "current_price": ltp,
                    "unrealized_pnl": LiveExecutionService._to_decimal(row.get("pl") or row.get("unrealized_pnl")),
                    "realized_pnl": LiveExecutionService._to_decimal(row.get("realized_pnl") or row.get("realized")),
                    "raw": row,
                }
            )
        return normalized

    @staticmethod
    def _normalize_broker_order_rows(payload):
        rows = LiveExecutionService._extract_orderbook_rows(payload)
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = row.get("symbol") or row.get("tradingsymbol") or row.get("ticker")
            qty = int(row.get("qty") or row.get("quantity") or row.get("orderQty") or 0)
            filled = int(row.get("filledQty") or row.get("filled_quantity") or row.get("tradedQty") or 0)
            pending = row.get("remainingQuantity") or row.get("pending_quantity")
            pending = int(pending) if pending is not None else max(qty - filled, 0)
            normalized.append(
                {
                    "broker_order_id": str(row.get("id") or row.get("orderid") or row.get("broker_order_id") or row.get("orderNumStatus") or ""),
                    "exchange_order_id": str(row.get("exchOrdId") or row.get("exchange_order_id") or ""),
                    "symbol": symbol,
                    "side": LiveExecutionService._normalize_broker_side(row.get("side") or row.get("transactiontype")),
                    "quantity": qty,
                    "filled_quantity": filled,
                    "pending_quantity": max(pending, 0),
                    "price": LiveExecutionService._to_decimal(row.get("limitPrice") or row.get("price") or row.get("avgPrice") or 0),
                    "status": LiveExecutionService._normalize_order_status(row.get("status") or row.get("orderStatus") or row.get("orderNumStatus")),
                    "raw": row,
                }
            )
        return normalized

    @staticmethod
    def _normalize_broker_side(value):
        if value == 1 or str(value).strip() == "1":
            return Side.BUY
        if value == -1 or str(value).strip() == "-1":
            return Side.SELL
        side_text = str(value or "").upper()
        if side_text in {"BUY", "B"}:
            return Side.BUY
        if side_text in {"SELL", "S"}:
            return Side.SELL
        return side_text

    @staticmethod
    def _sync_funds_from_broker(credential, force=False, async_refresh=False):
        cached = LiveBrokerStateCache.get_funds_state(credential.user_id, credential.id)
        if cached and not force:
            if not LiveExecutionService._is_state_stale(cached):
                return cached.get("payload") or {}

            if async_refresh:
                from live_trading.tasks import refresh_broker_funds
                refresh_broker_funds.delay(credential.id)
                return cached.get("payload") or {}
                
        if async_refresh and not force:
            from live_trading.tasks import refresh_broker_funds
            refresh_broker_funds.delay(credential.id)
            return cached.get("payload") if cached else {}

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
        LiveBrokerStateCache.set_funds_state(credential.user_id, credential.id, payload)
        return payload

    @staticmethod
    def _sync_allocation_wallet(allocation):
        positions = LivePosition.objects.filter(allocation=allocation)
        active_orders = LiveOrder.objects.filter(
            allocation=allocation,
            status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES,
            reduce_only=False,
        )
        used_capital = sum(
            (Decimal(str(pos.avg_price or 0)) * Decimal(str(pos.quantity or 0)) for pos in positions),
            Decimal("0"),
        )
        reserved_capital = sum(
            (
                Decimal(str(order.price or order.avg_fill_price or 0))
                * Decimal(str(order.pending_quantity or order.quantity or 0))
                for order in active_orders
            ),
            Decimal("0"),
        )
        realized_pnl = sum((Decimal(str(pos.realized_pnl or 0)) for pos in positions), Decimal("0"))
        unrealized_pnl = sum((Decimal(str(pos.unrealized_pnl or 0)) for pos in positions), Decimal("0"))
        total_pnl = realized_pnl + unrealized_pnl
        available_capital = max(Decimal("0"), Decimal(str(allocation.allocated_capital or 0)) - used_capital - reserved_capital)
        allocation.used_capital = used_capital
        allocation.reserved_capital = reserved_capital
        allocation.available_capital = available_capital
        allocation.realized_pnl = realized_pnl
        allocation.unrealized_pnl = unrealized_pnl
        allocation.total_pnl = total_pnl
        allocation.last_synced_at = timezone.now()
        allocation.save(
            update_fields=[
                "used_capital",
                "reserved_capital",
                "available_capital",
                "realized_pnl",
                "unrealized_pnl",
                "total_pnl",
                "last_synced_at",
                "updated_at",
            ]
        )
        LiveBrokerStateCache.set_strategy_wallet(
            allocation.strategy_id,
            allocation.broker_credential_id,
            {
                "allocation_id": allocation.id,
                "allocated_capital": str(allocation.allocated_capital),
                "used_capital": str(allocation.used_capital),
                "reserved_capital": str(allocation.reserved_capital),
                "available_capital": str(allocation.available_capital),
                "total_pnl": str(allocation.total_pnl),
                "is_over_allocated": allocation.is_over_allocated,
                "breach_reason": allocation.breach_reason,
            },
        )
        return allocation

    @staticmethod
    def _refresh_broker_allocation_health(user, broker_credential):
        funds = LiveExecutionService._sync_funds_from_broker(broker_credential)
        broker_equity = LiveExecutionService._to_decimal(funds.get("net_equity") or funds.get("available_margin") or 0)
        allocations = list(
            LiveStrategyAllocation.objects.filter(
                user=user,
                broker_credential=broker_credential,
            ).select_related("strategy")
        )
        total_allocated = sum((Decimal(str(item.allocated_capital or 0)) for item in allocations), Decimal("0"))
        for allocation in allocations:
            if allocation.allocation_type == CapitalAllocationType.PERCENTAGE and broker_equity > 0:
                allocation.allocated_capital = (Decimal(str(allocation.allocated_percentage or 0)) / Decimal("100")) * broker_equity
            allocation.broker_equity_reference = broker_equity
        total_allocated = sum((Decimal(str(item.allocated_capital or 0)) for item in allocations), Decimal("0"))
        for allocation in allocations:
            was_over_allocated = allocation.is_over_allocated
            allocation.broker_equity_reference = broker_equity
            allocation.is_over_allocated = broker_equity > 0 and total_allocated > broker_equity
            allocation.breach_reason = (
                f"Allocated capital {total_allocated} exceeds broker equity {broker_equity}"
                if allocation.is_over_allocated
                else ""
            )
            allocation.save(update_fields=["allocated_capital", "broker_equity_reference", "is_over_allocated", "breach_reason", "updated_at"])
            if allocation.is_over_allocated and not was_over_allocated:
                cache_key = f"live_over_allocation_notification_{allocation.id}"
                if not cache.get(cache_key):
                    NotificationService.notify(
                        user=user,
                        title="Live Allocation Over Limit",
                        message=allocation.breach_reason,
                        notification_type=NotificationType.RISK_ALERT,
                        severity=Severity.CRITICAL,
                        strategy=allocation.strategy,
                        data={
                            "allocation_id": str(allocation.id),
                            "broker_credential_id": str(broker_credential.id),
                            "module": "live",
                        },
                    )
                    cache.set(cache_key, True, 86400)
            LiveExecutionService._sync_allocation_wallet(allocation)
        return allocations

    @staticmethod
    def _resolve_live_allocation(
        user,
        strategy,
        credential,
        allocation_amount=None,
        allocation_percentage=None,
        allow_existing=False,
    ):
        portfolio = LivePortfolioService.get_or_create_portfolio(user)
        existing_allocation = LiveStrategyAllocation.objects.filter(
            user=user,
            strategy=strategy,
            broker_credential=credential,
        ).first()
        if existing_allocation and not allow_existing:
            raise ValueError(
                "A live allocation already exists for this strategy and broker. "
                "Update the existing allocation instead."
            )

        latest_funds = LiveExecutionService._sync_funds_from_broker(credential)
        broker_equity = LiveExecutionService._to_decimal(
            latest_funds.get("net_equity") or latest_funds.get("available_margin") or latest_funds.get("cash_balance") or 0
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
        elif existing_allocation:
            allocation_type = existing_allocation.allocation_type
            if allocation_type == CapitalAllocationType.PERCENTAGE:
                allocated_percentage = Decimal(str(existing_allocation.allocated_percentage or 0))
                allocated_capital = (allocated_percentage / Decimal("100")) * broker_equity
            else:
                allocated_capital = Decimal(str(existing_allocation.allocated_capital or 0))
                allocated_percentage = Decimal("0")
        else:
            raise ValueError("Live deployment requires a broker capital allocation amount or percentage")

        if allocated_capital <= 0:
            raise ValueError("Allocated capital must be greater than zero")

        existing = list(
            LiveStrategyAllocation.objects.filter(
                user=user,
                broker_credential=credential,
            ).exclude(strategy=strategy)
        )
        total_other = sum((Decimal(str(item.allocated_capital or 0)) for item in existing), Decimal("0"))
        if broker_equity > 0 and total_other + allocated_capital > broker_equity:
            raise ValueError(
                f"Live allocation exceeds broker equity. Requested={allocated_capital}, already allocated={total_other}, broker equity={broker_equity}"
            )

        if existing_allocation:
            allocation = existing_allocation
            allocation.portfolio = portfolio
            allocation.allocation_type = allocation_type
            allocation.allocated_capital = allocated_capital
            allocation.allocated_percentage = allocated_percentage or Decimal("0")
            allocation.available_capital = allocated_capital
            allocation.broker_equity_reference = broker_equity
            allocation.is_over_allocated = False
            allocation.breach_reason = ""
            allocation.save()
        else:
            allocation = LiveStrategyAllocation.objects.create(
                user=user,
                strategy=strategy,
                broker_credential=credential,
                portfolio=portfolio,
                allocation_type=allocation_type,
                allocated_capital=allocated_capital,
                allocated_percentage=allocated_percentage or Decimal("0"),
                available_capital=allocated_capital,
                broker_equity_reference=broker_equity,
            )
        return LiveExecutionService._sync_allocation_wallet(allocation)

    @staticmethod
    def _ensure_fresh_broker_state(user, credential, force=False):
        funds_state = LiveBrokerStateCache.get_funds_state(user.id, credential.id)
        pos_state = LiveBrokerStateCache.get_positions_state(user.id, credential.id)
        order_state = LiveBrokerStateCache.get_orders_state(user.id, credential.id)
        if force or LiveExecutionService._is_state_stale(funds_state) or LiveExecutionService._is_state_stale(pos_state) or LiveExecutionService._is_state_stale(order_state):
            LiveExecutionService.sync_account_state(user, credential=credential, force=True)

    @staticmethod
    def _resolve_product_type(instrument):
        if getattr(instrument, 'instrument_type', '') in ('STOCK', 'INDEX'):
            return ProductType.CNC
        return ProductType.MARGIN
    @staticmethod
    @transaction.atomic
    def deploy_strategy(user, strategy, broker_credential=None, allocation_amount=None, allocation_percentage=None):
        if strategy.user_id != user.id:
            raise ValueError("Strategy does not belong to the authenticated user")
        if not strategy.live_trading_enabled:
            strategy.live_trading_enabled = True
            if strategy.status == StrategyStatus.DRAFT:
                strategy.status = StrategyStatus.ACTIVE
            strategy.save(update_fields=["live_trading_enabled", "status", "updated_at"])

        credential = broker_credential or BrokerCredential.objects.filter(user=user, is_active=True, is_verified=True).first()
        if not credential:
            raise ValueError("No active verified broker credential found")

        BrokerService.ensure_session(credential)
        LiveExecutionService.sync_account_state(user, credential=credential, force=True)
        allocation = LiveExecutionService._resolve_live_allocation(
            user,
            strategy,
            credential,
            allocation_amount=allocation_amount,
            allocation_percentage=allocation_percentage,
        )

        session, _ = TradingSession.objects.update_or_create(
            allocation=allocation,
            defaults={
                "user": user,
                "strategy": strategy,
                "broker_credential": credential,
                "status": "RUNNING",
                "started_at": timezone.now(),
                "ended_at": None,
                "error_message": "",
            },
        )

        # read from the allocation's deployed StrategyVersion when pinned.
        from risk_management.cache import RiskCache
        RiskCache.sync_from_db("LIVE", session.id)

        LiveExecutionService._sync_allocation_wallet(allocation)
        LiveExecutionService._broadcast_update(user.id, "SESSION_UPDATE", {"session_id": session.id, "status": session.status})
        LiveExecutionService._update_routing_cache(session, add=True)
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
    def update_allocation(session, allocation_amount=None, allocation_percentage=None):
        user = session.user
        strategy = session.strategy
        credential = session.broker_credential
        if not session.allocation_id:
            raise ValueError("This live session is not linked to an allocation")
        allocation = LiveExecutionService._resolve_live_allocation(
            user,
            strategy,
            credential,
            allocation_amount=allocation_amount,
            allocation_percentage=allocation_percentage,
            allow_existing=True,
        )
        LiveExecutionService._broadcast_update(user.id, "ALLOCATION_UPDATE", {
            "strategy_id": strategy.id,
            "broker_id": credential.id,
            "allocated_capital": str(allocation.allocated_capital)
        })
        return allocation

    @staticmethod
    @transaction.atomic
    def pause_session(session):
        # Cancel pending entry orders (orders without a matching open position)
        for order in LiveOrder.objects.filter(session=session, status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES):
            has_position = LivePosition.objects.filter(
                user=session.user,
                strategy=session.strategy,
                broker_credential=session.broker_credential,
                instrument=order.instrument,
                quantity__gt=0
            ).exists()
            if not has_position:
                try:
                    LiveExecutionService.cancel_open_order(order)
                except Exception:
                    logger.exception("Failed cancelling live entry order %s during session pause", order.id)
                    try:
                        NotificationService.notify(
                            user=session.user,
                            title="Order Cancellation Failed",
                            message=f"Failed to cancel order {order.id} for {order.instrument.symbol} during session pause. This order may still be active at the broker.",
                            notification_type=NotificationType.RISK_ALERT,
                            severity=Severity.CRITICAL,
                            strategy=session.strategy,
                            data={"order_id": str(order.id), "symbol": order.instrument.symbol, "module": "live"}
                        )
                    except Exception:
                        logger.exception("Failed dispatching cancel failure notification")

        session.status = "PAUSED"
        session.error_message = ""
        session.save(update_fields=["status", "error_message", "updated_at"])
        LiveExecutionService._broadcast_update(session.user_id, "SESSION_UPDATE", {"session_id": session.id, "status": session.status})
        LiveExecutionService._update_routing_cache(session, add=False)

        NotificationService.notify(
            user=session.user,
            title="Live Strategy Paused",
            message=f"Strategy '{session.strategy.name}' has been paused manually.",
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
        for order in LiveOrder.objects.filter(session=session, status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES):
            try:
                LiveExecutionService.cancel_open_order(order)
            except Exception:
                logger.exception("Failed cancelling live order %s during session stop", order.id)
                try:
                    NotificationService.notify(
                        user=session.user,
                        title="Order Cancellation Failed",
                        message=f"Failed to cancel order {order.id} for {order.instrument.symbol} during session stop. This order may still be active at the broker.",
                        notification_type=NotificationType.RISK_ALERT,
                        severity=Severity.CRITICAL,
                        strategy=session.strategy,
                        data={"order_id": str(order.id), "symbol": order.instrument.symbol, "module": "live"}
                    )
                except Exception:
                    logger.exception("Failed dispatching cancel failure notification")
        if close_positions:
            position_query = LivePosition.objects.filter(
                user=session.user,
                strategy=session.strategy,
                broker_credential=session.broker_credential,
            )
            if session.allocation_id:
                position_query = position_query.filter(allocation_id=session.allocation_id)
            for position in position_query:
                for order in LiveOrder.objects.filter(
                    user=session.user,
                    strategy=session.strategy,
                    instrument=position.instrument,
                    status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES,
                ):
                    LiveExecutionService.cancel_open_order(order)

                # EOD Position Square-off
                LiveExecutionService.place_order(
                    session=session,
                    instrument=position.instrument,
                    side=Side.SELL if position.side == Side.BUY else Side.BUY,
                    quantity=position.quantity,
                    order_type=OrderType.MARKET,
                    price=position.current_price or position.avg_price,
                )
        # Check if any positions failed to close (e.g. stock hit circuit breaker, broker rejected order)
        has_open_positions = False
        if close_positions:
            has_open_positions = LivePosition.objects.filter(
                user=session.user, 
                strategy=session.strategy, 
                broker_credential=session.broker_credential,
                quantity__gt=0
            ).exists()
            if session.allocation_id:
                has_open_positions = LivePosition.objects.filter(
                    allocation_id=session.allocation_id,
                    quantity__gt=0,
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
        LiveExecutionService._broadcast_update(session.user_id, "SESSION_UPDATE", {"session_id": session.id, "status": session.status})
        LiveExecutionService._update_routing_cache(session, add=False)

        LiveExecutionService._publish_execution_event("SESSION_STOP", session, "live")
        NotificationService.notify(
            user=session.user,
            title="Live Strategy Stopped",
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
        
        LiveExecutionService._broadcast_update(session.user_id, "SESSION_UPDATE", {"session_id": session.id, "status": session.status})
        LiveExecutionService._update_routing_cache(session, add=True)
        return session

    @staticmethod
    @transaction.atomic
    def cancel_open_order(order):
        if order.status not in LiveExecutionService.ACTIVE_ORDER_STATUSES:
            return order
        broker_result = BrokerService.cancel_order(order.broker_credential, order.broker_order_id)
        mapped_status = LiveExecutionService._normalize_order_status(broker_result.get("status"))
        order.status = mapped_status
        if mapped_status == OrderStatus.CANCELLED:
            order.pending_quantity = 0
            order.cancelled_at = timezone.now()
        order.save(update_fields=["status", "pending_quantity", "cancelled_at", "updated_at"])
        LiveExecutionService._broadcast_update(order.user_id, "ORDER_UPDATE", {"order_id": order.id, "status": order.status})
        LiveExecutionService._create_execution_log(
            order,
            OrderStatus.CANCELLED if mapped_status == OrderStatus.CANCELLED else OrderStatus.REJECTED,
            message=f"Broker order {order.broker_order_id} {mapped_status}",
        )
        LiveExecutionService._restore_trade_phase_after_unsuccessful_order(order, mapped_status)
        return order

    @staticmethod
    def _restore_trade_phase_after_unsuccessful_order(order, status):
        if not order.strategy_id:
            return
        if order.reduce_only:
            position = LivePosition.objects.filter(
                user=order.user,
                strategy=order.strategy,
                broker_credential=order.broker_credential,
                instrument=order.instrument,
            ).first()
            if position:
                base_inst = LiveExecutionService._get_base_instrument(order.strategy, order.instrument)
                trade_state = StrategyRuntimeState.mark_open(
                    "live",
                    order.session_id or 0,
                    base_inst.id,
                    side=position.side,
                    quantity=position.quantity,
                    avg_price=position.avg_price,
                    config=LiveExecutionService._execution_config_for_order(order),
                    opened_at=position.opened_at,
                    execution_instrument_id=position.instrument_id,
                )
                StrategyRuntimeState.update_position_state(
                    "live-position",
                    position.id,
                    {
                        "phase": trade_state.get("phase"),
                        "entry_time": trade_state.get("entry_time"),
                        "protected_stop_price": trade_state.get("protected_stop_price"),
                        "protected_target_price": trade_state.get("protected_target_price"),
                    },
                )
                return
        base_inst = LiveExecutionService._get_base_instrument(order.strategy, order.instrument)
        StrategyRuntimeState.mark_closed(
            "live",
            order.session_id or 0,
            base_inst.id,
        )

    @staticmethod
    def _resolve_price(instrument, fallback_price=None):
        quote = QuoteStore.get_latest(instrument.sym_ticker)
        if quote and quote.get("price") is not None:
            return Decimal(str(quote["price"]))
        if fallback_price is not None:
            return Decimal(str(fallback_price))
        return Decimal(str(instrument.previous_close or 0))

    @staticmethod
    def _get_active_allocation(session):
        if not session.allocation_id:
            return None
        allocation = session.allocation
        if (
            allocation.user_id != session.user_id
            or allocation.strategy_id != session.strategy_id
            or allocation.broker_credential_id != session.broker_credential_id
        ):
            raise ValueError("Live session allocation does not match its strategy or broker")
        return allocation

    @staticmethod
    def _estimate_required_capital(quantity, price, slippage_pct=Decimal("0.005")):
        notional = Decimal(str(quantity)) * Decimal(str(price))
        return notional * (Decimal("1") + Decimal(str(slippage_pct or 0)))

    @staticmethod
    def _validate_allocation_and_margin(session, instrument, quantity, price, reduce_only=False):
        allocation = LiveExecutionService._get_active_allocation(session)
        if not allocation:
            raise ValueError("No live strategy allocation configured for this strategy and broker account")
        LiveExecutionService._sync_allocation_wallet(allocation)

        if allocation.is_over_allocated:
            raise ValueError(allocation.breach_reason or "Strategy allocation exceeds broker equity")

        if reduce_only:
            return allocation, Decimal("0"), quantity

        LiveExecutionService._ensure_fresh_broker_state(session.user, session.broker_credential)
        funds_state = LiveBrokerStateCache.get_funds_state(session.user_id, session.broker_credential_id)
        funds_payload = (funds_state or {}).get("payload") or {}
        available_margin = LiveExecutionService._to_decimal(funds_payload.get("available_margin") or funds_payload.get("cash_balance"))
        required_capital = LiveExecutionService._estimate_required_capital(quantity, price)

        if allocation.available_capital < required_capital or available_margin < required_capital:
            reason = []
            if allocation.available_capital < required_capital:
                reason.append(f"allocation available={allocation.available_capital}")
            if available_margin < required_capital:
                reason.append(f"broker margin available={available_margin}")
            raise ValueError(
                f"Live capital check failed: required={required_capital}; " + ", ".join(reason)
            )

        return allocation, required_capital, quantity

    @staticmethod
    def _validate_live_risk(session, instrument, quantity, price):
        LiveExecutionService._ensure_fresh_broker_state(session.user, session.broker_credential)
        from risk_management.auto_disable import AutoDisableGate
        from risk_management.cache import RiskCache

        stats = RiskCache.get_or_rebuild("LIVE", session.user_id, session.id)
        allocation = session.allocation
        capital = allocation.allocated_capital if allocation else Decimal("0")
        match = AutoDisableGate.evaluate(session, stats, capital)
        if match:
            raise ValueError(session.error_message)

    @staticmethod
    def _normalize_order_status(value):
        if value in OrderStatus.values:
            return value
        if value is None:
            return OrderStatus.PENDING
        status_text = str(value).upper()
        if status_text in {"6", "PENDING", "TRANSIT", "OPEN"}:
            return OrderStatus.PENDING
        if status_text in {"4", "PLACED", "TRIGGER PENDING", "ACKNOWLEDGED"}:
            return OrderStatus.PLACED
        if status_text in {"2", "FILLED", "TRADED", "EXECUTED", "COMPLETE"}:
            return OrderStatus.FILLED
        if status_text in {"1", "CANCELLED", "CANCELED"}:
            return OrderStatus.CANCELLED
        if status_text in {"5", "REJECTED"}:
            return OrderStatus.REJECTED
        if status_text in {"PARTIAL", "PARTIAL_FILL", "PARTIALLY FILLED"}:
            return OrderStatus.PARTIAL_FILL
        if status_text in {"EXPIRED"}:
            return OrderStatus.EXPIRED
        return OrderStatus.PENDING

    @staticmethod
    def _extract_orderbook_rows(payload):
        if not isinstance(payload, dict):
            return []
        for key in ("orderBook", "orderbook", "book", "data"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return rows
            if isinstance(rows, dict):
                for nested_key in ("orderBook", "orderbook", "rows"):
                    nested_rows = rows.get(nested_key)
                    if isinstance(nested_rows, list):
                        return nested_rows
        return []

    @staticmethod
    def _match_broker_order_row(order, rows):
        broker_id = (order.broker_order_id or "").strip()
        exchange_id = (order.exchange_order_id or "").strip()
        for row in rows:
            row_broker_id = str(row.get("id") or row.get("broker_order_id") or row.get("orderNumStatus") or "").strip()
            row_exchange_id = str(row.get("exchOrdId") or row.get("exchange_order_id") or "").strip()
            if broker_id and broker_id == row_broker_id:
                return row
            if exchange_id and exchange_id == row_exchange_id:
                return row
        return None

    @staticmethod
    def _create_execution_log(order, event_type, message="", fill_quantity=0, fill_price=None, latency_ms=0):
        return ExecutionLog.objects.create(
            order=order,
            event_type=event_type,
            message=message,
            fill_quantity=max(int(fill_quantity or 0), 0),
            fill_price=fill_price,
            latency_ms=max(int(latency_ms or 0), 0),
        )

    @staticmethod
    def place_order(session, instrument, side, quantity, order_type=OrderType.MARKET, price=None):
        try:
            return LiveExecutionService._place_order_internal(session, instrument, side, quantity, order_type, price)
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
    def _place_order_internal(session, instrument, side, quantity, order_type=OrderType.MARKET, price=None):
        if session.status != "RUNNING":
            raise ValueError("Live trading session is not running")
            
        existing_unknown = LiveOrder.objects.filter(
            session=session,
            instrument=instrument,
            status="UNKNOWN"
        ).exists()
        if existing_unknown:
            logger.warning(
                f"Skipping order placement: Session {session.id} has an UNKNOWN order "
                f"for {instrument.symbol}. Pending automatic verification."
            )
            return None

        BrokerService.ensure_session(session.broker_credential)
        LiveExecutionService._ensure_fresh_broker_state(session.user, session.broker_credential)
        settings = getattr(session.broker_credential, 'order_settings', None)
        max_retries = settings.max_retries if settings else 2
        retry_delay = (settings.retry_delay_ms if settings else 500) / 1000.0
        order_timeout = settings.order_timeout_seconds if settings else 30
        expected_price = Decimal(str(price)) if price is not None else LiveExecutionService._resolve_price(instrument)

        reduce_only = bool(
            LivePosition.objects.filter(
                user=session.user,
                strategy=session.strategy,
                broker_credential=session.broker_credential,
                instrument=instrument,
                side=Side.SELL if side == Side.BUY else Side.BUY,
            ).exists()
        )

        # Enforce Circuit Limits
        if instrument.circuit_limit_upper and expected_price > instrument.circuit_limit_upper:
             raise ValueError(f"Order price {expected_price} exceeds upper circuit limit {instrument.circuit_limit_upper}")
        if instrument.circuit_limit_lower and expected_price < instrument.circuit_limit_lower:
             raise ValueError(f"Order price {expected_price} is below lower circuit limit {instrument.circuit_limit_lower}")

        allocation, required_capital, quantity = LiveExecutionService._validate_allocation_and_margin(
            session,
            instrument,
            int(quantity),
            expected_price,
            reduce_only=reduce_only,
        )

        LiveExecutionService._validate_live_risk(session, instrument, quantity, expected_price)

        import uuid
        temp_order_id = f"live_pending_{uuid.uuid4().hex}"

        base_inst = LiveExecutionService._get_base_instrument(session.strategy, instrument) if session.strategy else instrument
        if reduce_only:
            StrategyRuntimeState.mark_exit_pending(
                "live",
                session.id,
                base_inst.id,
            )
        else:
            StrategyRuntimeState.mark_entry_pending(
                "live",
                session.id,
                base_inst.id,
                side=side,
            )

        order = LiveExecutionService._execute_broker_placement(
            temp_order_id,
            session.id,
            instrument.id,
            side,
            quantity,
            order_type,
            expected_price,
            reduce_only,
            order_timeout,
            max_retries,
            retry_delay,
            float(required_capital)
        )
        return order

    @classmethod
    def _execute_broker_placement(cls, temp_order_id, session_id, instrument_id, side, quantity, order_type, expected_price, reduce_only, order_timeout, max_retries, retry_delay, required_capital):
        """Executes a broker placement synchronously.."""
        from live_trading.models import LiveOrder, TradingSession
        from instruments.models import Instrument

        session = None
        order = None
        try:
            session = TradingSession.objects.get(id=session_id)
            instrument = Instrument.objects.get(id=instrument_id)
            settings = getattr(session.broker_credential, 'order_settings', None)
            allocation = session.allocation
            if not allocation:
                raise ValueError("Live session is not linked to an allocation")
            
            # Now create the order record asynchronously!
            order = LiveOrder.objects.create(
                user=session.user,
                strategy=session.strategy,
                session=session,
                allocation=allocation,
                portfolio=LivePortfolioService.get_or_create_portfolio(session.user),
                broker_credential=session.broker_credential,
                instrument=instrument,
                source_type="STRATEGY",
                reduce_only=reduce_only,
                requested_value=required_capital,
                order_type=order_type,
                product_type=LiveExecutionService._resolve_product_type(instrument),
                side=side,
                price=expected_price,
                quantity=int(quantity),
                status=OrderStatus.PENDING,
                validity="DAY",
            )
            LiveExecutionService._create_execution_log(order, "CREATED", message="Order record created, preparing for broker submission")
        except Exception as e:
            logger.exception("Async broker placement failed to load objects or create order")
            try:
                from users.models import User
                from strategies.models import Strategy
                user = User.objects.filter(id=TradingSession.objects.filter(id=session_id).values_list('user_id', flat=True).first()).first()
                strategy = Strategy.objects.filter(id=TradingSession.objects.filter(id=session_id).values_list('strategy_id', flat=True).first()).first()
                if user:
                    NotificationService.notify(
                        user=user,
                        title="Live Order Submission Failed",
                        message=f"Internal error prevented order submission to broker. The system will attempt recovery.",
                        notification_type=NotificationType.STRATEGY_ERROR,
                        severity=Severity.CRITICAL,
                        strategy=strategy,
                        data={"module": "live", "error": str(e)}
                    )
                state = StrategyRuntimeState.trade_state("live", session_id, instrument_id)
                revert_phase = StrategyRuntimeState.OPEN if state.get("quantity", 0) > 0 else StrategyRuntimeState.CLOSED
                StrategyRuntimeState.update_trade_state("live", session_id, instrument_id, {"phase": revert_phase})
            except Exception:
                logger.exception("Failed recovery after async broker placement crash")
            return

        broker_result = {}
        last_error = None
        import time
        started_at = time.perf_counter()

        # 4. Attempt Broker Submission (SENT)
        for attempt in range(max_retries + 1):
            try:
                broker_result = BrokerService.place_order(
                    session.broker_credential,
                    {
                        "instrument": instrument.sym_ticker,
                        "side": side,
                        "quantity": int(quantity),
                        "order_type": order_type,
                        "product_type": order.product_type,
                        "price": str(expected_price),
                        "fallback_price": str(expected_price),
                        "validity": order.validity,
                        # Idempotency key — unique per order DB record.
                        # The broker uses this to de-duplicate retried network calls.
                        # If the same client_ref_id arrives twice, the exchange
                        # only processes the first occurrence.
                        "tag": f"QN_{order.id}",
                        "client_ref_id": str(order.id),
                        "timeout": order_timeout,
                        "reduce_only": reduce_only,
                    },
                )
                if broker_result.get("status") != "REJECTED":
                    break

                # Only retry if it looks like a transient error
                msg = (broker_result.get("message") or "").lower()
                if any(x in msg for x in ["timeout", "network", "rate limit", "internal error", "busy"]):
                    if attempt < max_retries:
                        sleep_time = retry_delay * (2 ** attempt)
                        time.sleep(sleep_time)
                        continue
                break
            except Exception as e:
                last_error = e
                logger.warning(
                    "Broker order attempt %d/%d failed for order %s: %s",
                    attempt + 1, max_retries + 1, order.id, e,
                )
                if attempt < max_retries:
                    sleep_time = retry_delay * (2 ** attempt)
                    time.sleep(sleep_time)
                    continue
                break


        # 4. Handle Results
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        if not broker_result:
            is_timeout = False
            if last_error:
                err_str = str(last_error).lower()
                if "timeout" in err_str or "read" in err_str or "connection" in err_str:
                    is_timeout = True

            if is_timeout:
                order.status = "UNKNOWN"
                order.rejection_reason = f"Network timeout/disconnect: {last_error}"
                order.save(update_fields=["status", "rejection_reason", "updated_at"])
                LiveExecutionService._create_execution_log(order, "UNKNOWN", message="Broker timeout; status pending verification", latency_ms=latency_ms)
                # DO NOT restore trade phase. Let the sync task reconcile it.
                try:
                    NotificationService.notify(
                        user=order.user,
                        title="Live Order Status Unknown",
                        message=f"Order for {instrument.sym_ticker} timed out after broker network failure. Status is UNKNOWN and pending automatic verification.",
                        notification_type=NotificationType.RISK_ALERT,
                        severity=Severity.CRITICAL,
                        strategy=order.strategy,
                        data={"order_id": str(order.id), "symbol": instrument.sym_ticker, "module": "live"}
                    )
                except Exception:
                    logger.exception("Failed dispatching UNKNOWN order notification for order %s", order.id)
            else:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = str(last_error) if last_error else "Unknown broker error"
                order.save(update_fields=["status", "rejection_reason", "updated_at"])
                LiveExecutionService._create_execution_log(order, "REJECTED", message=order.rejection_reason, latency_ms=latency_ms)
                LiveExecutionService._restore_trade_phase_after_unsuccessful_order(order, OrderStatus.REJECTED)
            return order

        broker_status = LiveExecutionService._normalize_order_status(broker_result.get("status"))
        filled_quantity = max(int(broker_result.get("filled_quantity") or 0), 0)
        pending_quantity = max(int(quantity) - filled_quantity, 0)

        if broker_status == OrderStatus.FILLED and filled_quantity == 0:
            filled_quantity = int(quantity)
            pending_quantity = 0

        if broker_status in {OrderStatus.PLACED, OrderStatus.PENDING} and filled_quantity > 0:
            broker_status = OrderStatus.PARTIAL_FILL if pending_quantity > 0 else OrderStatus.FILLED

        fill_price = Decimal(str(broker_result.get("avg_fill_price") or expected_price))

        # Update order with broker details
        order.broker_order_id = broker_result.get("broker_order_id", "")
        order.exchange_order_id = broker_result.get("exchange_order_id", "")
        order.status = broker_status
        order.filled_quantity = filled_quantity
        order.pending_quantity = pending_quantity
        order.avg_fill_price = fill_price if filled_quantity else None
        order.rejection_reason = broker_result.get("message") or ""
        order.executed_at = timezone.now() if broker_status in LiveExecutionService.FILLED_ORDER_STATUSES else None
        order.save()
        if broker_status in {OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED}:
            LiveExecutionService._restore_trade_phase_after_unsuccessful_order(order, broker_status)

        LiveExecutionService._create_execution_log(
            order,
            broker_status if broker_status in dict(ExecutionLog.EVENT_TYPES) else "PLACED",
            message=f"Broker order {order.broker_order_id or 'submitted'} {broker_status}",
            fill_quantity=filled_quantity,
            fill_price=fill_price if filled_quantity else None,
            latency_ms=latency_ms
        )

        LiveExecutionService._broadcast_update(order.user_id, "ORDER_UPDATE", {"order_id": order.id, "status": order.status, "filled_quantity": order.filled_quantity})

        if expected_price and filled_quantity:
            slippage_amount = abs(fill_price - expected_price)
            slippage_pct = (slippage_amount / expected_price) * Decimal("100") if expected_price else Decimal("0")
            SlippageRecord.objects.update_or_create(
                order=order,
                defaults={
                    "expected_price": expected_price,
                    "actual_price": fill_price,
                    "slippage_pct": slippage_pct,
                    "slippage_amount": slippage_amount,
                    "market_impact": slippage_amount * Decimal(str(order.filled_quantity or 0)),
                },
            )

        if broker_status in LiveExecutionService.ACTIVE_ORDER_STATUSES:
            base_inst = LiveExecutionService._get_base_instrument(order.strategy, order.instrument) if order.strategy else order.instrument
            if reduce_only:
                StrategyRuntimeState.mark_exit_pending(
                    "live",
                    session.id,
                    base_inst.id,
                )
            else:
                StrategyRuntimeState.mark_entry_pending(
                    "live",
                    session.id,
                    base_inst.id,
                    side=side,
                )

        if broker_status in LiveExecutionService.FILLED_ORDER_STATUSES and filled_quantity > 0:
            LiveExecutionService._apply_fill_to_position(order, filled_quantity, fill_price)

        # Handle Partial Fills
        if broker_status == OrderStatus.PARTIAL_FILL and settings and settings.partial_fill_action == "CANCEL_REMAINING":
            try:
                LiveExecutionService.cancel_open_order(order)
            except Exception as e:
                logger.error(f"Failed to cancel remaining quantity for partial fill: {e}")
                try:
                    NotificationService.notify(
                        user=order.user,
                        title="Partial Fill Cancel Failed",
                        message=f"Failed to cancel remaining quantity for {order.instrument.symbol} after partial fill. Position size may differ from expected.",
                        notification_type=NotificationType.RISK_ALERT,
                        severity=Severity.WARNING,
                        strategy=order.strategy,
                        data={"order_id": str(order.id), "symbol": order.instrument.symbol, "module": "live"}
                    )
                except Exception:
                    logger.exception("Failed dispatching partial fill cancel notification")

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
    def _apply_fill_to_position(order, filled_quantity=None, fill_price=None):
        opposite_side = Side.SELL if order.side == Side.BUY else Side.BUY
        opposite_position = LivePosition.objects.select_for_update().filter(
            user=order.user,
            strategy=order.strategy,
            broker_credential=order.broker_credential,
            instrument=order.instrument,
            side=opposite_side,
        ).first()
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
                strategy=order.strategy or opposite_position.strategy,
                allocation=order.allocation or opposite_position.allocation,
                broker_credential=order.broker_credential,
                instrument=order.instrument,
                exit_order=order,
                side=opposite_position.side,
                quantity=closed_qty,
                entry_price=opposite_position.avg_price,
                entry_time=opposite_position.opened_at,
                exit_price=fill_price,
                exit_time=timezone.now(),
                realized_pnl=pnl,
            )
            opposite_position.quantity -= closed_qty
            opposite_position.realized_pnl += pnl
            opposite_position.day_pnl += pnl
            opposite_position.current_price = fill_price
            opposite_position.unrealized_pnl = Decimal("0")

            # Record consecutive losses in Redis
            from risk_management.cache import RiskCache
            if pnl is not None and order.session_id:
                RiskCache.record_trade_result("LIVE", order.user_id, order.session_id, float(pnl))

            if opposite_position.quantity > 0:
                opposite_position.save(update_fields=["quantity", "realized_pnl", "day_pnl", "current_price", "unrealized_pnl", "updated_at"])
                # Initialize trade_state before conditional block to prevent NameError
                # when strategy_id is falsy (manually-placed position on partial close).
                trade_state = {}
                base_inst = LiveExecutionService._get_base_instrument(order.strategy, opposite_position.instrument)
                if opposite_position.strategy_id:
                    trade_state = StrategyRuntimeState.mark_open(
                        "live",
                        order.session_id or 0,
                        base_inst.id,
                        side=opposite_position.side,
                        quantity=opposite_position.quantity,
                        avg_price=opposite_position.avg_price,
                        config=LiveExecutionService._execution_config_for_order(order),
                        opened_at=opposite_position.opened_at,
                        execution_instrument_id=opposite_position.instrument_id,
                    )
                StrategyRuntimeState.update_position_state(
                    "live-position",
                    opposite_position.id,
                    {
                        "phase": trade_state.get("phase") if trade_state else StrategyRuntimeState.OPEN,
                        "peak_price": float(fill_price),
                        "trailing_stop": None,
                        "entry_time": trade_state.get("entry_time") if trade_state else None,
                        "protected_stop_price": trade_state.get("protected_stop_price") if trade_state else None,
                        "protected_target_price": trade_state.get("protected_target_price") if trade_state else None,
                    },
                )
                LiveExecutionService._broadcast_update(order.user_id, "POSITION_UPDATE", {"position_id": opposite_position.id, "quantity": opposite_position.quantity})
            else:
                base_inst = LiveExecutionService._get_base_instrument(order.strategy, opposite_position.instrument)
                if opposite_position.strategy_id:
                    StrategyRuntimeState.mark_closed(
                        "live",
                        order.session_id or 0,
                        base_inst.id,
                    )
                StrategyRuntimeState.clear_position_state("live-position", opposite_position.id)
                opposite_position.delete()
                LiveExecutionService._broadcast_update(order.user_id, "POSITION_UPDATE", {"position_id": opposite_position.id, "quantity": 0})
            session = order.session.__class__.objects.select_for_update().get(id=order.session_id)
            session.trades_count += 1
            session.pnl += pnl
            session.save(update_fields=["trades_count", "pnl", "updated_at"])

            # Update Global Portfolio Realized PnL + Peak Tracking
            portfolio = LivePortfolioService.get_or_create_portfolio(order.user)
            portfolio = portfolio.__class__.objects.select_for_update().get(id=portfolio.id)
            portfolio.realized_pnl += pnl
            portfolio.today_pnl += pnl
            portfolio.today_trades += 1

            # Update invested_value and unrealized_pnl for accurate drawdown
            portfolio.invested_value = LivePortfolioService.calculate_invested_value(portfolio)
            portfolio.unrealized_pnl = LivePortfolioService.calculate_unrealized_pnl(portfolio)

            # Peak value / drawdown tracking
            if portfolio.total_value > portfolio.peak_value:
                portfolio.peak_value = portfolio.total_value
                portfolio.peak_date = timezone.localdate()

            portfolio.save(update_fields=[
                "realized_pnl", "today_pnl", "today_trades",
                "invested_value", "unrealized_pnl",
                "peak_value", "peak_date", "updated_at",
            ])

            # Sync Capital Allocation P&L for this strategy
            if order.allocation_id:
                allocation = order.allocation.__class__.objects.select_for_update().get(id=order.allocation_id)
                allocation.utilized_amount = LivePortfolioService._live_allocation_utilized(allocation)
                allocation.total_pnl += pnl
                allocation.today_pnl += pnl
                allocation.realized_pnl += pnl
                allocation.save(update_fields=["utilized_amount", "total_pnl", "today_pnl", "realized_pnl", "updated_at"])

            remaining -= closed_qty

        # Refresh Risk Cache
        from risk_management.cache import RiskCache
        if order.session_id:
            RiskCache.sync_on_fill("LIVE", order.session_id)
            session = order.session
            if session and session.allocation:
                from risk_management.auto_disable import AutoDisableGate
                stats = RiskCache.get_stats("LIVE", order.user_id, order.session_id)
                AutoDisableGate.evaluate(session, stats, session.allocation.allocated_capital)

        if remaining > 0:
            from django.db import transaction
            with transaction.atomic():
                position = LivePosition.objects.select_for_update().filter(
                    user=order.user,
                    strategy=order.strategy,
                    broker_credential=order.broker_credential,
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
                        source_type=order.source_type,
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
            base_inst = LiveExecutionService._get_base_instrument(order.strategy, order.instrument) if order.strategy else order.instrument
            trade_state = StrategyRuntimeState.mark_open(
                "live",
                order.session_id or 0,
                base_inst.id,
                side=position.side,
                quantity=position.quantity,
                avg_price=position.avg_price,
                config=LiveExecutionService._execution_config_for_order(order),
                opened_at=position.opened_at,
                execution_instrument_id=order.instrument_id,
            ) if order.strategy_id else {}
            StrategyRuntimeState.update_position_state(
                "live-position",
                position.id,
                {
                    "phase": trade_state.get("phase") if trade_state else StrategyRuntimeState.OPEN,
                    "peak_price": float(fill_price),
                    "trailing_stop": None,
                    "entry_time": trade_state.get("entry_time") if trade_state else None,
                    "protected_stop_price": trade_state.get("protected_stop_price") if trade_state else None,
                    "protected_target_price": trade_state.get("protected_target_price") if trade_state else None,
                },
            )
            LiveExecutionService._broadcast_update(order.user_id, "POSITION_UPDATE", {"position_id": position.id, "quantity": position.quantity})
        if order.allocation_id:
            LiveExecutionService._sync_allocation_wallet(order.allocation)

        from live_trading.cache import LiveBrokerStateCache
        LiveBrokerStateCache.invalidate_on_fill(order.user_id, order.broker_credential_id)

    @staticmethod
    def _sync_order_from_row(order, row):
        previous_status = order.status
        previous_filled = int(order.filled_quantity or 0)
        broker_status = LiveExecutionService._normalize_order_status(
            row.get("status") or row.get("orderStatus") or row.get("orderNumStatus")
        )
        new_filled = max(
            int(
                row.get("filledQty")
                or row.get("filled_quantity")
                or row.get("tradedQty")
                or row.get("filledqty")
                or previous_filled
                or 0
            ),
            0,
        )
        total_quantity = int(row.get("qty") or row.get("quantity") or order.quantity or 0)
        pending_quantity = row.get("remainingQuantity") or row.get("pending_quantity")
        if pending_quantity is None:
            pending_quantity = max(total_quantity - new_filled, 0)
        else:
            pending_quantity = max(int(pending_quantity), 0)

        fill_price_raw = (
            row.get("tradedPrice")
            or row.get("avgPrice")
            or row.get("avg_fill_price")
            or order.avg_fill_price
            or order.price
        )
        fill_price = Decimal(str(fill_price_raw or 0)) if fill_price_raw is not None else None
        delta_fill = max(new_filled - previous_filled, 0)

        update_fields = ["status", "filled_quantity", "pending_quantity", "updated_at"]
        order.status = broker_status
        order.filled_quantity = new_filled
        order.pending_quantity = pending_quantity
        if new_filled and fill_price is not None:
            order.avg_fill_price = fill_price
            update_fields.append("avg_fill_price")
        if broker_status in LiveExecutionService.FILLED_ORDER_STATUSES and not order.executed_at:
            order.executed_at = timezone.now()
            update_fields.append("executed_at")
        if broker_status == OrderStatus.CANCELLED and not order.cancelled_at:
            order.cancelled_at = timezone.now()
            update_fields.append("cancelled_at")
        rejection_reason = row.get("message") or row.get("reason") or ""
        if rejection_reason and rejection_reason != order.rejection_reason:
            order.rejection_reason = rejection_reason
            update_fields.append("rejection_reason")
        order.save(update_fields=update_fields)

        if broker_status != previous_status or delta_fill > 0:
            LiveExecutionService._broadcast_update(order.user_id, "ORDER_UPDATE", {"order_id": order.id, "status": order.status, "filled_quantity": order.filled_quantity})
            LiveExecutionService._create_execution_log(
                order,
                broker_status if broker_status in dict(ExecutionLog.EVENT_TYPES) else "ACKNOWLEDGED",
                message=f"Broker lifecycle update: {broker_status}",
                fill_quantity=delta_fill,
                fill_price=fill_price if delta_fill else None,
            )

        if previous_status != broker_status:
            OrderReconciliation.objects.create(
                user=order.user,
                broker_order_id=order.broker_order_id or order.exchange_order_id or str(order.id),
                internal_order_id=str(order.id),
                broker_status=broker_status,
                internal_status=previous_status,
                discrepancy_type="STATUS_MISMATCH",
                resolved=broker_status == previous_status,
                notes="Broker sync updated live order status.",
            )
            if broker_status in {OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED}:
                LiveExecutionService._restore_trade_phase_after_unsuccessful_order(order, broker_status)

        if delta_fill > 0:
            LiveExecutionService._apply_fill_to_position(order, filled_quantity=delta_fill, fill_price=fill_price)
            if order.price and fill_price is not None:
                slippage_amount = abs(fill_price - Decimal(str(order.price)))
                slippage_pct = (slippage_amount / Decimal(str(order.price))) * Decimal("100") if order.price else Decimal("0")
                SlippageRecord.objects.update_or_create(
                    order=order,
                    defaults={
                        "expected_price": Decimal(str(order.price)),
                        "actual_price": fill_price,
                        "slippage_pct": slippage_pct,
                        "slippage_amount": slippage_amount,
                        "market_impact": slippage_amount * Decimal(str(new_filled)),
                    },
                )

        session = order.session
        settings_obj = getattr(session.broker_credential, 'order_settings', None)
        if (
            order.status == OrderStatus.PARTIAL_FILL
            and order.pending_quantity > 0
            and settings_obj
            and settings_obj.partial_fill_action == "CANCEL_REMAINING"
        ):
            LiveExecutionService.cancel_open_order(order)

        return order

    @staticmethod
    def sync_open_orders(session, symbol=None, force=False):
        query = LiveOrder.objects.filter(session=session, status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES).select_related("instrument")
        if symbol:
            query = query.filter(instrument__sym_ticker=MarketDataStreamer.normalize_symbol(symbol))
        orders = list(query)
        if not orders:
            return []

        cache_key = LiveExecutionService._session_sync_cache_key(session.id)
        if not force and cache.get(cache_key):
            return orders
        cache.set(cache_key, True, timeout=LiveExecutionService.ORDERBOOK_SYNC_TTL_SECONDS)

        orderbook = BrokerService.get_orderbook(session.broker_credential)
        rows = LiveExecutionService._extract_orderbook_rows(orderbook)
        synced = []
        for order in orders:
            row = LiveExecutionService._match_broker_order_row(order, rows)
            synced.append(LiveExecutionService._sync_order_from_row(order, row) if row else order)
        return synced

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
                instrument_id = getattr(req, "instrument_id", "unknown")
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
    @transaction.atomic
    def sync_account_state(user, credential=None, force=False):
        credential = credential or BrokerCredential.objects.filter(user=user, is_active=True).first()
        if not credential:
            return {"funds": {}, "positions": 0, "orders": 0}
        funds = LiveExecutionService._sync_funds_from_broker(credential, force=force)
        positions = LiveExecutionService.sync_positions_from_broker(user, credential=credential, force=force)
        orders = LiveExecutionService.sync_orders_from_broker(user, credential=credential, force=force)
        LiveExecutionService._refresh_broker_allocation_health(user, credential)
        portfolio = LivePortfolioService.get_or_create_portfolio(user)
        portfolio.save(update_fields=["updated_at"])
        return {"funds": funds, "positions": positions, "orders": orders}

    @staticmethod
    def rebuild_runtime_state_from_db():
        """Initialize and recover Redis runtime state from DB positions on startup."""
        from strategy_engine.runtime import StrategyRuntimeState
        from risk_management.cache import RiskCache
        from live_trading.models import TradingSession

        active_positions = LivePosition.objects.filter(quantity__gt=0).select_related('strategy', 'instrument', 'user', 'allocation')
        recovered = 0
        sessions_seen = set()

        for pos in active_positions:
            if not pos.strategy_id:
                continue
            session_id = None
            if pos.allocation:
                session_id = TradingSession.objects.filter(
                    strategy_id=pos.allocation.strategy_id, 
                    broker_credential_id=pos.allocation.broker_credential_id
                ).values_list('id', flat=True).first()
            base_inst = LiveExecutionService._get_base_instrument(pos.strategy, pos.instrument)
            state = StrategyRuntimeState.trade_state("live", session_id or 0, base_inst.id)
            if state.get("phase") != StrategyRuntimeState.OPEN:
                config = pos.allocation.deployed_version.config_snapshot if pos.allocation and pos.allocation.deployed_version_id else pos.strategy.to_execution_dict()
                StrategyRuntimeState.mark_open(
                    "live",
                    session_id or 0,
                    base_inst.id,
                    side=pos.side,
                    quantity=pos.quantity,
                    avg_price=pos.avg_price,
                    config=config,
                    opened_at=pos.opened_at,
                    execution_instrument_id=pos.instrument_id,
                )
                recovered += 1
            if session_id:
                sessions_seen.add(session_id)

        for session_id in sessions_seen:
            try:
                RiskCache.sync_from_db("LIVE", session_id)
            except Exception:
                logger.exception("Failed to rehydrate risk cache for live session %s", session_id)

        if recovered > 0:
            logger.info("Recovered %s missing runtime states from live DB positions.", recovered)

    @staticmethod
    @transaction.atomic
    def sync_positions_from_broker(user, strategy=None, credential=None, force=False):
        credential = credential or BrokerCredential.objects.filter(user=user, is_active=True).first()
        if not credential:
            return 0

        try:
            broker_data = BrokerService.get_positions(credential)
            if broker_data.get("s") != "ok":
                return 0
            normalized = LiveExecutionService._normalize_broker_position_rows(broker_data)
            LiveBrokerStateCache.set_positions_state(
                user.id,
                credential.id,
                [
                    {
                        "symbol": row["symbol"],
                        "side": row["side"],
                        "quantity": row["quantity"],
                        "avg_price": str(row["avg_price"]),
                        "current_price": str(row["current_price"]),
                        "unrealized_pnl": str(row["unrealized_pnl"]),
                        "realized_pnl": str(row["realized_pnl"]),
                    }
                    for row in normalized
                ],
            )

            broker_keys = set()
            synced = 0
            for row in normalized:
                instrument = LiveExecutionService._resolve_instrument_from_broker_symbol(row["symbol"])
                if not instrument:
                    continue
                broker_keys.add((instrument.id, row["side"]))
                strategy_positions = list(
                    LivePosition.objects.filter(
                        user=user,
                        broker_credential=credential,
                        instrument=instrument,
                        side=row["side"],
                    ).exclude(strategy__isnull=True).order_by("opened_at", "id")
                )
                remaining_broker_qty = int(row["quantity"])
                for position in strategy_positions:
                    if remaining_broker_qty <= 0:
                        logger.warning(
                            "Phantom position detected: Local position %s (qty %s) for %s exists, but broker reports 0 or insufficient quantity. Deleting local position to sync.",
                            position.id, position.quantity, instrument.sym_ticker
                        )
                        LiveExecutionService._create_execution_log(
                            None, "WARNING",
                            message=f"Phantom position detected & deleted for {instrument.sym_ticker} (qty {position.quantity}). Broker reported 0.",
                            user_id=user.id, broker_credential_id=credential.id
                        )
                        try:
                            NotificationService.notify(
                                user,
                                title="Phantom live position detected",
                                message=f"Broker reports no remaining quantity for {instrument.sym_ticker}; internal position {position.id} was reconciled.",
                                severity=Severity.CRITICAL,
                                strategy=position.strategy,
                                data={
                                    "position_id": position.id,
                                    "instrument_id": position.instrument_id,
                                    "broker_credential_id": credential.id,
                                    "phantom_position": True,
                                },
                            )
                        except Exception:
                            logger.exception("Failed dispatching phantom position alert for position %s", position.id)
                        position.delete()
                        continue
                    assigned_qty = min(position.quantity, remaining_broker_qty)
                    position.quantity = assigned_qty
                    position.current_price = row["current_price"]
                    position.unrealized_pnl = (
                        (row["current_price"] - position.avg_price) * assigned_qty
                        if position.side == Side.BUY
                        else (position.avg_price - row["current_price"]) * assigned_qty
                    )
                    position.day_pnl = position.realized_pnl + position.unrealized_pnl
                    position.last_broker_sync = timezone.now()
                    position.save(update_fields=["quantity", "current_price", "unrealized_pnl", "day_pnl", "last_broker_sync", "updated_at"])
                    remaining_broker_qty -= assigned_qty

                if remaining_broker_qty > 0:
                    external_position, _ = LivePosition.objects.update_or_create(
                        user=user,
                        strategy=None,
                        broker_credential=credential,
                        instrument=instrument,
                        side=row["side"],
                        defaults={
                            "allocation": None,
                            "source_type": "EXTERNAL",
                            "product_type": ProductType.INTRADAY,
                            "quantity": remaining_broker_qty,
                            "avg_price": row["avg_price"],
                            "current_price": row["current_price"],
                            "unrealized_pnl": row["unrealized_pnl"],
                            "realized_pnl": row["realized_pnl"],
                            "day_pnl": row["realized_pnl"] + row["unrealized_pnl"],
                            "last_broker_sync": timezone.now(),
                        },
                    )
                    synced += 1
                else:
                    LivePosition.objects.filter(
                        user=user,
                        strategy=None,
                        broker_credential=credential,
                        instrument=instrument,
                        side=row["side"],
                    ).delete()
                synced += 1

            local_positions = LivePosition.objects.filter(
                user=user,
                broker_credential=credential,
            ).exclude(strategy__isnull=True).select_related("strategy", "instrument")
            for position in local_positions:
                if position.quantity <= 0:
                    continue
                position_key = (position.instrument_id, position.side)
                if position_key not in broker_keys:
                    logger.warning(
                        "Phantom position detected: Local position %s (qty %s) for %s exists, but broker reports no matching position. Deleting local position to sync.",
                        position.id,
                        position.quantity,
                        position.instrument.sym_ticker,
                    )
                    LiveExecutionService._create_execution_log(
                        None,
                        "WARNING",
                        message=f"Phantom position detected & deleted for {position.instrument.sym_ticker} (qty {position.quantity}). Broker reported no matching position.",
                        user_id=user.id,
                        broker_credential_id=credential.id,
                    )
                    try:
                        NotificationService.notify(
                            user,
                            title="Phantom live position detected",
                            message=f"Broker reports no matching position for {position.instrument.sym_ticker}; internal position {position.id} was reconciled.",
                            severity=Severity.CRITICAL,
                            strategy=position.strategy,
                            data={
                                "position_id": position.id,
                                "instrument_id": position.instrument_id,
                                "broker_credential_id": credential.id,
                                "phantom_position": True,
                            },
                        )
                    except Exception:
                        logger.exception("Failed dispatching phantom position alert for position %s", position.id)
                    position.delete()

            stale_external = LivePosition.objects.filter(
                user=user,
                strategy=None,
                broker_credential=credential,
                source_type="EXTERNAL",
            )
            for position in stale_external:
                if (position.instrument_id, position.side) not in broker_keys:
                    position.delete()

            for allocation in LiveStrategyAllocation.objects.filter(user=user, broker_credential=credential):
                LiveExecutionService._sync_allocation_wallet(allocation)
            return synced
        except Exception as e:
            logger.exception("Failed syncing positions for user %s: %s", user.id, e)
            try:
                NotificationService.notify(
                    user=user,
                    title="Position Sync Failed",
                    message="Failed to sync positions with broker. Portfolio positions may be out of sync. Will retry automatically.",
                    notification_type=NotificationType.SYSTEM_ALERT,
                    severity=Severity.WARNING,
                    data={"module": "live", "error": str(e)}
                )
            except Exception:
                logger.exception("Failed dispatching position sync failure notification")
            return 0

    @staticmethod
    @transaction.atomic
    def sync_orders_from_broker(user, credential=None, force=False):
        credential = credential or BrokerCredential.objects.filter(user=user, is_active=True).first()
        if not credential:
            return 0

        try:
            broker_data = BrokerService.get_orderbook(credential)
            if broker_data.get("s") not in (None, "ok") and broker_data.get("status") not in (None, "ok"):
                reason = str(broker_data)
                LiveExecutionService._alert_stale_pending_orders(user, credential, reason)
                LiveExecutionService._auto_cancel_stale_pending_orders(user, credential, reason)
                return 0
            rows = LiveExecutionService._normalize_broker_order_rows(broker_data)
            LiveBrokerStateCache.set_orders_state(
                user.id,
                credential.id,
                [
                    {
                        "broker_order_id": row["broker_order_id"],
                        "exchange_order_id": row["exchange_order_id"],
                        "symbol": row["symbol"],
                        "side": row["side"],
                        "quantity": row["quantity"],
                        "filled_quantity": row["filled_quantity"],
                        "pending_quantity": row["pending_quantity"],
                        "price": str(row["price"]),
                        "status": row["status"],
                    }
                    for row in rows
                ],
            )
            if not rows:
                return 0

            synced = 0
            active_orders = LiveOrder.objects.filter(user=user, status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES)
            for order in active_orders:
                match = LiveExecutionService._match_broker_order_row(order, [item["raw"] for item in rows])
                if match is not None:
                    LiveExecutionService._sync_order_from_row(order, match)
                    synced += 1

            internal_ids = {
                value
                for value in LiveOrder.objects.filter(user=user, broker_credential=credential).values_list("broker_order_id", flat=True)
                if value
            }
            for row in rows:
                if not row["broker_order_id"] or row["broker_order_id"] in internal_ids:
                    continue
                instrument = LiveExecutionService._resolve_instrument_from_broker_symbol(row["symbol"])
                if not instrument:
                    continue
                LiveOrder.objects.update_or_create(
                    user=user,
                    broker_credential=credential,
                    broker_order_id=row["broker_order_id"],
                    defaults={
                        "strategy": None,
                        "session": None,
                        "allocation": None,
                        "portfolio": LivePortfolioService.get_or_create_portfolio(user),
                        "exchange_order_id": row["exchange_order_id"],
                        "instrument": instrument,
                        "source_type": "EXTERNAL",
                        "reduce_only": False,
                        "requested_value": Decimal(str(row["price"])) * Decimal(str(row["quantity"] or 0)),
                        "order_type": OrderType.MARKET,
                        "product_type": ProductType.INTRADAY,
                        "side": Side.BUY if row["side"] == "BUY" else Side.SELL,
                        "price": row["price"],
                        "quantity": row["quantity"],
                        "filled_quantity": row["filled_quantity"],
                        "pending_quantity": row["pending_quantity"],
                        "avg_fill_price": row["price"] if row["filled_quantity"] else None,
                        "status": row["status"],
                    },
                )
                synced += 1
            return synced
        except Exception as e:
            logger.exception("Failed syncing orders for user %s: %s", user.id, e)
            reason = str(e)
            LiveExecutionService._alert_stale_pending_orders(user, credential, reason)
            LiveExecutionService._auto_cancel_stale_pending_orders(user, credential, reason)
            return 0

    @staticmethod
    def session_summary(user):
        sessions = TradingSession.objects.filter(user=user).select_related("strategy", "broker_credential")
        positions = LivePosition.objects.filter(user=user)
        orders = LiveOrder.objects.filter(user=user)
        active_sessions = sessions.filter(status="RUNNING")
        open_orders = orders.filter(status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES)
        today_orders = orders.filter(placed_at__date=timezone.localdate())
        active_credentials = BrokerCredential.objects.filter(user=user, is_active=True)
        broker_summaries = []
        for credential in active_credentials:
            funds_state = LiveBrokerStateCache.get_funds_state(user.id, credential.id)
            funds_payload = (funds_state or {}).get("payload") or {}
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
                    "credential_id": credential.id,
                    "broker_name": credential.broker_name,
                    "broker_label": credential.label,
                    "is_healthy": account_healthy,
                    "broker_session_valid": session_valid,
                    "available_margin": str(LiveExecutionService._to_decimal(funds_payload.get("available_margin"))),
                    "used_margin": str(LiveExecutionService._to_decimal(funds_payload.get("used_margin"))),
                    "net_equity": str(LiveExecutionService._to_decimal(funds_payload.get("net_equity"))),
                    "cash_balance": str(LiveExecutionService._to_decimal(funds_payload.get("cash_balance"))),
                    "allocations": [
                        {
                            "id": row.id,
                            "strategy_id": row.strategy_id,
                            "strategy_name": row.strategy.name,
                            "allocated_capital": str(row.allocated_capital),
                            "used_capital": str(row.used_capital),
                            "available_capital": str(row.available_capital),
                            "is_over_allocated": row.is_over_allocated,
                            "breach_reason": row.breach_reason,
                        }
                        for row in allocation_rows
                    ],
                }
            )

        return {
            "total_sessions": sessions.count(),
            "running_sessions": active_sessions.count(),
            "paused_sessions": sessions.filter(status="PAUSED").count(),
            "error_sessions": sessions.filter(status="ERROR").count(),
            "open_positions": positions.count(),
            "open_orders": open_orders.count(),
            "today_orders": today_orders.count(),
            "today_fills": today_orders.filter(status__in=LiveExecutionService.FILLED_ORDER_STATUSES).count(),
            # Use DB-level aggregation instead of Python iteration to avoid N+1.
            "unrealized_pnl": str(positions.aggregate(s=Sum("unrealized_pnl"))["s"] or Decimal("0")),
            "realized_pnl": str(sessions.aggregate(s=Sum("pnl"))["s"] or Decimal("0")),
            "day_pnl": str(
                (positions.aggregate(s=Sum("unrealized_pnl"))["s"] or Decimal("0"))
                + (sessions.aggregate(s=Sum("pnl"))["s"] or Decimal("0"))
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
