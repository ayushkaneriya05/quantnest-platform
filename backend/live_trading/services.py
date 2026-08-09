from concurrent.futures import ThreadPoolExecutor
import logging
from decimal import Decimal

from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from brokers.models import BrokerCredential, BrokerFundsSnapshot, OrderReconciliation, OrderSettings
from brokers.services import BrokerService
from rules_engine.utils import compute_sl_distance_from_config
from common.enums import CapitalAllocationType, OrderStatus, OrderType, ProductType, Severity, Side, StrategyStatus, ViolationAction, ViolationType
from instruments.models import WatchlistInstrument
from marketdata.access import StrategyMarketDataService
from marketdata.streaming import MarketDataStreamer
from notifications.services import NotificationService
from paper_trading.services import PaperStrategyEngine
from risk_management.evaluator import RiskEvaluator
from risk_management.models import PortfolioRiskProfile, RiskViolation

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from strategy_engine.executor import StrategyExecutor
from strategy_engine.runtime import StrategyRuntimeState
from .cache import LiveBrokerStateCache
from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, SlippageRecord, TradingSession, LivePortfolio

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
    _execution_pool = ThreadPoolExecutor(max_workers=32, thread_name_prefix="live_exec")

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
    def _record_violation(
        user,
        strategy,
        violation_type,
        message,
        threshold_value=None,
        actual_value=None,
        action_taken=ViolationAction.BLOCKED,
        severity=Severity.WARNING,
    ):
        RiskViolation.objects.create(
            user=user,
            strategy=strategy,
            violation_type=violation_type,
            severity=severity,
            message=message,
            threshold_value=threshold_value,
            actual_value=actual_value,
            action_taken=action_taken,
        )
        try:
            NotificationService.notify(
                user,
                title="Live risk alert",
                message=message,
                strategy=strategy,
                severity=severity,
            )
        except Exception:
            logger.exception("Failed dispatching live risk notification")

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
    def _latest_funds_snapshot(credential):
        return BrokerFundsSnapshot.objects.filter(credential=credential).order_by("-snapshot_time", "-created_at").first()

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
                is_active=True,
            ).select_related("strategy")
        )
        total_allocated = sum((Decimal(str(item.allocated_capital or 0)) for item in allocations), Decimal("0"))
        for allocation in allocations:
            if allocation.allocation_type == CapitalAllocationType.PERCENTAGE and broker_equity > 0:
                allocation.allocated_capital = (Decimal(str(allocation.allocated_percentage or 0)) / Decimal("100")) * broker_equity
            allocation.broker_equity_reference = broker_equity
        total_allocated = sum((Decimal(str(item.allocated_capital or 0)) for item in allocations), Decimal("0"))
        for allocation in allocations:
            allocation.broker_equity_reference = broker_equity
            allocation.is_over_allocated = broker_equity > 0 and total_allocated > broker_equity
            allocation.breach_reason = (
                f"Allocated capital {total_allocated} exceeds broker equity {broker_equity}"
                if allocation.is_over_allocated
                else ""
            )
            allocation.save(update_fields=["allocated_capital", "broker_equity_reference", "is_over_allocated", "breach_reason", "updated_at"])
            LiveExecutionService._sync_allocation_wallet(allocation)
        return allocations

    @staticmethod
    def _resolve_live_allocation(user, strategy, credential, allocation_amount=None, allocation_percentage=None):
        portfolio = LivePortfolioService.get_or_create_portfolio(user)
        capital_allocation = None
        try:
            capital_allocation = portfolio.live_allocations.filter(strategy=strategy).first()
        except Exception:
            capital_allocation = None

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
        elif capital_allocation:
            allocation_type = capital_allocation.allocation_type
            if allocation_type == CapitalAllocationType.PERCENTAGE:
                allocated_percentage = Decimal(str(capital_allocation.allocated_percentage or 0))
                allocated_capital = capital_allocation.effective_allocated
            else:
                allocated_capital = Decimal(str(capital_allocation.allocated_amount or 0))
                allocated_percentage = Decimal("0")
        else:
            raise ValueError("Live deployment requires a broker capital allocation amount or percentage")

        if allocated_capital <= 0:
            raise ValueError("Allocated capital must be greater than zero")

        existing = list(
            LiveStrategyAllocation.objects.filter(
                user=user,
                broker_credential=credential,
                is_active=True,
            ).exclude(strategy=strategy)
        )
        total_other = sum((Decimal(str(item.allocated_capital or 0)) for item in existing), Decimal("0"))
        if broker_equity > 0 and total_other + allocated_capital > broker_equity:
            raise ValueError(
                f"Live allocation exceeds broker equity. Requested={allocated_capital}, already allocated={total_other}, broker equity={broker_equity}"
            )

        allocation, _ = LiveStrategyAllocation.objects.update_or_create(
            user=user,
            strategy=strategy,
            broker_credential=credential,
            defaults={
                "portfolio": portfolio,
                "allocation_type": allocation_type,
                "allocated_capital": allocated_capital,
                "allocated_percentage": allocated_percentage or Decimal("0"),
                "available_capital": allocated_capital,
                "broker_equity_reference": broker_equity,
                "is_active": True,
                "is_over_allocated": False,
                "breach_reason": "",
            },
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
            user=user,
            strategy=strategy,
            defaults={
                "broker_credential": credential,
                "status": "RUNNING",
                "started_at": timezone.now(),
                "ended_at": None,
                "error_message": "",
            },
        )

        # Risk state is warmed for fast execution. Strategy execution config is
        # read from the allocation's deployed StrategyVersion when pinned.
        from risk_management.cache import RiskCache
        RiskCache.sync_from_db(user, strategy)

        LiveExecutionService._sync_allocation_wallet(allocation)
        LiveExecutionService._broadcast_update(user.id, "SESSION_UPDATE", {"session_id": session.id, "status": session.status})
        LiveExecutionService._update_routing_cache(session, add=True)
        return session

    @staticmethod
    @transaction.atomic
    def update_allocation(user, strategy, credential, allocation_amount=None, allocation_percentage=None):
        allocation = LiveExecutionService._resolve_live_allocation(
            user,
            strategy,
            credential,
            allocation_amount=allocation_amount,
            allocation_percentage=allocation_percentage,
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

        session.status = "PAUSED"
        session.error_message = ""
        session.save(update_fields=["status", "error_message", "updated_at"])
        LiveExecutionService._broadcast_update(session.user_id, "SESSION_UPDATE", {"session_id": session.id, "status": session.status})
        LiveExecutionService._update_routing_cache(session, add=False)
        return session

    @staticmethod
    @transaction.atomic
    def stop_session(session, close_positions=False):
        for order in LiveOrder.objects.filter(session=session, status__in=LiveExecutionService.ACTIVE_ORDER_STATUSES):
            try:
                LiveExecutionService.cancel_open_order(order)
            except Exception:
                logger.exception("Failed cancelling live order %s during session stop", order.id)
        if close_positions:
            for position in LivePosition.objects.filter(user=session.user, strategy=session.strategy, broker_credential=session.broker_credential):
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
        session.status = "STOPPED"
        session.ended_at = timezone.now()
        session.error_message = ""
        session.save(update_fields=["status", "ended_at", "error_message", "updated_at"])
        LiveExecutionService._broadcast_update(session.user_id, "SESSION_UPDATE", {"session_id": session.id, "status": session.status})
        LiveExecutionService._update_routing_cache(session, add=False)
        return session

    @staticmethod
    @transaction.atomic
    def resume_session(session):
        BrokerService.ensure_session(session.broker_credential)
        session.status = "RUNNING"
        session.error_message = ""
        session.save(update_fields=["status", "error_message", "updated_at"])
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
                trade_state = StrategyRuntimeState.mark_open(
                    "live",
                    order.strategy_id,
                    order.instrument_id,
                    position_id=position.id,
                    side=position.side,
                    quantity=position.quantity,
                    avg_price=position.avg_price,
                    config=LiveExecutionService._execution_config_for_order(order),
                    opened_at=position.opened_at,
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
        StrategyRuntimeState.mark_closed(
            "live",
            order.strategy_id,
            order.instrument_id,
            reason=f"Order {status.lower()}",
        )

    @staticmethod
    def _resolve_price(instrument, fallback_price=None):
        try:
            return StrategyMarketDataService.get_quote(instrument, fallback_price=fallback_price)
        except ValueError:
            return Decimal(str(instrument.previous_close or 0))

    @staticmethod
    def _risk_stats(user, strategy, instrument, quantity, price):
        from datetime import timedelta
        from paper_trading.models import DailyPerformance

        strategy_positions = LivePosition.objects.filter(user=user, strategy=strategy)
        broker_credential = (
            TradingSession.objects.filter(user=user, strategy=strategy, status__in=["RUNNING", "PAUSED", "ERROR"])
            .values_list("broker_credential_id", flat=True)
            .first()
        )
        positions_state = LiveBrokerStateCache.get_positions_state(user.id, broker_credential) if broker_credential else {}
        broker_positions = (positions_state or {}).get("payload") or []
        portfolio = LivePortfolioService.get_or_create_portfolio(user)
        exposure = sum(
            (
                LiveExecutionService._to_decimal(pos.get("current_price") or pos.get("avg_price"))
                * Decimal(str(pos.get("quantity") or 0))
                for pos in broker_positions
            ),
            Decimal("0"),
        )
        strategy_exposure = sum(
            (Decimal(str(pos.current_price or pos.avg_price)) * pos.quantity for pos in strategy_positions),
            Decimal("0"),
        )
        instrument_exposure = sum(
            (
                LiveExecutionService._to_decimal(pos.get("current_price") or pos.get("avg_price"))
                * Decimal(str(pos.get("quantity") or 0))
                for pos in broker_positions
                if pos.get("symbol") == instrument.sym_ticker
            ),
            Decimal("0"),
        )
        payload_exposure = Decimal(str(quantity)) * Decimal(str(price))
        if quantity:
            exposure += payload_exposure
            strategy_exposure += payload_exposure
            instrument_exposure += payload_exposure
        funds_state = LiveBrokerStateCache.get_funds_state(user.id, broker_credential) if broker_credential else {}
        funds_payload = (funds_state or {}).get("payload") or {}
        broker_equity = LiveExecutionService._to_decimal(
            funds_payload.get("net_equity") or funds_payload.get("available_margin") or portfolio.total_value or 0
        )
        portfolio_value = float(broker_equity or portfolio.total_value or portfolio.current_capital or 0)
        daily_pnl = float(portfolio.today_pnl or 0)

        today = timezone.localdate()
        entry_config = getattr(strategy, "entry_order_config", None)
        entry_side = getattr(entry_config, "entry_side", Side.BUY) if entry_config else Side.BUY
        exit_side = Side.SELL if entry_side == Side.BUY else Side.BUY

        # Count completed trade exits, not raw entry+exit orders.
        completed_trade_query = LiveOrder.objects.filter(
            user=user,
            strategy=strategy,
            status__in=LiveExecutionService.FILLED_ORDER_STATUSES,
            side=exit_side,
        ).exclude(executed_at__isnull=True)

        from risk_management.cache import RiskCache
        consecutive_losses = RiskCache.get_stats(user.id, strategy.id).get("consecutive_losses", 0)

        # Weekly and monthly PnL from daily performance records
        weekly_pnl = float(
            DailyPerformance.objects.filter(
                portfolio=portfolio, date__gte=today - timedelta(days=7),
            ).aggregate(v=Sum("total_pnl"))["v"] or 0
        )
        monthly_pnl = float(
            DailyPerformance.objects.filter(
                portfolio=portfolio, date__gte=today - timedelta(days=30),
            ).aggregate(v=Sum("total_pnl"))["v"] or 0
        )

        return {
            "open_positions": strategy_positions.count(),
            "daily_trades": completed_trade_query.filter(executed_at__date=today).count(),
            "daily_pnl": daily_pnl,
            "total_exposure": float(exposure),
            "drawdown": float(portfolio.current_drawdown or 0),
            "strategy_allocation_pct": (float(strategy_exposure) / portfolio_value * 100) if portfolio_value > 0 else 0,
            "instrument_exposure_pct": (float(instrument_exposure) / portfolio_value * 100) if portfolio_value > 0 else 0,
            "consecutive_losses": consecutive_losses,
            "max_consecutive_losses": 0,
            "weekly_pnl": weekly_pnl,
            "monthly_pnl": monthly_pnl,
            "broker_equity": float(broker_equity),
            "available_margin": float(LiveExecutionService._to_decimal(funds_payload.get("available_margin"))),
            "used_margin": float(LiveExecutionService._to_decimal(funds_payload.get("used_margin"))),
        }

    @staticmethod
    def _get_active_allocation(session):
        return LiveStrategyAllocation.objects.filter(
            user=session.user,
            strategy=session.strategy,
            broker_credential=session.broker_credential,
        ).first()

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

        entry_config = getattr(session.strategy, "entry_order_config", None)
        allow_partial = bool(getattr(entry_config, "allow_partial_entry", False)) if entry_config else False

        if allocation.available_capital < required_capital or available_margin < required_capital:
            if allow_partial and price:
                cap = min(Decimal(str(allocation.available_capital)), available_margin)
                lot_size = instrument.lot_size or 1
                if lot_size > 1:
                    max_lots = int(cap / (Decimal(str(price)) * Decimal(str(lot_size))))
                    adjusted_qty = max(max_lots, 0) * lot_size
                else:
                    adjusted_qty = int(cap / Decimal(str(price)))

                if adjusted_qty >= max(lot_size, 1):
                    required_capital = LiveExecutionService._estimate_required_capital(adjusted_qty, price)
                    return allocation, required_capital, adjusted_qty
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
        portfolio = LivePortfolioService.get_or_create_portfolio(session.user)
        evaluator = RiskEvaluator(portfolio.total_value or portfolio.current_capital or 0)
        stats = LiveExecutionService._risk_stats(session.user, session.strategy, instrument, quantity, price)
        ok, msg = evaluator.check_strategy_limits(session.strategy, stats)
        if not ok:
            LiveExecutionService._record_violation(
                session.user,
                session.strategy,
                ViolationType.MAX_TRADES if "daily trades" in msg.lower() else ViolationType.POSITION_SIZE,
                f"Live strategy blocked: {msg}",
            )
            raise ValueError(msg)

        profile = PortfolioRiskProfile.objects.filter(user=session.user).first()
        portfolio_eval = evaluator.evaluate_portfolio_risk(profile, stats)
        if portfolio_eval.get("breached"):
            breach = (portfolio_eval.get("breaches") or [{}])[0]
            LiveExecutionService._record_violation(
                session.user,
                session.strategy,
                breach.get("violation_type") or ViolationType.EXPOSURE,
                f"Live portfolio risk violation: {breach.get('message', 'Portfolio risk breached')}",
                threshold_value=breach.get("threshold_value"),
                actual_value=breach.get("actual_value"),
                action_taken=ViolationAction.BLOCKED,
                severity=breach.get("severity") or Severity.CRITICAL,
            )
            raise ValueError(breach.get("message", "Portfolio risk breached"))

        strategy_stats = {
            **stats,
            "open_positions": LivePosition.objects.filter(user=session.user, strategy=session.strategy).count(),
            "daily_trades": stats.get("daily_trades", 0),
        }
        auto_disable_eval = evaluator.evaluate_auto_disable_rules(
            session.strategy.auto_disable_rules.filter(is_active=True),
            strategy_stats,
        )
        if auto_disable_eval.get("should_disable"):
            disable_match = (auto_disable_eval.get("matches") or [{}])[0]
            LiveExecutionService._record_violation(
                session.user,
                session.strategy,
                ViolationType.CONSECUTIVE_LOSS,
                f"Strategy auto-disable triggered: {disable_match.get('message', 'Strategy paused')}",
                threshold_value=disable_match.get("threshold"),
                actual_value=disable_match.get("actual_value"),
                action_taken=ViolationAction.DISABLED,
                severity=Severity.CRITICAL,
            )
            # Strategy status no longer controls execution, only the session does
            session.status = "PAUSED"
            session.error_message = disable_match.get("message", "Strategy auto-disable triggered")
            session.save(update_fields=["status", "error_message", "updated_at"])
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
    def _has_pending_order(session, instrument, side=None):
        from marketdata.l1_cache import tick_cache
        open_orders = tick_cache.get_live_open_orders(session.id)
        for o in open_orders:
            if getattr(o, "instrument_id", getattr(getattr(o, "instrument", None), "id", None)) == instrument.id:
                if side is None or o.side == side:
                    return True
        return False

    @staticmethod
    def place_order(session, instrument, side, quantity, order_type=OrderType.MARKET, price=None, trigger_price=None):
        if session.status != "RUNNING":
            raise ValueError("Live trading session is not running")

        BrokerService.ensure_session(session.broker_credential)
        LiveExecutionService._ensure_fresh_broker_state(session.user, session.broker_credential)
        settings = getattr(session.broker_credential, 'order_settings', None)
        max_retries = settings.max_retries if settings else 2
        retry_delay = (settings.retry_delay_ms if settings else 500) / 1000.0
        order_timeout = settings.order_timeout_seconds if settings else 30
        default_slippage = Decimal(str(settings.default_slippage_pct)) if settings and settings.default_slippage_pct else Decimal("0")

        expected_price = Decimal(str(price)) if price is not None else LiveExecutionService._resolve_price(instrument, trigger_price)

        if default_slippage > 0 and expected_price > 0 and order_type in {OrderType.LIMIT, OrderType.STOP_LIMIT}:
            slippage_amt = expected_price * (default_slippage / Decimal("100"))
            tick_size = Decimal(str(getattr(instrument, 'tick_size', "0.05") or "0.05"))
            if side == Side.BUY:
                expected_price = expected_price + slippage_amt
            else:
                expected_price = expected_price - slippage_amt
            expected_price = (expected_price / tick_size).quantize(Decimal("1"), rounding="ROUND_HALF_UP") * tick_size

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

        if reduce_only:
            StrategyRuntimeState.mark_exit_pending(
                "live",
                session.strategy_id,
                instrument.id,
                order_id=temp_order_id,
                reason="Exit order submitted",
            )
        else:
            StrategyRuntimeState.mark_entry_pending(
                "live",
                session.strategy_id,
                instrument.id,
                side=side,
                order_id=temp_order_id,
                order_type=order_type,
                requested_price=float(expected_price) if expected_price is not None else None,
                trigger_price=float(trigger_price) if trigger_price is not None else None,
            )

        # Offload DB writes and broker call to threadpool
        LiveExecutionService._execution_pool.submit(
            LiveExecutionService._async_broker_placement,
            temp_order_id,
            session.id,
            instrument.id,
            side,
            quantity,
            order_type,
            expected_price,
            trigger_price,
            reduce_only,
            order_timeout,
            max_retries,
            retry_delay,
            float(required_capital)
        )
        return temp_order_id

    @classmethod
    def _async_broker_placement(cls, temp_order_id, session_id, instrument_id, side, quantity, order_type, expected_price, trigger_price, reduce_only, order_timeout, max_retries, retry_delay, required_capital):
        """Runs in _execution_pool, away from tick evaluation."""
        from live_trading.models import LiveOrder, TradingSession
        from instruments.models import Instrument
        from brokers.models import OrderSettings

        try:
            session = TradingSession.objects.get(id=session_id)
            instrument = Instrument.objects.get(id=instrument_id)
            settings = getattr(session.broker_credential, 'order_settings', None)
            allocation = session.strategy.live_allocations.filter(portfolio__user=session.user, broker_credential=session.broker_credential).first()
            
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
                trigger_price=trigger_price,
                quantity=int(quantity),
                status=OrderStatus.PENDING,
                validity="DAY",
            )
            LiveExecutionService._create_execution_log(order, "CREATED", message="Order record created, preparing for broker submission")
        except Exception as e:
            logger.error(f"Async broker placement failed to load objects: {e}")
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
                        "trigger_price": str(trigger_price) if trigger_price is not None else None,
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
            StrategyRuntimeState.update_live_order_status(order, broker_status)
        elif broker_status == OrderStatus.FILLED:
            LiveExecutionService._apply_fill_to_position(order, filled_quantity, fill_price)

        # Handle Partial Fills
        if broker_status == OrderStatus.PARTIAL_FILL and settings and settings.partial_fill_action == "CANCEL_REMAINING":
            try:
                LiveExecutionService.cancel_open_order(order)
            except Exception as e:
                logger.error(f"Failed to cancel remaining quantity for partial fill: {e}")

        return order

    @staticmethod
    def _apply_fill_to_position(order, filled_quantity=None, fill_price=None):
        opposite_side = Side.SELL if order.side == Side.BUY else Side.BUY
        opposite_position = LivePosition.objects.filter(
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
            opposite_position.quantity -= closed_qty
            opposite_position.realized_pnl += pnl
            opposite_position.day_pnl += pnl
            opposite_position.current_price = fill_price
            opposite_position.unrealized_pnl = Decimal("0")

            # Record consecutive losses in Redis
            from risk_management.cache import RiskCache
            if order.strategy_id:
                RiskCache.record_trade_result(order.user_id, order.strategy_id, float(pnl))

            if opposite_position.quantity > 0:
                opposite_position.save(update_fields=["quantity", "realized_pnl", "day_pnl", "current_price", "unrealized_pnl", "updated_at"])
                # Initialize trade_state before conditional block to prevent NameError
                # when strategy_id is falsy (manually-placed position on partial close).
                trade_state = {}
                if opposite_position.strategy_id:
                    trade_state = StrategyRuntimeState.mark_open(
                        "live",
                        opposite_position.strategy_id,
                        opposite_position.instrument_id,
                        position_id=opposite_position.id,
                        side=opposite_position.side,
                        quantity=opposite_position.quantity,
                        avg_price=opposite_position.avg_price,
                        config=LiveExecutionService._execution_config_for_order(order),
                        opened_at=opposite_position.opened_at,
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
                if opposite_position.strategy_id:
                    StrategyRuntimeState.mark_closed(
                        "live",
                        opposite_position.strategy_id,
                        opposite_position.instrument_id,
                        reason="Exit fill completed",
                    )
                StrategyRuntimeState.clear_position_state("live-position", opposite_position.id)
                opposite_position.delete()
                LiveExecutionService._broadcast_update(order.user_id, "POSITION_UPDATE", {"position_id": opposite_position.id, "quantity": 0})
            order.session.trades_count += 1
            order.session.pnl += pnl
            order.session.save(update_fields=["trades_count", "pnl", "updated_at"])

            # Update Global Portfolio Realized PnL + Peak Tracking
            portfolio = LivePortfolioService.get_or_create_portfolio(order.user)
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
                allocation = order.allocation
                allocation.utilized_amount = LivePortfolioService._live_allocation_utilized(allocation)
                allocation.total_pnl += pnl
                allocation.today_pnl += pnl
                allocation.realized_pnl += pnl
                allocation.save(update_fields=["utilized_amount", "total_pnl", "today_pnl", "realized_pnl", "updated_at"])

            remaining -= closed_qty

        # Refresh Risk Cache for the hot-path (execute_session_once)
        from risk_management.cache import RiskCache
        portfolio = LivePortfolioService.get_or_create_portfolio(order.user)
        portfolio_value = float(portfolio.total_value or 0)
        RiskCache.sync_on_fill(order.user_id, portfolio_value)

        if remaining > 0:
            position, created = LivePosition.objects.get_or_create(
                user=order.user,
                strategy=order.strategy,
                broker_credential=order.broker_credential,
                instrument=order.instrument,
                side=order.side,
                defaults={
                    "allocation": order.allocation,
                    "source_type": order.source_type,
                    "product_type": order.product_type,
                    "quantity": remaining,
                    "avg_price": fill_price,
                    "current_price": fill_price,
                    "last_broker_sync": timezone.now(),
                },
            )
            if not created:
                total_qty = position.quantity + remaining
                position.avg_price = ((position.avg_price * position.quantity) + (fill_price * remaining)) / total_qty
                position.quantity = total_qty
                position.current_price = fill_price
                position.allocation = order.allocation
                position.last_broker_sync = timezone.now()
                position.save(update_fields=["allocation", "avg_price", "quantity", "current_price", "last_broker_sync", "updated_at"])
            trade_state = StrategyRuntimeState.mark_open(
                "live",
                order.strategy_id,
                order.instrument_id,
                position_id=position.id,
                side=position.side,
                quantity=position.quantity,
                avg_price=position.avg_price,
                config=LiveExecutionService._execution_config_for_order(order),
                opened_at=position.opened_at,
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

    @staticmethod
    def _update_position_mtm(position, last_price):
        position.current_price = last_price
        position.unrealized_pnl = (
            (last_price - position.avg_price) * position.quantity
            if position.side == Side.BUY
            else (position.avg_price - last_price) * position.quantity
        )
        position.day_pnl = position.realized_pnl + position.unrealized_pnl
        position.save(update_fields=["current_price", "unrealized_pnl", "day_pnl", "updated_at"])
        return position

    @staticmethod
    def execute_session_once(session, symbol=None, candle_states=None):
        """Process a single strategy session tick.

        Wrapped with a distributed Redis lock so that two concurrent Celery
        workers processing ticks for the same (session, instrument) cannot
        both enter or exit a position simultaneously.
        """
        if session.status not in ("RUNNING", "PAUSED") or session.strategy.status != StrategyStatus.ACTIVE:
            return False

        # 1. Load Strategy Snapshot & Initialize Unified Executor
        from marketdata.l1_cache import tick_cache
        allocation = tick_cache.get_live_allocation(session.id)
        config = None

        if allocation and allocation.deployed_version_id:
            try:
                version = allocation.deployed_version
                if version:
                    config = version.config_snapshot
            except Exception:
                pass

        if not config:
            config = session.strategy.to_execution_dict()

        executor = StrategyExecutor(config)
        # 2. Get Real-time Risk Stats from Redis (Avoid DB hit)
        from risk_management.cache import RiskCache
        risk_stats = RiskCache.get_stats(session.user_id, session.strategy_id)

        # In HFT Fanning, we only process the specific symbol that triggered the tick
        if not symbol:
            return False

        from marketdata.l1_cache import tick_cache
        instrument = tick_cache.get_instrument(symbol)
        if not instrument:
            return False

        timestamp = timezone.now()
        no_trade_zone = executor.is_in_no_trade_zone(timestamp)

        # Do NOT sync open orders synchronously here. It blocks the ThreadPool and makes an API call.
        # LiveExecutionService.sync_open_orders(session, symbol=symbol)

        processed = False

        # Acquire distributed lock per (session, instrument) so concurrent
        # workers cannot double-enter or double-exit the same position.
        try:
            with StrategyRuntimeState.execution_lock(
                "live", session.strategy_id, instrument.id
            ):
                processed = LiveExecutionService.process_tick(
                    allocation=session,
                    instrument=instrument,
                    config=config,
                    executor=executor,
                    risk_stats=risk_stats,
                    timestamp=timestamp,
                    no_trade_zone=no_trade_zone,
                    symbol=symbol,
                    candle_states=candle_states,
                ) or processed
        except RuntimeError as lock_err:
            # Lock could not be acquired — another worker is processing this
            # instrument right now. Skip this tick to prevent duplicate execution.
            logger.warning(
                "Skipping tick for session=%s instrument=%s: %s",
                session.id, instrument.sym_ticker, lock_err,
            )

        return processed

    @staticmethod
    def process_tick(
        allocation,
        instrument,
        config,
        executor,
        risk_stats,
        timestamp,
        no_trade_zone,
        symbol=None,
        candle_states=None,
    ):
        """Inner tick processor — runs inside the distributed execution lock."""
        base_timeframe, mtf_data = StrategyMarketDataService.get_multi_timeframe_data(config, instrument, candle_states=candle_states)
        candle_df = mtf_data.get(base_timeframe)
        if candle_df is None or candle_df.empty:
            return False
        executor = StrategyExecutor(config, mtf_data=mtf_data)

        last_price = Decimal(str(candle_df["close"].iloc[-1]))
        signal_df = executor.completed_signal_frame(candle_df)
        if signal_df is None or signal_df.empty:
            return False
        from marketdata.l1_cache import tick_cache
        position = tick_cache.get_live_position(allocation.id, instrument.id)
        if not position and hasattr(instrument, "underlying_symbol") and instrument.underlying_symbol:
            underlying = tick_cache.get_instrument(instrument.underlying_symbol)
            if underlying:
                position = tick_cache.get_live_position(allocation.id, underlying.id)

        entry_side = executor.entry_config.get("entry_side", Side.BUY)
        risk_stats = tick_cache.get_live_stats(allocation.id)
        trade_state = StrategyRuntimeState.trade_state("live", allocation.strategy_id, instrument.id)

        if position:
            # EXIT EVALUATION
            state = StrategyRuntimeState.build_position_state(
                config=config,
                position=position,
                side=position.side,
                avg_price=position.avg_price,
                current_price=position.current_price or position.avg_price,
                opened_at=position.opened_at,
                identifier=position.id,
                scope="live-position",
            )
            should_exit, reason, action, action_params = executor.evaluate_exit_logic(state, candle_df, timestamp)

            # Reverse entry check
            reverse_enabled = config.get("reentry_rule", {}).get("allow_reverse_entry", False)
            if not should_exit and reverse_enabled and not no_trade_zone:
                entry_signals = executor.evaluate_entry_signals(signal_df)
                if entry_signals.iloc[-1] and entry_side != position.side:
                    should_exit = True
                    reason = "Reverse Entry Signal"
                    action = "EXIT_ALL"
                    action_params = {}

            StrategyRuntimeState.update_position_state(
                "live-position",
                position.id,
                {
                    "trailing_stop": state.get("trailing_stop"),
                    "peak_price": state.get("peak_price"),
                },
            )

            exit_side = Side.SELL if position.side == Side.BUY else Side.BUY
            if (
                should_exit
                and trade_state.get("phase") != StrategyRuntimeState.EXIT_PENDING
                and not LiveExecutionService._has_pending_order(allocation, instrument, exit_side)
            ):
                if action == 'MOVE_TO_BREAKEVEN':
                    if not state.get(f'breakeven_{reason}'):
                        state['protected_stop_price'] = state['avg_price']
                        StrategyRuntimeState.update_position_state("live-position", position.id, {
                            "protected_stop_price": state['avg_price'],
                            f"breakeven_{reason}": True
                        })
                elif action == 'PARTIAL_EXIT':
                    exit_pct = float(action_params.get('exit_pct', 50))
                    if not state.get(f'partial_exit_{reason}'):
                        exit_qty = int(position.quantity * (exit_pct / 100.0))
                        if exit_qty > 0:
                            StrategyRuntimeState.mark_exit_pending("live", allocation.strategy_id, instrument.id, reason=f"Partial Exit ({exit_pct}%): {reason}")
                            LiveExecutionService.place_strategy_order(
                                session=allocation, instrument=position.instrument,
                                side=exit_side, quantity=exit_qty, order_type="MARKET", price=last_price,
                            )
                            StrategyRuntimeState.update_position_state("live-position", position.id, {f'partial_exit_{reason}': True})
                else:
                    StrategyRuntimeState.mark_exit_pending("live", allocation.strategy_id, instrument.id, reason=reason)
                    LiveExecutionService.place_strategy_order(
                        session=allocation, instrument=position.instrument,
                        side=exit_side, quantity=position.quantity, order_type="MARKET", price=last_price,
                    )
                    return True

                # If reverse entry was triggered, we allow re-entry
                if reason == "Reverse Entry Signal":
                    position = None
        else:
            if no_trade_zone:
                return False

            # ENTRY EVALUATION
            funds_payload = LiveExecutionService._sync_funds_from_broker(allocation.broker_credential, async_refresh=True)
            broker_margin = LiveExecutionService._to_decimal(funds_payload.get("available_margin", 0))

            from marketdata.l1_cache import tick_cache
            allocation_res = tick_cache.get_live_allocation(allocation.id)
            if allocation_res:
                alloc_available = Decimal(str(allocation_res.available_capital or allocation_res.allocated_capital))
                sizing_capital = min(alloc_available, broker_margin)
            else:
                sizing_capital = broker_margin

            evaluator = RiskEvaluator(sizing_capital)

            ok, msg = evaluator.check_strategy_limits(config, risk_stats)
            if not ok:
                return False

            ok, msg = evaluator.check_portfolio_risk(config.get("risk_profile", {}), risk_stats)
            if not ok:
                return False

            can_enter, reason = executor.can_enter(risk_stats, timestamp)
            if not can_enter:
                return False
            if trade_state.get("phase") in {StrategyRuntimeState.ENTRY_PENDING, StrategyRuntimeState.EXIT_PENDING}:
                return False

            signals = executor.evaluate_entry_signals(signal_df)
            if signals.iloc[-1]:
                from instruments.services import InstrumentResolver
                from marketdata.l1_cache import tick_cache
                watch = tick_cache.get_watchlist_instrument(allocation.strategy_id, instrument.id)
                if not watch:
                    return False
                resolutions = InstrumentResolver.resolve(
                    watch, entry_side, spot_price=float(last_price)
                )

                for exec_instrument, exec_side, sizing_config in resolutions:
                    if LiveExecutionService._has_pending_order(allocation, exec_instrument):
                        continue

                    # Step 2: Get execution price and lot size
                    exec_price = StrategyMarketDataService.get_quote(exec_instrument, fallback_price=last_price)
                    lot_size = getattr(exec_instrument, 'lot_size', 1) or 1

                    # Step 3: Determine sizing config
                    if not sizing_config:
                        sizing_config = config

                    # Step 4: Calculate quantity with lot-size rounding
                    quantity = evaluator.calculate_quantity(sizing_config, exec_price, stats=risk_stats, lot_size=lot_size)

                    current_candle = (
                        candle_df.iloc[-1]
                        if executor.candle_completion_rule in ("ON_CLOSE", "ON_OPEN")
                        else signal_df.iloc[-1]
                    )
                    otype, resolved_entry_price, trigger_price = executor.resolve_entry_order(
                        signal_df.iloc[-1],
                        execution_candle=current_candle,
                    )

                    # If entering a derivative/different instrument, original signal-based limit prices don't map cleanly. Force MARKET.
                    if exec_instrument.id != instrument.id:
                        otype = "MARKET"
                        resolved_entry_price = exec_price
                        trigger_price = None

                    LiveExecutionService.place_strategy_order(
                        session=allocation, instrument=exec_instrument,
                        side=exec_side,
                        quantity=quantity, order_type=otype,
                        price=resolved_entry_price,
                        trigger_price=trigger_price,
                    )
            return True

        return False

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
        from django.contrib.auth import get_user_model
        from strategies.models import Strategy

        active_positions = LivePosition.objects.filter(quantity__gt=0).select_related('strategy', 'instrument', 'user')
        recovered = 0
        strategies_seen = set()

        for pos in active_positions:
            if not pos.strategy_id:
                continue
            state = StrategyRuntimeState.trade_state("live", pos.strategy_id, pos.instrument_id)
            if not state.get("phase"):
                StrategyRuntimeState.mark_open(
                    "live",
                    pos.strategy_id,
                    pos.instrument_id,
                    position_id=pos.id,
                    side=pos.side,
                    quantity=pos.quantity,
                    avg_price=pos.avg_price,
                    config=pos.strategy.to_execution_dict(),
                    opened_at=pos.opened_at,
                )
                recovered += 1
            strategies_seen.add((pos.user_id, pos.strategy_id))

        for user_id, strategy_id in strategies_seen:
            try:
                user = get_user_model().objects.get(id=user_id)
                strategy = Strategy.objects.get(id=strategy_id)
                RiskCache.sync_from_db(user, strategy)
            except Exception:
                logger.exception("Failed to rehydrate risk cache for live strategy %s", strategy_id)

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
