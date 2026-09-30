import logging
import uuid
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
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


CHARGE_PROFILE_FIELDS = (
    "brokerage_per_order",
    "brokerage_pct",
    "brokerage_cap",
    "stt_eq_delivery_pct",
    "stt_eq_intraday_pct",
    "stt_futures_pct",
    "stt_options_sell_pct",
    "exchange_txn_pct",
    "exchange_txn_fo_pct",
    "sebi_turnover_pct",
    "stamp_duty_pct",
    "gst_pct",
)


def _snapshot_charge_profile(profile):
    if not profile:
        return {"resolved": True}
    return {
        "name": profile.name,
        **{field: str(getattr(profile, field)) for field in CHARGE_PROFILE_FIELDS},
    }


def _charge_profile_from_snapshot(snapshot):
    if not snapshot or not any(field in snapshot for field in CHARGE_PROFILE_FIELDS):
        return None
    return SimpleNamespace(**snapshot)


def _publish_cache_after_commit(method_name, *args, **kwargs):
    callback = getattr(cache_api, method_name)
    transaction.on_commit(lambda: callback(*args, **kwargs))


def _refresh_paper_account_funds_after_commit(account):
    funds_data = {
        "net_equity": str(account.current_balance),
        "cash_balance": str(account.current_balance),
        "available_margin": str(account.margin_available),
        "used_margin": str(account.margin_used),
        "account_id": str(account.id),
    }
    for session_id in account.sessions.values_list("id", flat=True):
        transaction.on_commit(lambda sid=str(session_id), data=funds_data: cache_api.update_session_funds("paper", sid, data))


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
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
        amount = Decimal(str(amount))
        balance_before = portfolio.current_capital
        portfolio.current_capital = balance_before + amount
        if portfolio.initial_capital <= 0:
            portfolio.initial_capital = portfolio.current_capital
        current_value = portfolio.total_value
        if portfolio.peak_value < current_value:
            portfolio.peak_value = current_value
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
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
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
        from common.enums import StrategyStatus
        
        if portfolio.user_id != strategy.user_id:
            raise ValueError('Strategy and portfolio must belong to the same user.')
        if allocation_instance is None:
            if strategy.status != StrategyStatus.ACTIVE:
                raise ValueError('Capital can only be allocated to an active strategy.')
            if not strategy.paper_trading_enabled:
                raise ValueError('Paper trading is disabled for this strategy.')
        elif allocation_instance.strategy_id != strategy.id:
            raise ValueError('Allocation does not belong to this strategy.')

        if allocation_instance is None:
            from strategies.models import Strategy
            strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
            if strategy.status != StrategyStatus.ACTIVE:
                raise ValueError('Capital can only be allocated to an active strategy.')
            if not strategy.paper_trading_enabled:
                raise ValueError('Paper trading is disabled for this strategy.')
        
        paper_account = None
        if allocation_instance:
            paper_account = PaperAccount.objects.select_for_update().filter(allocation_id=allocation_instance.pk).first()
            allocation_instance = CapitalAllocation.objects.select_for_update().get(pk=allocation_instance.pk)
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
        
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

        if paper_account and paper_account.margin_used > paper_account.current_balance + delta:
            raise ValueError("Allocation cannot be reduced below the account's margin in use")

        if delta != 0:
            balance_before = portfolio.current_capital
            portfolio.current_capital -= delta
            portfolio.save(update_fields=['current_capital'])
            if paper_account:
                paper_account.current_balance += delta
                paper_account.save(update_fields=["current_balance", "updated_at"])
                _refresh_paper_account_funds_after_commit(paper_account)

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
    def deallocate_from_strategy(allocation, delete_paper_account=False):
        """Release unassigned capital or detach/delete an associated account."""
        paper_account = PaperAccount.objects.select_for_update().filter(allocation_id=allocation.pk).first()
        allocation = CapitalAllocation.objects.select_for_update().select_related("portfolio", "strategy").get(pk=allocation.pk)
        from strategies.models import Strategy
        strategy = Strategy.objects.select_for_update().get(pk=allocation.strategy_id)
        allocation.strategy = strategy
        if allocation.portfolio.user_id != strategy.user_id:
            raise ValueError('Strategy allocation belongs to a different user.')
        portfolio = allocation.portfolio
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
        amount_to_return = allocation.effective_allocated if not paper_account else Decimal("0")

        if paper_account:
            if paper_account.sessions.filter(status__in=["RUNNING", "PAUSED"]).exists():
                raise ValueError("Stop the paper session before removing its allocation")
            if paper_account.positions.exists():
                raise ValueError("Close all paper positions before removing the allocation")
            if delete_paper_account:
                can_delete, reason = PortfolioService.can_delete_paper_account(paper_account)
                if not can_delete:
                    raise ValueError(reason)
                amount_to_return = paper_account.current_balance
                paper_account.delete()

        if amount_to_return:
            balance_before = portfolio.current_capital
            portfolio.current_capital = balance_before + amount_to_return
            portfolio.save(update_fields=["current_capital", "updated_at"])
            FundTransaction.objects.create(
                portfolio=portfolio,
                transaction_type=TransactionType.DEALLOCATION,
                amount=amount_to_return,
                balance_before=balance_before,
                balance_after=portfolio.current_capital,
                notes=f"De-allocation from {allocation.strategy.name}",
            )
        allocation.delete()

    @staticmethod
    @transaction.atomic
    def rebalance_allocations(portfolio):
        """
        Adjust allocated_amount for all PERCENTAGE type allocations.
        """
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
        total_value = portfolio.total_value
        if total_value <= 0:
            return

        paper_accounts = {
            account.allocation_id: account
            for account in PaperAccount.objects.select_for_update()
            .filter(allocation__portfolio=portfolio, allocation__allocation_type=CapitalAllocationType.PERCENTAGE)
            .order_by("id")
        }
        allocations = list(portfolio.allocations.select_for_update().filter(allocation_type=CapitalAllocationType.PERCENTAGE))
        changes = []
        account_delta = Decimal("0")

        for alloc in allocations:
            new_amount = total_value * (alloc.allocated_percentage / Decimal("100"))
            paper_account = paper_accounts.get(alloc.id)
            if paper_account:
                if new_amount < paper_account.margin_used:
                    logger.warning("Skipping allocation %s rebalance: target is below margin in use", alloc.id)
                    return 0
                account_delta += new_amount - paper_account.current_balance
            changes.append((alloc, paper_account, new_amount))

        balance_before = portfolio.current_capital
        balance_after = balance_before - account_delta
        if balance_after < 0:
            logger.warning("Skipping portfolio %s rebalance: target requires unavailable wallet capital", portfolio.id)
            return 0
        if balance_after != balance_before:
            portfolio.current_capital = balance_after
            portfolio.save(update_fields=["current_capital", "updated_at"])
            FundTransaction.objects.create(
                portfolio=portfolio,
                transaction_type=TransactionType.ADJUSTMENT,
                amount=balance_after - balance_before,
                balance_before=balance_before,
                balance_after=balance_after,
                notes="Percentage allocation rebalance",
            )

        for alloc, paper_account, new_amount in changes:
            alloc.allocated_amount = new_amount
            alloc.save(update_fields=["allocated_amount", "updated_at"])
            if paper_account and paper_account.current_balance != new_amount:
                paper_account.current_balance = new_amount
                paper_account.save(update_fields=["current_balance", "updated_at"])
                _refresh_paper_account_funds_after_commit(paper_account)

        return len(allocations)

    @staticmethod
    @transaction.atomic
    def ensure_paper_account_for_allocation(allocation, name=None):
        paper_account = PaperAccount.objects.select_for_update().filter(allocation_id=allocation.pk).first()
        allocation = CapitalAllocation.objects.select_for_update().select_related("portfolio", "strategy").get(pk=allocation.pk)
        if allocation.strategy.status != 'ACTIVE':
            raise ValueError('A paper account can only be created for an active strategy.')
        if not allocation.strategy.paper_trading_enabled:
            raise ValueError('Paper trading is disabled for this strategy.')
        portfolio = Portfolio.objects.select_for_update().get(pk=allocation.portfolio_id)
        target_amount = allocation.effective_allocated
        created = paper_account is None
        if created:
            paper_account = PaperAccount.objects.create(
                user=allocation.portfolio.user,
                allocation=allocation,
                name=name or f"Paper Account - {allocation.strategy.name} (Alloc #{allocation.id})",
                initial_balance=target_amount,
                current_balance=target_amount,
            )

        if not created and paper_account.current_balance != target_amount:
            delta = target_amount - paper_account.current_balance
            if delta > portfolio.current_capital:
                raise ValueError("Insufficient unallocated capital to restore the paper account balance")
            balance_before = portfolio.current_capital
            portfolio.current_capital -= delta
            portfolio.save(update_fields=["current_capital", "updated_at"])
            paper_account.current_balance = target_amount
            paper_account.save(update_fields=["current_balance", "updated_at"])
            _refresh_paper_account_funds_after_commit(paper_account)
            FundTransaction.objects.create(
                portfolio=portfolio,
                transaction_type=TransactionType.ADJUSTMENT,
                amount=-delta,
                balance_before=balance_before,
                balance_after=portfolio.current_capital,
                notes=f"Paper account allocation adjustment for {allocation.strategy.name}",
            )

        return paper_account

    @staticmethod
    def can_delete_paper_account(paper_account):
        """Check if paper account can be safely deleted."""
        if paper_account.sessions.filter(status__in=["RUNNING", "PAUSED"]).exists():
            return False, "Stop the paper session before deleting this account"

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
    @transaction.atomic
    def delete_paper_account(paper_account):
        paper_account = PaperAccount.objects.select_for_update().select_related("allocation", "user").get(pk=paper_account.pk)
        can_delete, reason = PortfolioService.can_delete_paper_account(paper_account)
        if not can_delete:
            raise ValueError(reason)

        if paper_account.allocation_id:
            PortfolioService.deallocate_from_strategy(paper_account.allocation, delete_paper_account=True)
            return

        portfolio, _ = Portfolio.objects.get_or_create(user=paper_account.user, defaults={"name": "Primary Portfolio"})
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
        amount = paper_account.current_balance
        balance_before = portfolio.current_capital
        paper_account.delete()
        portfolio.current_capital += amount
        portfolio.save(update_fields=["current_capital", "updated_at"])
        FundTransaction.objects.create(
            portfolio=portfolio,
            transaction_type=TransactionType.DEALLOCATION,
            amount=amount,
            balance_before=balance_before,
            balance_after=portfolio.current_capital,
            notes=f"Deleted detached paper account {paper_account.name}",
        )

    @staticmethod
    @transaction.atomic
    def reset_paper_account(paper_account):
        paper_account = PaperAccount.objects.select_for_update().get(pk=paper_account.pk)
        if paper_account.sessions.filter(status__in=["RUNNING", "PAUSED"]).exists():
            raise ValueError("Stop the paper session before resetting this account")
        if paper_account.positions.exists():
            raise ValueError("Close all open positions before resetting this account")

        portfolio, _ = Portfolio.objects.get_or_create(
            user=paper_account.user,
            defaults={"name": "Primary Portfolio"},
        )
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
        delta = paper_account.initial_balance - paper_account.current_balance
        if delta > portfolio.current_capital:
            raise ValueError("Insufficient paper wallet balance to restore this account's initial balance")

        wallet_before = portfolio.current_capital
        if delta:
            portfolio.current_capital -= delta
            paper_account.current_balance = paper_account.initial_balance
            portfolio.save(update_fields=["current_capital", "updated_at"])
            paper_account.save(update_fields=["current_balance", "updated_at"])
            FundTransaction.objects.create(
                portfolio=portfolio,
                transaction_type=TransactionType.ADJUSTMENT,
                amount=-delta,
                balance_before=wallet_before,
                balance_after=portfolio.current_capital,
                notes=f"Reset paper account {paper_account.name} to its initial balance",
            )
            _refresh_paper_account_funds_after_commit(paper_account)

    @staticmethod
    def take_daily_snapshot(portfolio):
        current_date = timezone.localdate()
        closing_capital = portfolio.total_value
        if closing_capital > portfolio.peak_value:
            portfolio.peak_value = closing_capital
            portfolio.peak_date = current_date
            portfolio.save(update_fields=["peak_value", "peak_date", "updated_at"])
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
    def _resolve_cost_configuration(user, slippage_pct, charge_profile_id, include_charges):
        from brokers.models import BrokerChargeProfile

        try:
            slippage_pct = Decimal(str(slippage_pct))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Slippage must be a valid percentage.")
        if slippage_pct < 0 or slippage_pct > 100 or slippage_pct.as_tuple().exponent < -4:
            raise ValueError("Slippage must be between 0 and 100 with at most 4 decimal places.")
        if not isinstance(include_charges, bool):
            raise ValueError("Include charges must be true or false.")

        if charge_profile_id not in (None, ""):
            try:
                profile = BrokerChargeProfile.objects.get(pk=charge_profile_id, user=user)
            except (BrokerChargeProfile.DoesNotExist, ValueError, TypeError):
                raise ValueError("Charge profile was not found for this user.")
        else:
            profile = BrokerChargeProfile.objects.filter(user=user, is_default=True).first()
            if not profile:
                profile = BrokerChargeProfile.objects.filter(user=user).first()
        return slippage_pct, profile, _snapshot_charge_profile(profile)

    @staticmethod
    def configure_session_costs(session, *, slippage_pct, charge_profile_id, include_charges):
        if session.status != "STOPPED":
            raise ValueError("Execution costs can only be changed while the session is stopped.")
        if PaperPosition.objects.filter(
            account=session.account, strategy=session.strategy, quantity__gt=0
        ).exists():
            raise ValueError("Close all open positions before changing paper execution costs.")

        slippage_pct, profile, snapshot = PaperExecutionService._resolve_cost_configuration(
            session.user, slippage_pct, charge_profile_id, include_charges
        )
        session.slippage_pct = slippage_pct
        session.charge_profile = profile
        session.charge_profile_snapshot = snapshot
        session.include_charges = include_charges
        session.save(update_fields=[
            "slippage_pct", "charge_profile", "charge_profile_snapshot",
            "include_charges", "updated_at",
        ])
        return session

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
    def _get_session_id(account, strategy_id):
        if not account or not strategy_id:
            return 0
        from paper_trading.models import PaperTradingSession
        sess = PaperTradingSession.objects.filter(account=account, strategy_id=strategy_id).values_list('id', flat=True).first()
        return sess or 0

    @staticmethod
    def deploy_session(
        user,
        strategy,
        allocation,
        account,
        initial_status="RUNNING",
        slippage_pct=0,
        charge_profile_id=None,
        include_charges=True,
    ):
        from paper_trading.models import PaperTradingSession
        from django.utils import timezone
        from strategies.models import Strategy
        strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
        if strategy.status != 'ACTIVE':
            raise ValueError('Only active strategies can start paper sessions.')
        if not strategy.paper_trading_enabled:
            raise ValueError('Paper trading is disabled for this strategy.')
        if allocation.strategy_id != strategy.id or account.allocation_id != allocation.id:
            raise ValueError('Paper account and allocation must belong to the selected strategy.')
        if strategy.user_id != user.id or allocation.portfolio.user_id != user.id or account.user_id != user.id:
            raise ValueError('Paper strategy, allocation, and account must belong to the selected user.')

        slippage_pct, profile, profile_snapshot = PaperExecutionService._resolve_cost_configuration(
            user, slippage_pct, charge_profile_id, include_charges
        )

        session = PaperTradingSession.objects.select_for_update().filter(
            user=user, strategy=strategy, allocation=allocation, account=account
        ).first()
        if session:
            if session.status == "RUNNING":
                raise ValueError("This paper session is already running.")
            has_open_positions = PaperPosition.objects.filter(account=account, strategy=strategy, quantity__gt=0).exists()
            if has_open_positions:
                raise ValueError("Close open positions before changing paper execution costs or deploying again.")
            session.slippage_pct = slippage_pct
            session.charge_profile = profile
            session.charge_profile_snapshot = profile_snapshot
            session.include_charges = include_charges
            session.status = initial_status
            session.started_at = timezone.now() if initial_status == "RUNNING" else None
            session.ended_at = None
            session.error_message = ""
            session.save(update_fields=[
                "slippage_pct", "charge_profile", "charge_profile_snapshot", "include_charges",
                "status", "started_at", "ended_at", "error_message", "updated_at",
            ])
        else:
            session = PaperTradingSession.objects.create(
                user=user,
                strategy=strategy,
                allocation=allocation,
                account=account,
                slippage_pct=slippage_pct,
                charge_profile=profile,
                charge_profile_snapshot=profile_snapshot,
                include_charges=include_charges,
                status=initial_status,
                started_at=timezone.now() if initial_status == "RUNNING" else None,
                ended_at=None,
                error_message="",
            )

        # Initialize the separate account-funds cache used for capital sizing.
        from core.cache_api import cache_api
        funds_data = {
            'net_equity': str(account.current_balance),
            'cash_balance': str(account.current_balance),
            'available_margin': str(account.current_balance),
            'used_margin': '0',
            'account_id': str(account.id),
        }
        cache_api.update_session_funds("paper", str(session.id), funds_data)

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
                    PaperExecutionService._close_position(session, pos)
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
                    
        remaining_positions = PaperPosition.objects.filter(account=session.account, strategy=session.strategy, quantity__gt=0).count()

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
        return session, remaining_positions

    @staticmethod
    def resume_session(session):
        from django.utils import timezone
        if session.strategy.status != 'ACTIVE' or not session.strategy.paper_trading_enabled:
            raise ValueError('Activate the strategy and enable paper trading before resuming this session.')
        
        cache_api.update_session_funds("paper", str(session.id), {
            'net_equity': str(session.account.current_balance),
            'cash_balance': str(session.account.current_balance),
            'available_margin': str(session.account.current_balance),
            'used_margin': '0',
            'account_id': str(session.account.id),
        })
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
    def _close_position(session, position):
        from common.enums import Side
        
        
        close_side = Side.SELL if position.side == Side.BUY else Side.BUY
        
        PaperExecutionService._execute_market_order(
            session=session,
            account=session.account,
            strategy=session.strategy,
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
    def place_order(
        session,
        strategy,
        account,
        instrument,
        side,
        quantity,
        price=None,
        order_tag="strategy_execution",
        reason="",
        request_id=None,
    ):
        if request_id:
            existing = PaperOrder.objects.filter(request_id=request_id).first()
            if existing:
                return existing.id

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
            reason=reason,
            request_id=request_id,
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
        reason="",
        request_id=None,
    ):
        executed_at = executed_at or timezone.now()
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("Order quantity must be greater than zero")
        if request_id:
            existing = PaperOrder.objects.filter(request_id=request_id).first()
            if existing:
                return existing
        order_type = OrderType.MARKET
        
        # Lock rows separately because both relations are nullable and PostgreSQL
        # rejects FOR UPDATE on the nullable side of an outer join.
        account = PaperAccount.objects.select_for_update().get(id=account.id)
        allocation = None
        if account.allocation_id:
            allocation = CapitalAllocation.objects.select_for_update().get(
                id=account.allocation_id
            )
        
        product_type = PaperExecutionService._resolve_product_type(instrument)
                
        raw_price = PaperExecutionService.resolve_market_price(instrument, fallback_price=fallback_price)

        strategy_config = None
        if allocation and allocation.deployed_version:
            strategy_config = allocation.deployed_version.config_snapshot
        else:
            logger.error("No deployed version found for allocation")
            raise ValueError("Strategy must have a deployed version for execution")

        from common.costs import TradingCostCalculator
        slippage_pct = Decimal(str(session.slippage_pct or 0))
        price = TradingCostCalculator.apply_slippage(raw_price, side, slippage_pct)
        slippage_amount = (abs(Decimal(str(price)) - Decimal(str(raw_price))) * quantity).quantize(Decimal("0.01"))
        
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
                rejected_order = PaperOrder.objects.create(
                    account=account, strategy=strategy,
                    instrument=instrument, reason=str(reason or "")[:255], order_type=order_type,
                    product_type=product_type, side=side,
                    quantity=quantity, price=raw_price,
                    status=OrderStatus.REJECTED,
                    rejection_reason="Insufficient allocation capital",
                    executed_at=executed_at, order_tag=order_tag,
                    request_id=request_id or uuid.uuid4(),
                )
                return rejected_order
            if required_margin > account.current_balance:
                rejected_order = PaperOrder.objects.create(
                    account=account, strategy=strategy, instrument=instrument, reason=str(reason or "")[:255], order_type=order_type,
                    product_type=product_type, side=side, quantity=quantity, price=raw_price,
                    status=OrderStatus.REJECTED, rejection_reason="Insufficient margin",
                    executed_at=executed_at, order_tag=order_tag,
                    request_id=request_id or uuid.uuid4(),
                )
                return rejected_order

        order = PaperOrder.objects.create(
            account=account, strategy=strategy, instrument=instrument, reason=str(reason or "")[:255], order_type=order_type,
            product_type=product_type, side=side, quantity=quantity, price=raw_price,
            avg_fill_price=price, filled_quantity=quantity,
            slippage_pct_applied=slippage_pct, slippage_amount=slippage_amount,
            status=OrderStatus.FILLED,
            executed_at=executed_at, order_tag=order_tag,
            request_id=request_id or uuid.uuid4(),
        )
        if opposite_position:
            gross_pnl = (
                (price - opposite_position.avg_price) * closing_qty
                if opposite_position.side == Side.BUY
                else (opposite_position.avg_price - price) * closing_qty
            )
            profile_snapshot = session.charge_profile_snapshot
            if session.include_charges and not profile_snapshot:
                profile = session.charge_profile
                if not profile:
                    from brokers.models import BrokerChargeProfile
                    profile = BrokerChargeProfile.objects.filter(user=account.user, is_default=True).first()
                    if not profile:
                        profile = BrokerChargeProfile.objects.filter(user=account.user).first()
                profile_snapshot = _snapshot_charge_profile(profile)
                if profile_snapshot:
                    session.charge_profile = profile
                    session.charge_profile_snapshot = profile_snapshot
                    session.save(update_fields=["charge_profile", "charge_profile_snapshot", "updated_at"])
            profile = _charge_profile_from_snapshot(profile_snapshot) if session.include_charges else None

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
                include_charges=session.include_charges,
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
            current = cache_view.get_risk_metrics("paper", session.id)
            pnl = float(net_pnl)
            current["daily_trades"] = int(current.get("daily_trades", 0) or 0) + 1
            current["daily_pnl"] = float(current.get("daily_pnl", 0.0) or 0.0) + pnl
            current["weekly_pnl"] = float(current.get("weekly_pnl", 0.0) or 0.0) + pnl
            current["monthly_pnl"] = float(current.get("monthly_pnl", 0.0) or 0.0) + pnl
            current["total_closed_trades"] = int(current.get("total_closed_trades", 0) or 0) + 1
            current["closed_trades"] = current["total_closed_trades"]
            current["last_exit_time"] = executed_at
            
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

            _publish_cache_after_commit("update_risk_metrics", "paper", session.id, current)

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
                    StrategyRuntimeState.mark_open(
                        "paper",
                        session.id,
                        opposite_position.instrument_id,
                        side=opposite_position.side,
                        quantity=opposite_position.quantity,
                        avg_price=opposite_position.avg_price,
                        config=strategy_config,
                        opened_at=opposite_position.opened_at,
                        execution_instrument_id=opposite_position.instrument_id,
                    )

                    # Update unified cache for paper trading on partial close
                    _publish_cache_after_commit("update_order", "paper", str(session.id), {
                        'id': str(order.id),
                        'instrument_id': order.instrument_id,
                        'symbol': order.instrument.sym_ticker if order.instrument else '',
                        'side': side,
                        'quantity': closing_qty,
                        'filled_quantity': closing_qty,
                        'status': 'FILLED',
                        'avg_fill_price': str(price),
                        'slippage_pct_applied': str(slippage_pct),
                        'slippage_amount': str(slippage_amount),
                        'session_id': str(session.id),
                    })
                    # Update only the affected position in cache (no DB reload)
                    if opposite_position.quantity > 0:
                        _publish_cache_after_commit("update_position", "paper", str(session.id), {
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
                    StrategyRuntimeState.mark_closed(
                        "paper",
                        session.id,
                        opposite_position.instrument_id,
                    )
                opposite_position.delete()
                
                # Update unified cache for paper trading on position close
                _publish_cache_after_commit("remove_position", "paper", str(session.id), str(opposite_position.id))
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
                    account=account, strategy=strategy, instrument=instrument,
                    side=side,
                    quantity=remaining, avg_price=price, current_price=price, margin_blocked=price * remaining,
                )
            
            trade_strategy_id = strategy.id if strategy else position.strategy_id
            if trade_strategy_id:
                StrategyRuntimeState.mark_open(
                    "paper",
                    session.id,
                    position.instrument_id,
                    side=position.side,
                    quantity=position.quantity,
                    avg_price=position.avg_price,
                    config=strategy_config or {},
                    opened_at=position.opened_at,
                    execution_instrument_id=position.instrument_id,
                )
            
            # Update unified cache for paper trading
            _publish_cache_after_commit("update_order", "paper", str(session.id), {
                'id': str(order.id),
                'instrument_id': order.instrument_id,
                'symbol': order.instrument.sym_ticker if order.instrument else '',
                'side': side,
                'quantity': remaining,
                'filled_quantity': remaining,
                'status': 'FILLED',
                'avg_fill_price': str(price),
                'slippage_pct_applied': str(slippage_pct),
                'slippage_amount': str(slippage_amount),
                'session_id': str(session.id),
            })
            # Update only the affected position in cache (no DB reload)
            if position.quantity > 0:
                _publish_cache_after_commit("update_position", "paper", str(session.id), {
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
            _publish_cache_after_commit("update_risk_metrics", "paper", session.id, {"last_entry_time": executed_at})

        account.save(update_fields=["current_balance", "updated_at"])

        # Update unified cache for account funds
        funds_data = {
            'net_equity': str(account.current_balance),
            'cash_balance': str(account.current_balance),
            'available_margin': str(account.current_balance),
            'used_margin': '0',
            'account_id': str(account.id),
        }
        if session:
            cache_api.update_session_funds("paper", str(session.id), funds_data)
        
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
    def run_order_stream_consumer(cls, stop_event=None):
        """Consume durable paper requests and acknowledge recorded outcomes."""
        from paper_trading.models import PaperOrder, PaperTradingSession
        from common.enums import OrderStatus
        from instruments.models import Instrument
        from strategy_engine.order_queue import consume_orders, entry_is_allowed

        def handle(data):
            request_id = data["request_id"]
            if PaperOrder.objects.filter(request_id=request_id).exists():
                return
            session = PaperTradingSession.objects.select_related("account", "strategy").get(id=data["session_id"])
            instrument = Instrument.objects.get(id=data["instrument_id"])
            try:
                if not entry_is_allowed(session.status, data.get("intent")):
                    raise ValueError(f"Paper session is {session.status}; queued entry was not executed")
                order_id = PaperExecutionService.place_order(
                    session=session, strategy=session.strategy, account=session.account,
                    instrument=instrument, side=data["side"], quantity=data["qty"],
                    price=data.get("target_price"), reason=data.get("reason") or "", request_id=request_id,
                )
                order = PaperOrder.objects.get(pk=order_id)
            except Exception as exc:
                logger.exception("Paper request %s failed before a terminal order outcome", request_id)
                order, _ = PaperOrder.objects.get_or_create(
                    request_id=request_id,
                    defaults={
                        "account": session.account,
                        "strategy": session.strategy,
                        "instrument": instrument,
                        "side": data["side"],
                        "quantity": max(int(data.get("qty") or 0), 0),
                        "price": data.get("target_price"),
                        "status": OrderStatus.REJECTED,
                        "reason": str(data.get("reason") or "")[:255],
                        "rejection_reason": str(exc),
                    },
                )
        def reconcile(data):
            StrategyRuntimeState.reconcile_trade_state(
                "paper", data["session_id"], data["instrument_id"], failed_reason=data.get("reason")
            )
        logger.info("PaperExecutionService Redis Stream consumer is ready")
        consume_orders("paper", handle, stop_event=stop_event, after_durable=reconcile)


