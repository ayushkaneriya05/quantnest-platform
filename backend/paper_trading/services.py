import logging
from decimal import Decimal
from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from common.enums import (
    CapitalAllocationType,
    OrderStatus,
    OrderType,
    ProductType,
    Severity,
    Side,
    TransactionType,
    NotificationType,
)
from marketdata.quote_store import QuoteStore
from strategy_engine.runtime import StrategyRuntimeState
from notifications.services import NotificationService
from core.cache_api import cache_api

from .models import (
    PaperOrder, PaperPosition, PaperTrade, PaperAccount,
    Portfolio, CapitalAllocation, FundTransaction, DailyPerformance
)

logger = logging.getLogger(__name__)


def _charge_totals(charges):
    """Flatten calculator entry/exit charges for PaperTrade fields."""
    charges = charges if isinstance(charges, dict) else {}
    legs = (
        charges.get("entry_charges") or {},
        charges.get("exit_charges") or {},
    )
    brokerage = sum((Decimal(str(leg.get("brokerage", 0) or 0)) for leg in legs), Decimal("0"))
    taxes = sum(
        (
            Decimal(str(leg.get("stt", 0) or 0))
            + Decimal(str(leg.get("stamp_duty", 0) or 0))
            + Decimal(str(leg.get("gst", 0) or 0))
            + Decimal(str(leg.get("exchange_charges", 0) or 0))
            + Decimal(str(leg.get("sebi_fee", 0) or 0))
        )
        for leg in legs
    )
    return brokerage, taxes


class PortfolioService:
    @staticmethod
    def get_or_create_portfolio(user):
        portfolio, _ = Portfolio.objects.get_or_create(
            user=user,
            defaults={
                "name": "Primary Portfolio",
                "initial_capital": Decimal("0"),
                "current_capital": Decimal("0"),
                "peak_value": Decimal("0"),
            },
        )
        return portfolio

    @staticmethod
    @transaction.atomic
    def deposit(user, amount, notes=""):
        portfolio = PortfolioService.get_or_create_portfolio(user)
        amount = Decimal(str(amount))
        balance_before = portfolio.current_capital
        portfolio.current_capital = balance_before + amount
        if portfolio.initial_capital <= 0:
            portfolio.initial_capital = portfolio.current_capital
        if portfolio.peak_value < portfolio.current_capital:
            portfolio.peak_value = portfolio.current_capital
            portfolio.peak_date = timezone.now().date()
        portfolio.save()
        return FundTransaction.objects.create(
            portfolio=portfolio,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=portfolio.current_capital,
            notes=notes,
        )

    @staticmethod
    @transaction.atomic
    def withdraw(user, amount, notes=""):
        portfolio = PortfolioService.get_or_create_portfolio(user)
        amount = Decimal(str(amount))

        # Allow small rounding differences (1 paise = 0.01)
        if amount > portfolio.current_capital + Decimal("0.01"):
            raise ValueError(f"Insufficient funds. Available: ₹{portfolio.current_capital:,.2f}")

        # Clamp to available balance to handle rounding
        withdrawal_amount = min(amount, portfolio.current_capital)

        balance_before = portfolio.current_capital
        portfolio.current_capital = balance_before - withdrawal_amount
        portfolio.save()
        return FundTransaction.objects.create(
            portfolio=portfolio,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=-withdrawal_amount,
            balance_before=balance_before,
            balance_after=portfolio.current_capital,
            notes=notes,
        )   

    @staticmethod
    @transaction.atomic
    def allocate_to_strategy(portfolio, strategy, amount_or_pct, allocation_type=CapitalAllocationType.FIXED, allocation_instance=None, deployed_version_id=None):
        """
        Allocate capital to a strategy.
        """
        if allocation_type == CapitalAllocationType.FIXED:
            amount = Decimal(str(amount_or_pct))
        else:
            pct = Decimal(str(amount_or_pct))
            if pct <= 0 or pct > 100:
                raise ValueError("Allocation percentage must be between 0 and 100")
        
        # Get existing allocation if it exists to calculate delta
        old_amount = allocation_instance.effective_allocated if allocation_instance else Decimal("0")
        
        # Total equity before any changes
        E = portfolio.total_value
        
        if allocation_type == CapitalAllocationType.FIXED:
            new_amount = amount
            defaults = {
                "allocation_type": allocation_type,
                "allocated_amount": amount,
                "allocated_percentage": Decimal("0")
            }
        else:
            new_amount = E * (pct / Decimal("100"))
            defaults = {
                "allocation_type": allocation_type,
                "allocated_amount": new_amount,
                "allocated_percentage": pct
            }

        if deployed_version_id is not None:
            from strategies.models import StrategyVersion
            try:
                deployed_version = StrategyVersion.objects.get(id=deployed_version_id, strategy=strategy)
                defaults["deployed_version"] = deployed_version
            except StrategyVersion.DoesNotExist:
                raise ValueError("Invalid strategy version")

        delta = new_amount - old_amount

        if delta > portfolio.current_capital:
            raise ValueError(f"Insufficient unallocated capital. Needed: ₹{delta:,.2f}, Available: ₹{portfolio.current_capital:,.2f}")

        if delta != 0:
            balance_before = portfolio.current_capital
            portfolio.current_capital -= delta
            portfolio.save(update_fields=['current_capital'])

            FundTransaction.objects.create(
                portfolio=portfolio,
                transaction_type=TransactionType.ALLOCATION if delta > 0 else TransactionType.DEALLOCATION,
                amount=-delta,
                balance_before=balance_before,
                balance_after=portfolio.current_capital,
                notes=f"{'Increase' if delta > 0 else 'Decrease'} allocation for {strategy.name}",
            )

        if allocation_instance:
            for key, value in defaults.items():
                setattr(allocation_instance, key, value)
            allocation_instance.save()
            allocation = allocation_instance
        else:
            allocation = CapitalAllocation.objects.create(
                portfolio=portfolio,
                strategy=strategy,
                **defaults,
            )

        return allocation

    @staticmethod
    @transaction.atomic
    def deallocate_from_strategy(allocation):
        """
        Return allocated capital to the portfolio balance.
        """
        portfolio = allocation.portfolio
        strategy_name = allocation.strategy.name
        amount_to_return = allocation.effective_allocated

        balance_before = portfolio.current_capital
        portfolio.current_capital = balance_before + amount_to_return
        portfolio.save()

        FundTransaction.objects.create(
            portfolio=portfolio,
            transaction_type=TransactionType.DEALLOCATION,
            amount=amount_to_return,
            balance_before=balance_before,
            balance_after=portfolio.current_capital,
            notes=f"De-allocation from {strategy_name}",
        )

        allocation.delete()

    @staticmethod
    @transaction.atomic
    def rebalance_allocations(portfolio):
        """
        Adjust allocated_amount for all PERCENTAGE type allocations.
        """
        total_value = portfolio.total_value
        if total_value <= 0:
            return

        allocations = portfolio.allocations.filter(
            allocation_type=CapitalAllocationType.PERCENTAGE
        )

        for alloc in allocations:
            new_amount = total_value * (alloc.allocated_percentage / Decimal("100"))
            alloc.allocated_amount = new_amount
            alloc.save(update_fields=["allocated_amount", "updated_at"])

            # Also sync linked paper account if it exists.
            paper_account = PaperAccount.objects.filter(allocation=alloc).first()
            if paper_account:
                paper_account.current_balance = new_amount
                paper_account.save(update_fields=["current_balance", "updated_at"])

                # Update unified cache for account funds
                funds_data = {
                    'net_equity': str(paper_account.current_balance),
                    'cash_balance': str(paper_account.current_balance),
                    'available_margin': str(paper_account.current_balance),
                    'used_margin': '0',
                    'account_id': str(paper_account.id),
                }
                cache_api.update_account_funds(paper_account.id, funds_data)

        return allocations.count()

    @staticmethod
    def ensure_paper_account_for_allocation(allocation, name=None):
        target_amount = allocation.effective_allocated
        paper_account, created = PaperAccount.objects.get_or_create(
            user=allocation.portfolio.user,
            allocation=allocation,
            defaults={
                "name": name or f"Paper Account - {allocation.strategy.name} (Alloc #{allocation.id})",
                "initial_balance": target_amount,
                "current_balance": target_amount,
            },
        )

        # Update unified cache for account funds
        funds_data = {
            'net_equity': str(paper_account.current_balance),
            'cash_balance': str(paper_account.current_balance),
            'available_margin': str(paper_account.current_balance),
            'used_margin': '0',
            'account_id': str(paper_account.id),
        }
        cache_api.update_account_funds(paper_account.id, funds_data)

        if not created:
            if paper_account.current_balance > target_amount:
                paper_account.current_balance = target_amount
            paper_account.save(update_fields=["current_balance", "updated_at"])

        return paper_account

    @staticmethod
    def can_delete_paper_account(paper_account):
        """Check if paper account can be safely deleted."""
        # Check for open positions
        open_positions = PaperPosition.objects.filter(account=paper_account).count()
        if open_positions > 0:
            return False, f"Cannot delete: account has {open_positions} open position(s)"

        # Use a small epsilon instead of exact float comparison to handle
        # rounding differences (e.g. 0.000001 residual from DB aggregation).
        if abs(paper_account.unrealized_pnl or 0) > Decimal("0.01"):
            return False, f"Cannot delete: account has \u20b9{abs(paper_account.unrealized_pnl):.2f} unrealized P&L"

        return True, "Safe to delete"

    @staticmethod
    def take_daily_snapshot(portfolio):
        current_date = timezone.localdate()
        closing_capital = portfolio.total_value
        opening_capital = closing_capital - portfolio.today_pnl
        trades = PaperTrade.objects.filter(account__user=portfolio.user, exit_time__date=current_date)
        
        # Calculate daily fees
        brokerage_paid = sum(
            (_charge_totals(t.charges_json)[0] for t in trades),
            Decimal("0"),
        )
        taxes_paid = sum(
            (_charge_totals(t.charges_json)[1] for t in trades),
            Decimal("0"),
        )

        record, _ = DailyPerformance.objects.update_or_create(
            portfolio=portfolio,
            date=current_date,
            defaults={
                "opening_capital": opening_capital,
                "closing_capital": closing_capital,
                "total_pnl": portfolio.today_pnl,
                "pnl_percentage": ((portfolio.today_pnl / opening_capital) * 100) if opening_capital else 0,
                "trades_count": trades.count(),
                "winning_trades": trades.filter(net_pnl__gt=0).count(),
                "losing_trades": trades.filter(net_pnl__lt=0).count(),
                "brokerage_paid": brokerage_paid,
                "taxes_paid": taxes_paid,
            },
        )
        return record

class PaperExecutionService:
    STRATEGY_ORDER_STATUSES = {OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL}

    @staticmethod
    def _publish_execution_event(action: str, session, scope: str = "paper"):
        from django.core.cache import cache
        import json
        import logging
        logger = logging.getLogger(__name__)
        
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
    def _get_session_id(account, strategy_id):
        if not account or not strategy_id:
            return 0
        from paper_trading.models import PaperTradingSession
        sess = PaperTradingSession.objects.filter(account=account, strategy_id=strategy_id).values_list('id', flat=True).first()
        return sess or 0

    @staticmethod
    def deploy_session(user, strategy, allocation, account, initial_status="RUNNING"):
        from paper_trading.models import PaperTradingSession
        from django.utils import timezone
        
        session, created = PaperTradingSession.objects.update_or_create(
            user=user,
            strategy=strategy,
            allocation=allocation,
            account=account,
            defaults={
                "status": initial_status,
                "started_at": timezone.now() if initial_status == "RUNNING" else None,
                "ended_at": None,
                "error_message": "",
            }
        )

        # Initialize risk metrics for paper session
        from core.cache_api import cache_api
        cache_api.update_risk_metrics("paper", str(session.id), {
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
            "net_equity": str(account.current_balance),
            "cash_balance": str(account.current_balance),
            "available_margin": str(account.current_balance),
        })

        # Initialize account funds in unified cache
        funds_data = {
            'net_equity': str(account.current_balance),
            'cash_balance': str(account.current_balance),
            'available_margin': str(account.current_balance),
            'used_margin': '0',
            'account_id': str(account.id),
        }
        cache_api.update_account_funds(account.id, funds_data)

        # Rebuild runtime state from database for session recovery
        PaperExecutionService.rebuild_runtime_state_from_db(str(session.id))

        if initial_status == "RUNNING":
            PaperExecutionService._publish_execution_event("SESSION_START", session, "paper")
        
        NotificationService.notify(
            user=user,
            title="Paper Strategy Deployed",
            message=f"Strategy '{strategy.name}' has been deployed to paper trading.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.INFO,
            strategy=strategy,
            data={"session_id": str(session.id), "module": "paper"}
        )
        return session

    @staticmethod
    def pause_session(session):
        session.status = "PAUSED"
        session.error_message = ""
        session.save(update_fields=["status", "error_message", "updated_at"])
        
        NotificationService.notify(
            user=session.user,
            title="Paper Strategy Paused",
            message=f"Paper session for '{session.strategy.name}' has been paused.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.WARNING,
            strategy=session.strategy,
            data={"session_id": str(session.id), "module": "paper"}
        )
        PaperExecutionService._publish_execution_event("SESSION_PAUSE", session, "paper")
        return session

    @staticmethod
    def stop_session(session, close_positions=True):            
        if close_positions:
            open_positions = PaperPosition.objects.filter(
                account=session.account,
                strategy=session.strategy,
                quantity__gt=0
            )
            for pos in open_positions:
                try:
                    PaperExecutionService._close_position(session.strategy, session.account, pos)
                except Exception as e:
                    logger.error(f"Failed to close paper position {pos.id}: {e}")
                    try:
                        NotificationService.notify(
                            user=session.user,
                            title="Paper Position Close Failed",
                            message=f"Failed to close paper position for {pos.instrument.symbol} during session stop. Position may remain open.",
                            notification_type=NotificationType.STRATEGY_ERROR,
                            severity=Severity.WARNING,
                            strategy=session.strategy,
                            data={"position_id": str(pos.id), "symbol": pos.instrument.symbol, "module": "paper"}
                        )
                    except Exception:
                        logger.exception("Failed dispatching paper position close failure notification")
                    
        session.status = "STOPPED"
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "ended_at", "updated_at"])
        
        NotificationService.notify(
            user=session.user,
            title="Paper Session Stopped",
            message=f"Paper session for '{session.strategy.name}' has been stopped.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.CRITICAL,
            strategy=session.strategy,
            data={"session_id": str(session.id), "module": "paper"}
        )
        PaperExecutionService._publish_execution_event("SESSION_STOP", session, "paper")
        return session

    @staticmethod
    def resume_session(session):
        from django.utils import timezone
        session.status = "RUNNING"
        session.error_message = ""
        if not session.started_at:
            session.started_at = timezone.now()
        session.ended_at = None
        session.save(update_fields=["status", "error_message", "started_at", "ended_at", "updated_at"])
        
        NotificationService.notify(
            user=session.user,
            title="Paper Strategy Resumed",
            message=f"Paper session for '{session.strategy.name}' is running again.",
            notification_type=NotificationType.SYSTEM_ALERT,
            severity=Severity.INFO,
            strategy=session.strategy,
            data={"session_id": str(session.id), "module": "paper"}
        )
        PaperExecutionService._publish_execution_event("SESSION_START", session, "paper")
        return session

    @staticmethod
    def _close_position(strategy, account, position):
        from common.enums import Side
        from decimal import Decimal
        
        
        close_side = Side.SELL if position.side == Side.BUY else Side.BUY
        
        PaperExecutionService._execute_market_order(
            account=account,
            strategy=strategy,
            instrument=position.instrument,
            side=close_side,
            quantity=position.quantity,
            exit_reason="SESSION_STOP",
        )


    @staticmethod
    def _validate_auto_disable(session, account, raise_on_trigger=True):
        from risk_management.auto_disable import AutoDisableGate
        from core.cache_view import cache_view

        stats = cache_view.get_risk_metrics("paper", session.id)
        match = AutoDisableGate.evaluate(session, stats, account.initial_balance)
        if match:
            PaperExecutionService._publish_execution_event("SESSION_PAUSE", session, "paper")
        if match and raise_on_trigger:
            raise ValueError(f"Strategy auto-disable triggered: {match.get('message', 'Strategy auto-disable triggered')}")
        return bool(match)

    @staticmethod
    def _resolve_product_type(instrument):
        if getattr(instrument, 'instrument_type', '') in ('STOCK', 'INDEX'):
            return ProductType.CNC
        return ProductType.MARGIN

    @staticmethod
    def _get_base_instrument(strategy, execution_instrument):
        if not strategy:
            return execution_instrument
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
    def place_order(
        session,
        strategy,
        account,
        instrument,
        side,
        quantity,
        price=None,
        order_tag="strategy_execution",
    ):

        PaperExecutionService._validate_auto_disable(
            session=session,
            account=account,
        )

        return PaperExecutionService._execute_market_order(
            session=session,
            account=account, instrument=instrument,
            strategy=strategy, side=side,
            quantity=quantity, order_tag=order_tag,
            fallback_price=price,
        ).id
    
    @staticmethod
    def start_websocket_processor(account):
        """
        Start WebSocket simulator for paper trading account.
        This enables paper trading to use the same unified architecture as live trading.
        
        Args:
            account: PaperAccount instance
        """
        from brokers.websocket import PaperWebSocketSimulator
        
        try:
            websocket_simulator = PaperWebSocketSimulator(account)
            websocket_simulator.connect()
            websocket_simulator.subscribe(['orders', 'trades', 'positions'])
            logger.info(f"Started WebSocket simulator for paper account {account.id}")
            return websocket_simulator
        except Exception as e:
            logger.exception(f"Failed to start WebSocket simulator for paper account {account.id}: {e}")
            return None


    @staticmethod
    def resolve_market_price(instrument, fallback_price=None):
        quote = QuoteStore.get_latest(instrument.sym_ticker)
        if quote and quote.get("price") is not None:
            return Decimal(str(quote["price"]))
        if fallback_price is not None:
            return Decimal(str(fallback_price))
        if instrument.previous_close is not None:
            return Decimal(str(instrument.previous_close))
        raise ValueError("Live market price is unavailable")


    @staticmethod
    @transaction.atomic
    def _execute_market_order(
        session,
        account,
        instrument,
        side,
        quantity,
        strategy=None,
        order_tag="",
        fallback_price=None,
        executed_at=None,
        exit_reason="strategy_exit",
    ):
        executed_at = executed_at or timezone.now()
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("Order quantity must be greater than zero")
        order_type = OrderType.MARKET
        
        # Re-fetch account and allocation with select_for_update to ensure atomic balance updates
        account = PaperAccount.objects.select_for_update().select_related(
            "allocation__deployed_version"
        ).get(id=account.id)
        allocation = account.allocation
        
        product_type = PaperExecutionService._resolve_product_type(instrument)
                
        raw_price = PaperExecutionService.resolve_market_price(instrument, fallback_price=fallback_price)

        strategy_config = None
        if allocation and allocation.deployed_version:
            strategy_config = allocation.deployed_version.config_snapshot
        else:
            logger.error("No deployed version found for allocation")
            raise ValueError("Strategy must have a deployed version for execution")

        from common.costs import TradingCostCalculator
        price = TradingCostCalculator.apply_slippage(raw_price, side, 0)
        
        remaining = quantity
        opposite_side = Side.SELL if side == Side.BUY else Side.BUY
        opposite_position = (
            PaperPosition.objects.select_for_update().filter(account=account, instrument=instrument, side=opposite_side)
            .order_by("opened_at")
            .first()
        )
        
        closing_qty = min(opposite_position.quantity, remaining) if opposite_position else 0
        opening_qty = remaining - closing_qty
        if opening_qty > 0:
            required_margin = price * opening_qty
            if allocation and required_margin > allocation.available_amount:
                PaperOrder.objects.create(
                    account=account, strategy=strategy,
                    instrument=instrument, order_type=order_type,
                    product_type=product_type, side=side,
                    quantity=quantity, price=raw_price,
                    status=OrderStatus.REJECTED,
                    rejection_reason="Insufficient allocation capital",
                    executed_at=executed_at, order_tag=order_tag,
                )
                raise ValueError(
                    f"Insufficient allocation capital. Required: {required_margin}, "
                    f"Available: {allocation.available_amount}"
                )
            if required_margin > account.current_balance:
                PaperOrder.objects.create(
                    account=account, strategy=strategy, instrument=instrument, order_type=order_type,
                    product_type=product_type, side=side, quantity=quantity, price=raw_price,
                    status=OrderStatus.REJECTED, rejection_reason="Insufficient margin",
                    executed_at=executed_at, order_tag=order_tag,
                )
                raise ValueError(f"Insufficient margin. Required: {required_margin}, Available: {account.current_balance}")

        order = PaperOrder.objects.create(
            account=account, strategy=strategy, instrument=instrument, order_type=order_type,
            product_type=product_type, side=side, quantity=quantity, price=raw_price,
            avg_fill_price=price, filled_quantity=quantity, status=OrderStatus.FILLED,
            executed_at=executed_at, order_tag=order_tag,
        )
        if opposite_position:
            gross_pnl = (
                (price - opposite_position.avg_price) * closing_qty
                if opposite_position.side == Side.BUY
                else (opposite_position.avg_price - price) * closing_qty
            )
            from brokers.models import BrokerChargeProfile

            profile = BrokerChargeProfile.objects.filter(user=account.user, is_default=True).first()
            if not profile:
                profile = BrokerChargeProfile.objects.filter(user=account.user).first()

            net_pnl, charges = TradingCostCalculator.calculate_net_pnl(
                gross_pnl=gross_pnl,
                entry_price=opposite_position.avg_price,
                exit_price=price,
                quantity=closing_qty,
                side=opposite_position.side,
                instrument_type=instrument.instrument_type if instrument else 'EQUITY',
                entry_time=opposite_position.opened_at,
                exit_time=executed_at,
                profile=profile,
            )

            trade = PaperTrade.objects.create(
                account=account, strategy=strategy or opposite_position.strategy, instrument=instrument,
                side=opposite_position.side, quantity=closing_qty, entry_price=opposite_position.avg_price,
                entry_time=opposite_position.opened_at, exit_price=price, exit_time=executed_at,
                exit_order=order, exit_reason=exit_reason, gross_pnl=gross_pnl,
                net_pnl=net_pnl,
                pnl_pct=((net_pnl / (opposite_position.avg_price * closing_qty)) * 100) if opposite_position.avg_price else 0,
                brokerage=_charge_totals(charges)[0],
                taxes=_charge_totals(charges)[1],
                charges_json=charges,
                holding_duration_seconds=max(int((executed_at - opposite_position.opened_at).total_seconds()), 0),
            )

            # Update unified cache risk metrics with trade result
            from core.cache_view import cache_view
            from core.cache_api import cache_api
            current = cache_view.get_risk_metrics("paper", session.id)
            pnl = float(net_pnl)
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

            cache_api.update_risk_metrics("paper", session.id, current)

            margin_released = (
                Decimal(str(opposite_position.margin_blocked or 0))
                * Decimal(str(closing_qty)) / Decimal(str(opposite_position.quantity))
            )
            account.current_balance += net_pnl
            opposite_position.quantity -= closing_qty
            opposite_position.margin_blocked = max(Decimal("0"), Decimal(str(opposite_position.margin_blocked)) - margin_released)
            if opposite_position.quantity > 0:
                opposite_position.save(update_fields=["quantity", "margin_blocked", "updated_at"])
                if opposite_position.strategy_id:
                    base_inst = PaperExecutionService._get_base_instrument(opposite_position.strategy, opposite_position.instrument)
                    StrategyRuntimeState.mark_open(
                        "paper",
                        session.id,
                        base_inst.id,
                        side=opposite_position.side,
                        quantity=opposite_position.quantity,
                        avg_price=opposite_position.avg_price,
                        config=strategy_config,
                        opened_at=opposite_position.opened_at,
                        execution_instrument_id=opposite_position.instrument_id,
                    )

                    # Update unified cache for paper trading on partial close
                    cache_api.update_order("paper", str(session.id), {
                        'id': str(order.id),
                        'instrument_id': order.instrument_id,
                        'symbol': order.instrument.sym_ticker if order.instrument else '',
                        'side': side,
                        'quantity': closing_qty,
                        'filled_quantity': closing_qty,
                        'status': 'FILLED',
                        'avg_fill_price': str(price),
                        'session_id': str(session.id),
                    })
                    # Update only the affected position in cache (no DB reload)
                    if opposite_position.quantity > 0:
                        cache_api.update_position("paper", str(session.id), {
                            'id': str(opposite_position.id),
                            'instrument_id': opposite_position.instrument_id,
                            'symbol': opposite_position.instrument.sym_ticker if opposite_position.instrument else '',
                            'side': opposite_position.side,
                            'quantity': opposite_position.quantity,
                            'avg_price': str(opposite_position.avg_price),
                            'current_price': str(opposite_position.current_price),
                            'unrealized_pnl': str(opposite_position.unrealized_pnl),
                            'session_id': str(session.id),
                        })
            else:
                if opposite_position.strategy_id:
                    base_inst = PaperExecutionService._get_base_instrument(opposite_position.strategy, opposite_position.instrument)
                    StrategyRuntimeState.mark_closed(
                        "paper",
                        session.id,
                        base_inst.id,
                    )
                opposite_position.delete()
                
                # Update unified cache for paper trading on position close
                cache_api.remove_position("paper", str(session.id), str(opposite_position.id))
            remaining -= closing_qty

        if remaining > 0:
            position = PaperPosition.objects.select_for_update().filter(account=account, instrument=instrument, side=side).first()
            if position:
                total_quantity = position.quantity + remaining
                total_cost = (Decimal(str(position.avg_price)) * position.quantity) + (price * remaining)
                position.quantity = total_quantity
                position.avg_price = total_cost / total_quantity if total_quantity else price
                position.current_price = price
                position.margin_blocked = Decimal(str(position.margin_blocked)) + (price * remaining)
                position.save(update_fields=["strategy", "quantity", "avg_price", "current_price", "margin_blocked", "last_updated", "updated_at"])
                
            else:
                position = PaperPosition.objects.create(
                    account=account, strategy=strategy, instrument=instrument, side=side,
                    quantity=remaining, avg_price=price, current_price=price, margin_blocked=price * remaining,
                )
            
            trade_state = {}
            trade_strategy_id = strategy.id if strategy else position.strategy_id
            if trade_strategy_id:
                base_inst = PaperExecutionService._get_base_instrument(strategy or position.strategy, position.instrument)
                StrategyRuntimeState.mark_open(
                    "paper",
                    session.id,
                    base_inst.id,
                    side=position.side,
                    quantity=position.quantity,
                    avg_price=position.avg_price,
                    config=strategy_config or {},
                    opened_at=position.opened_at,
                    execution_instrument_id=position.instrument_id,
                )
            
            # Update unified cache for paper trading
            cache_api.update_order("paper", str(session.id), {
                'id': str(order.id),
                'instrument_id': order.instrument_id,
                'symbol': order.instrument.sym_ticker if order.instrument else '',
                'side': side,
                'quantity': remaining,
                'filled_quantity': remaining,
                'status': 'FILLED',
                'avg_fill_price': str(price),
                'session_id': str(session.id),
            })
            # Update only the affected position in cache (no DB reload)
            if position.quantity > 0:
                cache_api.update_position("paper", str(session.id), {
                    'id': str(position.id),
                    'instrument_id': position.instrument_id,
                    'symbol': position.instrument.sym_ticker if position.instrument else '',
                    'side': position.side,
                    'quantity': position.quantity,
                    'avg_price': str(position.avg_price),
                    'current_price': str(position.current_price),
                    'unrealized_pnl': str(position.unrealized_pnl),
                    'session_id': str(session.id),
                })

        account.save(update_fields=["current_balance", "updated_at"])

        # Update unified cache for account funds
        funds_data = {
            'net_equity': str(account.current_balance),
            'cash_balance': str(account.current_balance),
            'available_margin': str(account.current_balance),
            'used_margin': '0',
            'account_id': str(account.id),
        }
        cache_api.update_account_funds(account.id, funds_data)
        
        if session:
            PaperExecutionService._validate_auto_disable(
                session=session,
                account=account,
                raise_on_trigger=False,
            )
        return order


    @staticmethod
    def rebuild_runtime_state_from_db(session_id):
        """Initialize and recover runtime state from open paper positions using centralized method."""
        from strategy_engine.runtime import StrategyRuntimeState
        return StrategyRuntimeState.rebuild_runtime_state_from_db("paper", session_id)

    @classmethod
    def run_zmq_subscriber(cls):
        """
        Runs continuously in a background process/thread, listening to the StrategyOrderRouter 
        ZeroMQ publisher for any 'PAPER' scope OrderRequests.
        """
        import zmq
        import json
        from strategy_engine.router import OrderRequest
        from paper_trading.models import PaperTradingSession
        from instruments.models import Instrument
        
        context = zmq.Context.instance()
        socket = context.socket(zmq.SUB)
        socket.bind("tcp://127.0.0.1:5556")
        socket.setsockopt_string(zmq.SUBSCRIBE, "PAPER")
        
        logger.info("PaperExecutionService ZMQ Subscriber listening for PAPER orders...")
        
        while True:
            req = None
            try:
                topic, message = socket.recv_multipart()
                data = json.loads(message.decode('utf-8'))
                req = OrderRequest(**data)
                
                # Rehydrate objects
                session = PaperTradingSession.objects.select_related('account', 'strategy').get(id=req.session_id)
                instrument = Instrument.objects.get(id=req.instrument_id)
                
                PaperExecutionService.place_order(
                    session=session,
                    strategy=session.strategy,
                    account=session.account,
                    instrument=instrument,
                    side=req.side,
                    quantity=req.qty,
                    price=req.target_price,
                )
                logger.info(f"ZMQ paper order placed: {req.side} {req.qty} {instrument.sym_ticker} reason={getattr(req, 'reason', 'N/A')}")
            except Exception as e:
                session_id = getattr(req, "session_id", "unknown")
                logger.error(f"ZMQ Paper Subscriber Error for session {session_id}: {e}", exc_info=True)
                # Revert phase to prevent permanent state lock
                try:
                    if req is None:
                        continue
                    state = StrategyRuntimeState.trade_state("paper", req.session_id, req.instrument_id)
                    if state.get("phase") in (StrategyRuntimeState.ENTRY_PENDING, StrategyRuntimeState.EXIT_PENDING):
                        revert_phase = StrategyRuntimeState.OPEN if state.get("quantity", 0) > 0 else StrategyRuntimeState.CLOSED
                        StrategyRuntimeState.update_trade_state("paper", req.session_id, req.instrument_id, {"phase": revert_phase})
                        logger.info(f"Reverted paper phase to {revert_phase} for session {req.session_id} instrument {req.instrument_id}")
                except Exception:
                    logger.exception("Failed to revert paper trade phase after ZMQ error")


