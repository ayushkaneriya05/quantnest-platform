from decimal import Decimal, InvalidOperation
from common.costs import snapshot_charge_profile
from django.db import transaction
from django.utils import timezone
from execution.lifecycle import request_session_refresh

from common.enums import (
    TransactionType,
    NotificationType,
)
from notifications.services import NotificationService

from .models import (
    PaperPosition, PaperAccount, PaperTradingSession,
    Portfolio, CapitalAllocation, FundTransaction
)


class PortfolioService:
    @staticmethod
    def get_or_create_portfolio(user):
        portfolio, _ = Portfolio.objects.get_or_create(
            user=user,
            defaults={
                "name": "Primary Portfolio",
                "initial_capital": Decimal("0"),
                "current_capital": Decimal("0"),
            },
        )
        return portfolio

    @staticmethod
    @transaction.atomic
    def deposit(user, amount: Decimal, notes=""):
        portfolio = PortfolioService.get_or_create_portfolio(user)
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)
        balance_before = portfolio.current_capital
        portfolio.current_capital = balance_before + amount
        if portfolio.initial_capital <= 0:
            portfolio.initial_capital = portfolio.current_capital
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
    def withdraw(user, amount: Decimal, notes=""):
        portfolio = PortfolioService.get_or_create_portfolio(user)
        portfolio = Portfolio.objects.select_for_update().get(pk=portfolio.pk)

        if amount > portfolio.current_capital:
            raise ValueError(f"Insufficient funds. Available: ₹{portfolio.current_capital:,.2f}")

        balance_before = portfolio.current_capital
        portfolio.current_capital = balance_before - amount
        portfolio.save()
        return FundTransaction.objects.create(
            portfolio=portfolio,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=-amount,
            balance_before=balance_before,
            balance_after=portfolio.current_capital,
            notes=notes,
        )

    @staticmethod
    @transaction.atomic
    def update_allocation(allocation: CapitalAllocation, amount: Decimal):
        from execution.models import Command
        from execution.repository import enqueue
        from common.enums import ExecutionMode, ExecutionCommandType
        allocation = CapitalAllocation.objects.select_for_update().get(pk=allocation.pk)
        portfolio = Portfolio.objects.select_for_update().get(pk=allocation.portfolio_id)
        account = PaperAccount.objects.filter(allocation_id=allocation.pk).first()
        delta = amount - allocation.allocated_amount
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Allocation must be positive.")
        if account and Command.objects.filter(mode=ExecutionMode.PAPER, account_id=account.pk,
                kind=ExecutionCommandType.BALANCE, applied_at__isnull=True).exists():
            raise ValueError("Wait for the previous capital change to finish.")
        if delta > portfolio.current_capital:
            raise ValueError("Insufficient paper wallet funds.")
        if not delta:
            return allocation
        # Deposits reserve wallet funds now; withdrawals wait for owner approval.
        if delta > 0 or account is None:
            before = portfolio.current_capital
            portfolio.current_capital -= delta
            portfolio.save(update_fields=["current_capital", "updated_at"])
            FundTransaction.objects.create(portfolio=portfolio,
                transaction_type=TransactionType.ALLOCATION if delta > 0 else TransactionType.DEALLOCATION,
                amount=-delta, balance_before=before, balance_after=portfolio.current_capital,
                notes=f"Capital for {allocation.strategy.name}")
        if account is None:
            allocation.allocated_amount = amount
            allocation.save(update_fields=["allocated_amount", "updated_at"])
        else:
            enqueue(ExecutionMode.PAPER, account.pk, ExecutionCommandType.BALANCE,
                {"delta": str(delta), "session_id": account.sessions.get().pk,
                 "portfolio_id": portfolio.pk, "allocation_id": allocation.pk,
                 "allocation_amount": str(amount), "wallet_debited": delta > 0})
        return allocation

    @staticmethod
    @transaction.atomic
    def delete_paper_account(account: PaperAccount):
        """Remove a stopped deployment and return its remaining cash to the wallet."""
        from django.contrib.auth import get_user_model
        get_user_model().objects.select_for_update().get(pk=account.user_id)
        account = PaperAccount.objects.select_for_update().select_related("allocation").get(pk=account.pk)
        from execution.models import AccountCheckpoint, Command, EvaluationCheckpoint
        from common.enums import ExecutionMode
        if Command.objects.filter(mode=ExecutionMode.PAPER, account_id=account.pk, applied_at__isnull=True).exists():
            raise ValueError("Wait for pending account changes before removing this deployment.")
        if account.sessions.exclude(status="STOPPED").exists():
            raise ValueError("Stop the session before removing this deployment.")
        from execution.order_reports import ACTIVE
        if account.positions.exists() or account.orders.filter(status__in=ACTIVE).exists():
            raise ValueError("Close positions and finish pending orders before removing this deployment.")
        allocation = CapitalAllocation.objects.select_for_update().get(pk=account.allocation_id)
        portfolio = Portfolio.objects.select_for_update().get(pk=allocation.portfolio_id)
        before = portfolio.current_capital
        portfolio.current_capital += account.current_balance
        portfolio.save(update_fields=["current_capital", "updated_at"])
        FundTransaction.objects.create(
            portfolio=portfolio, transaction_type=TransactionType.DEALLOCATION,
            amount=account.current_balance, balance_before=before, balance_after=portfolio.current_capital,
            notes=f"Removed deployment {account.name}",
        )
        EvaluationCheckpoint.objects.filter(mode=ExecutionMode.PAPER, session_id__in=account.sessions.values('pk')).delete()
        AccountCheckpoint.objects.filter(mode=ExecutionMode.PAPER, account_id=account.pk).delete()
        account.delete()
        allocation.delete()

    @staticmethod
    @transaction.atomic
    def reset_paper_account(paper_account):
        from execution.models import Command
        from execution.repository import enqueue
        from common.enums import ExecutionMode, ExecutionCommandType
        paper_account = PaperAccount.objects.select_for_update().get(pk=paper_account.pk)
        if paper_account.sessions.exclude(status="STOPPED").exists() or paper_account.positions.exists():
            raise ValueError("Stop and close the session before resetting its capital.")
        if Command.objects.filter(mode=ExecutionMode.PAPER, account_id=paper_account.pk,
                                  applied_at__isnull=True).exists():
            raise ValueError("Wait for pending account changes to finish.")
        portfolio = Portfolio.objects.select_for_update().get(pk=paper_account.allocation.portfolio_id)
        delta = paper_account.allocation.allocated_amount - paper_account.current_balance
        if delta > portfolio.current_capital:
            raise ValueError("Insufficient paper wallet funds.")
        if not delta:
            return
        if delta > 0:
            before = portfolio.current_capital
            portfolio.current_capital -= delta
            portfolio.save(update_fields=["current_capital", "updated_at"])
            FundTransaction.objects.create(portfolio=portfolio, transaction_type=TransactionType.ADJUSTMENT,
                amount=-delta, balance_before=before, balance_after=portfolio.current_capital,
                notes=f"Reset capital for {paper_account.name}")
        enqueue(ExecutionMode.PAPER, paper_account.pk, ExecutionCommandType.BALANCE,
            {"delta": str(delta), "session_id": paper_account.sessions.get().pk,
             "portfolio_id": portfolio.pk, "wallet_debited": delta > 0})

class PaperExecutionService:
    @staticmethod
    def _resolve_cost_configuration(user, slippage_pct, charge_profile_id, include_charges):
        from brokers.models import BrokerChargeProfile

        try:
            slippage_pct = Decimal(str(slippage_pct))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Slippage must be a valid percentage.")
        if not slippage_pct.is_finite() or not 0 <= slippage_pct < 100 or slippage_pct.as_tuple().exponent < -4:
            raise ValueError('Slippage must be at least zero and less than 100 percent, with at most 4 decimal places.')
        if not isinstance(include_charges, bool):
            raise ValueError("Include charges must be true or false.")

        if charge_profile_id not in (None, ""):
            try:
                profile = BrokerChargeProfile.objects.get(pk=charge_profile_id, user=user)
            except (BrokerChargeProfile.DoesNotExist, ValueError, TypeError):
                raise ValueError("Charge profile was not found for this user.")
        else:
            profile = None
        return slippage_pct, profile, snapshot_charge_profile(profile)

    @staticmethod
    @transaction.atomic
    def configure_session_costs(session, *, slippage_pct, charge_profile_id, include_charges):
        PaperAccount.objects.select_for_update().get(pk=session.account_id)
        session = PaperTradingSession.objects.select_for_update().get(pk=session.pk)
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
    @transaction.atomic
    def deploy_session(user, strategy, version, allocation_amount: Decimal,
                       slippage_pct=0, charge_profile_id=None, include_charges=True):
        """Create a complete Paper deployment; standalone ledger creation is not supported."""
        from django.contrib.auth import get_user_model
        from strategies.models import Strategy
        from strategies.services import StrategyDeploymentService
        from commercial.usage import require_inventory_capacity
        user = get_user_model().objects.select_for_update().get(pk=user.pk)
        strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
        if not user.is_active or strategy.user_id != user.pk:
            raise ValueError("Select your own active user account and strategy.")
        if strategy.status != "ACTIVE" or not strategy.paper_trading_enabled:
            raise ValueError("Activate this strategy and enable Paper trading before deployment.")
        if version.strategy_id != strategy.pk:
            raise ValueError("Select a saved version of this strategy.")
        if CapitalAllocation.objects.filter(strategy=strategy, deployed_version=version).exists():
            raise ValueError("This strategy version already has a Paper deployment. Start or manage the existing session.")
        StrategyDeploymentService.validate_snapshot(version.config_snapshot, "paper")
        require_inventory_capacity(user, paper_snapshot=version.config_snapshot)
        slippage_pct, profile, profile_snapshot = PaperExecutionService._resolve_cost_configuration(
            user, slippage_pct, charge_profile_id, include_charges
        )
        portfolio = PortfolioService.get_or_create_portfolio(user)
        allocation = CapitalAllocation.objects.create(
            portfolio=portfolio, strategy=strategy, deployed_version=version,
        )
        allocation = PortfolioService.update_allocation(allocation, allocation_amount)
        account = PaperAccount.objects.create(
            user=user, allocation=allocation, name=strategy.name[:100],
            initial_balance=allocation_amount, current_balance=allocation_amount,
        )
        session = PaperTradingSession.objects.create(
            user=user, strategy=strategy, allocation=allocation, account=account,
            slippage_pct=slippage_pct, charge_profile=profile,
            charge_profile_snapshot=profile_snapshot, include_charges=include_charges,
            status="RUNNING", started_at=timezone.now(),
        )
        suffix = f" · S{session.pk}"
        account.name = f"{strategy.name[:100 - len(suffix)]}{suffix}"
        account.save(update_fields=["name", "updated_at"])
        request_session_refresh("paper", session)
        NotificationService.notify(
            user=user, title="Paper strategy deployed",
            message=f"Strategy '{strategy.name}' has been deployed to Paper trading.",
            type=NotificationType.INFO,
            data={"session_id": str(session.id), "strategy_id": str(strategy.pk),
                  "strategy_name": strategy.name, "module": "paper"},
            dedupe_key=f"paper-session:{session.id}:RUNNING:{session.updated_at.isoformat()}",
        )
        return session

    @staticmethod
    @transaction.atomic
    def pause_session(session):
        session = PaperTradingSession.objects.select_for_update().get(pk=session.pk)
        if session.status != 'RUNNING':
            raise ValueError('Only running sessions can be paused.')
        session.status = "PAUSED"
        session.error_message = ""
        session.save(update_fields=["status", "error_message", "updated_at"])

        NotificationService.notify(
            user=session.user,
            title="Paper Strategy Paused",
            message=f"Paper session for '{session.strategy.name}' has been paused.",
            type=NotificationType.WARNING,
            data={"session_id": str(session.id), "strategy_id": str(session.strategy_id), "strategy_name": session.strategy.name, "module": "paper"},
            dedupe_key=f"paper-session:{session.id}:PAUSED:{session.updated_at.isoformat()}"
        )
        request_session_refresh("paper", session)
        return session

    @staticmethod
    @transaction.atomic
    def stop_session(session, close_positions=True):
        session = PaperTradingSession.objects.select_for_update().get(pk=session.pk)
        session.status, session.ended_at, session.error_message = "STOPPING", None, ""
        session.save(update_fields=["status", "ended_at", "error_message", "updated_at"])
        request_session_refresh("paper", session, close_positions=close_positions)
        remaining = PaperPosition.objects.filter(account_id=session.account_id, quantity__gt=0).count()
        return session, remaining

    @staticmethod
    @transaction.atomic
    def resume_session(session):
        from django.contrib.auth import get_user_model
        get_user_model().objects.select_for_update().get(pk=session.account.user_id)
        account = PaperAccount.objects.select_for_update().get(pk=session.account_id)
        CapitalAllocation.objects.select_for_update().get(pk=session.allocation_id)
        session = PaperTradingSession.objects.select_for_update().get(pk=session.pk)
        from strategies.services import StrategyDeploymentService
        StrategyDeploymentService.validate_snapshot(session.allocation.deployed_version.config_snapshot, 'paper')
        if session.status not in {'PAUSED', 'STOPPED', 'ERROR'}:
            raise ValueError('Wait for a stopping session to settle before resuming.')
        if session.strategy.status != 'ACTIVE' or not session.strategy.paper_trading_enabled:
            raise ValueError('Activate the strategy and enable paper trading before resuming this session.')

        from commercial.usage import require_inventory_capacity
        require_inventory_capacity(session.user, paper_snapshot=session.allocation.deployed_version.config_snapshot,
                                   paper_session_id=session.pk)
        was_stopped = session.status == "STOPPED"
        session.status = "RUNNING"
        session.error_message = ""
        if was_stopped or not session.started_at:
            session.started_at = timezone.now()
        session.ended_at = None
        session.save(update_fields=["status", "error_message", "started_at", "ended_at", "updated_at"])

        NotificationService.notify(
            user=session.user,
            title="Paper Strategy Resumed",
            message=f"Paper session for '{session.strategy.name}' is running again.",
            type=NotificationType.INFO,
            data={"session_id": str(session.id), "strategy_id": str(session.strategy_id), "strategy_name": session.strategy.name, "module": "paper"},
            dedupe_key=f"paper-session:{session.id}:RUNNING:{session.updated_at.isoformat()}"
        )
        request_session_refresh("paper", session)
        return session

