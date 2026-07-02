import logging
from decimal import Decimal
from datetime import timedelta

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
    StrategyStatus,
    TransactionType,
    ViolationAction,
    ViolationType,
)
from marketdata.access import StrategyMarketDataService
from marketdata.streaming import MarketDataStreamer
from risk_management.models import PortfolioRiskProfile, RiskViolation
from risk_management.evaluator import RiskEvaluator
from strategies.models import Strategy
from strategy_engine.runtime import StrategyRuntimeState

from .models import (
    PaperOrder, PaperPosition, PaperTrade, PaperAccount,
    Portfolio, CapitalAllocation, FundTransaction, ExposureSnapshot, DailyPerformance
)

logger = logging.getLogger(__name__)


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
        if portfolio.peak_value < portfolio.total_value:
            portfolio.peak_value = portfolio.total_value
            portfolio.peak_date = timezone.localdate()
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
    def allocate_to_strategy(portfolio, strategy, amount_or_pct, allocation_type=CapitalAllocationType.FIXED):
        """
        Allocate capital to a strategy.
        """
        # Enforce portfolio-level capital availability
        if allocation_type == CapitalAllocationType.FIXED:
            amount = Decimal(str(amount_or_pct))
            if amount > portfolio.total_value:
                raise ValueError("Allocation amount cannot exceed portfolio total equity")
        else:
            pct = Decimal(str(amount_or_pct))
            if pct <= 0 or pct > 100:
                raise ValueError("Allocation percentage must be between 0 and 100")

        defaults = {"allocation_type": allocation_type, "is_active": True}
        if allocation_type == CapitalAllocationType.PERCENTAGE:
            defaults["allocated_percentage"] = pct
            defaults["allocated_amount"] = portfolio.total_value * (pct / Decimal("100"))
        else:
            defaults["allocated_amount"] = amount

        # Get existing allocation if it exists to calculate delta
        old_allocation = CapitalAllocation.objects.filter(portfolio=portfolio, strategy=strategy).first()
        old_amount = old_allocation.effective_allocated if old_allocation else Decimal("0")

        allocation, created = CapitalAllocation.objects.update_or_create(
            portfolio=portfolio,
            strategy=strategy,
            defaults=defaults,
        )

        # Deduct delta from current_capital
        new_amount = allocation.effective_allocated
        delta = new_amount - old_amount
        
        if delta != 0:
            balance_before = portfolio.current_capital
            portfolio.current_capital = balance_before - delta
            portfolio.save()

            FundTransaction.objects.create(
                portfolio=portfolio,
                transaction_type=TransactionType.ALLOCATION if delta > 0 else TransactionType.DEALLOCATION,
                amount=-delta,
                balance_before=balance_before,
                balance_after=portfolio.current_capital,
                notes=f"{'Increase' if delta > 0 else 'Decrease'} allocation for {strategy.name}",
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
    def get_allocation_for_strategy(portfolio, strategy):
        return CapitalAllocation.objects.filter(portfolio=portfolio, strategy=strategy).first()

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
            allocation_type=CapitalAllocationType.PERCENTAGE,
            is_active=True
        )
        
        for alloc in allocations:
            new_amount = total_value * (alloc.allocated_percentage / Decimal("100"))
            alloc.allocated_amount = new_amount
            alloc.save(update_fields=["allocated_amount", "updated_at"])

            # Also sync linked paper account if it exists.
            # IMPORTANT: do NOT blindly set margin_available = new_amount.
            # Open positions have already consumed some margin; we must
            # only give back the truly unused portion.
            paper_account = PaperAccount.objects.filter(allocation=alloc).first()
            if paper_account:
                from paper_trading.models import PaperPosition
                used_margin = PaperPosition.objects.filter(
                    account=paper_account
                ).aggregate(s=Sum("invested_value"))["s"] or Decimal("0")
                free_margin = max(new_amount - used_margin, Decimal("0"))
                paper_account.current_balance = new_amount
                paper_account.margin_available = free_margin
                paper_account.save(update_fields=["current_balance", "margin_available", "updated_at"])

        return allocations.count()

    @staticmethod
    def ensure_paper_account_for_strategy(portfolio, strategy):
        allocation = PortfolioService.get_allocation_for_strategy(portfolio, strategy)
        if not allocation:
            raise ValueError("Strategy has no portfolio allocation")

        target_amount = allocation.effective_allocated
        paper_account, created = PaperAccount.objects.get_or_create(
            user=portfolio.user,
            allocation=allocation,
            name=f"Paper Account - {strategy.name}",
            defaults={
                "initial_balance": target_amount,
                "current_balance": target_amount,
                "margin_available": target_amount,
            },
        )

        if not created:
            if paper_account.allocation_id != allocation.id:
                paper_account.allocation = allocation
            if paper_account.current_balance > target_amount:
                paper_account.current_balance = target_amount
            if paper_account.margin_available > target_amount:
                paper_account.margin_available = target_amount
            paper_account.save(update_fields=["allocation", "current_balance", "margin_available", "updated_at"])

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
    @transaction.atomic
    def record_trade_impact(paper_trade: PaperTrade):
        portfolio = PortfolioService.get_or_create_portfolio(paper_trade.account.user)
        allocation = CapitalAllocation.objects.filter(
            portfolio=portfolio,
            strategy=paper_trade.strategy,
        ).first()

        portfolio.unrealized_pnl = PortfolioService._portfolio_unrealized_pnl(portfolio)
        portfolio.invested_value = PortfolioService._portfolio_invested_value(portfolio)
        total_value = portfolio.total_value
        if total_value > portfolio.peak_value:
            portfolio.peak_value = total_value
            portfolio.peak_date = timezone.localdate()
        portfolio.save()

        if allocation:
            allocation.total_pnl += paper_trade.net_pnl
            allocation.today_pnl += paper_trade.net_pnl
            allocation.utilized_amount = PortfolioService._allocation_utilized_amount(allocation)
            allocation.save()

        PortfolioService.sync_from_paper_account(paper_trade.account)

    @staticmethod
    @transaction.atomic
    def sync_from_paper_account(account):
        """Sync P&L and position data from paper account back to portfolio."""
        portfolio = PortfolioService.get_or_create_portfolio(account.user)

        paper_accounts = PaperAccount.objects.filter(user=account.user)
        aggregate_metrics = paper_accounts.aggregate(
            initial_balance=Sum("initial_balance"),
            realized_pnl=Sum("realized_pnl"),
            today_pnl=Sum("today_pnl"),
            today_trades=Sum("today_trades"),
        )

        if portfolio.initial_capital <= 0:
            portfolio.initial_capital = Decimal(str(aggregate_metrics.get("initial_balance") or 0))

        portfolio.realized_pnl = Decimal(str(aggregate_metrics.get("realized_pnl") or 0))
        portfolio.unrealized_pnl = PortfolioService._portfolio_unrealized_pnl(portfolio)
        portfolio.invested_value = PortfolioService._portfolio_invested_value(portfolio)
        portfolio.today_pnl = Decimal(str(aggregate_metrics.get("today_pnl") or 0))
        portfolio.today_trades = int(aggregate_metrics.get("today_trades") or 0)

        total_value = portfolio.total_value
        if total_value > portfolio.peak_value:
            portfolio.peak_value = total_value
            portfolio.peak_date = timezone.localdate()
        portfolio.save()

        for allocation in portfolio.allocations.select_related("strategy").all():
            strategy_trades = PaperTrade.objects.filter(
                account__user=portfolio.user,
                strategy=allocation.strategy,
            )
            allocation.utilized_amount = PortfolioService._allocation_utilized_amount(allocation)
            allocation.total_pnl = Decimal(str(strategy_trades.aggregate(v=Sum("net_pnl"))["v"] or 0))
            allocation.today_pnl = Decimal(str(
                strategy_trades.filter(exit_time__date=timezone.localdate()).aggregate(v=Sum("net_pnl"))["v"] or 0
            ))
            allocation.save(update_fields=["utilized_amount", "total_pnl", "today_pnl", "updated_at"])

        return portfolio

    @staticmethod
    def take_daily_snapshot(portfolio):
        current_date = timezone.localdate()
        closing_capital = portfolio.total_value
        opening_capital = closing_capital - portfolio.today_pnl
        trades = PaperTrade.objects.filter(account__user=portfolio.user, exit_time__date=current_date)
        record, _ = DailyPerformance.objects.update_or_create(
            portfolio=portfolio,
            date=current_date,
            defaults={
                "opening_capital": opening_capital,
                "closing_capital": closing_capital,
                "realized_pnl": portfolio.realized_pnl,
                "unrealized_pnl": portfolio.unrealized_pnl,
                "total_pnl": portfolio.today_pnl,
                "pnl_percentage": ((portfolio.today_pnl / opening_capital) * 100) if opening_capital else 0,
                "trades_count": trades.count(),
                "winning_trades": trades.filter(net_pnl__gt=0).count(),
                "losing_trades": trades.filter(net_pnl__lt=0).count(),
                "max_exposure": PortfolioService._portfolio_invested_value(portfolio),
                "avg_exposure": PortfolioService._portfolio_invested_value(portfolio),
            },
        )
        return record

    @staticmethod
    def take_exposure_snapshot(portfolio):
        positions = PaperPosition.objects.filter(account__user=portfolio.user).select_related("instrument", "strategy")
        total_exposure = Decimal("0")
        long_exposure = Decimal("0")
        short_exposure = Decimal("0")
        asset_breakdown = {}
        strategy_breakdown = {}
        for position in positions:
            exposure = Decimal(str(position.current_price or position.avg_price)) * position.quantity
            total_exposure += exposure
            if position.side == "BUY":
                long_exposure += exposure
            else:
                short_exposure += exposure
            asset_type = getattr(position.instrument, "instrument_type", "UNKNOWN")
            asset_breakdown[asset_type] = float(asset_breakdown.get(asset_type, 0) + exposure)
            strategy_name = getattr(position.strategy, "name", "Manual")
            strategy_breakdown[strategy_name] = float(strategy_breakdown.get(strategy_name, 0) + exposure)

        return ExposureSnapshot.objects.create(
            portfolio=portfolio,
            snapshot_time=timezone.now(),
            total_exposure=total_exposure,
            exposure_percentage=((total_exposure / portfolio.total_value) * 100) if portfolio.total_value else 0,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            net_exposure=long_exposure - short_exposure,
            exposure_by_asset_type=asset_breakdown,
            exposure_by_sector={},
            exposure_by_strategy=strategy_breakdown,
            open_positions_count=positions.count(),
        )

    @staticmethod
    def _portfolio_invested_value(portfolio):
        positions = PaperPosition.objects.filter(account__user=portfolio.user)
        return sum((Decimal(str(pos.avg_price)) * pos.quantity for pos in positions), Decimal("0"))

    @staticmethod
    def _live_invested_value(portfolio):
        from live_trading.models import LivePosition

        live_positions = LivePosition.objects.filter(user=portfolio.user)
        return sum((Decimal(str(pos.avg_price)) * pos.quantity for pos in live_positions), Decimal("0"))

    @staticmethod
    def _live_unrealized_pnl(portfolio):
        from live_trading.models import LivePosition

        live_positions = LivePosition.objects.filter(user=portfolio.user)
        return sum((Decimal(str(pos.unrealized_pnl or 0)) for pos in live_positions), Decimal("0"))

    @staticmethod
    def _portfolio_unrealized_pnl(portfolio):
        positions = PaperPosition.objects.filter(account__user=portfolio.user)
        return sum((Decimal(str(pos.unrealized_pnl or 0)) for pos in positions), Decimal("0"))

    @staticmethod
    def _allocation_utilized_amount(allocation):
        positions = PaperPosition.objects.filter(account__user=allocation.portfolio.user, strategy=allocation.strategy)
        return sum((Decimal(str(pos.avg_price)) * pos.quantity for pos in positions), Decimal("0"))




def _related_or_none(obj, attr):
    if isinstance(obj, dict):
        return obj.get(attr)
    try:
        return getattr(obj, attr)
    except Exception:
        return None


class PaperExecutionService:
    STRATEGY_ORDER_STATUSES = {OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL}

    @staticmethod
    def _record_violation(user, strategy, violation_type, message, threshold_value=None, actual_value=None, action_taken=ViolationAction.BLOCKED, severity=Severity.WARNING):
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

    @staticmethod
    def _compute_risk_stats(account, strategy, instrument, side, quantity, price):
        positions = PaperPosition.objects.filter(account__user=account.user)
        open_positions = positions.count()
        today_trades = sum(
            int(value or 0)
            for value in account.user.paper_accounts.values_list("today_trades", flat=True)
        )
        daily_pnl = float(
            sum(
                (Decimal(str(value or 0)) for value in account.user.paper_accounts.values_list("today_pnl", flat=True)),
                Decimal("0"),
            )
        )

        total_exposure = sum(
            (Decimal(str(pos.current_price or pos.avg_price)) * pos.quantity) for pos in positions
        )
        strategy_exposure = sum(
            (Decimal(str(pos.current_price or pos.avg_price)) * pos.quantity)
            for pos in positions.filter(strategy=strategy)
        )
        instrument_exposure = sum(
            (Decimal(str(pos.current_price or pos.avg_price)) * pos.quantity)
            for pos in positions.filter(instrument=instrument)
        )

        opposite_side = Side.SELL if side == Side.BUY else Side.BUY
        opens_new_exposure = not PaperPosition.objects.filter(
            account=account,
            instrument=instrument,
            side=opposite_side,
        ).exists()
        if opens_new_exposure:
            payload = Decimal(str(quantity)) * Decimal(str(price))
            total_exposure += payload
            strategy_exposure += payload
            instrument_exposure += payload

        portfolio = PortfolioService.get_or_create_portfolio(account.user)
        portfolio_value = float(portfolio.total_value or 0)

        strategy_allocation_pct = (float(strategy_exposure) / portfolio_value * 100) if portfolio_value > 0 else 0.0
        instrument_exposure_pct = (float(instrument_exposure) / portfolio_value * 100) if portfolio_value > 0 else 0.0

        # Compute consecutive losses
        consecutive_losses = 0
        recent_trades = PaperTrade.objects.filter(
            account=account,
            strategy=strategy,
        ).order_by("-exit_time")[:100]
        for trade in recent_trades:
            if Decimal(str(trade.net_pnl or 0)) < 0:
                consecutive_losses += 1
            else:
                break

        today = timezone.localdate()
        weekly_pnl = float(
            PaperTrade.objects.filter(
                account=account,
                strategy=strategy,
                exit_time__date__gte=today - timedelta(days=7),
            ).aggregate(v=Sum("net_pnl"))["v"] or 0
        )
        monthly_pnl = float(
            PaperTrade.objects.filter(
                account=account,
                strategy=strategy,
                exit_time__date__gte=today - timedelta(days=30),
            ).aggregate(v=Sum("net_pnl"))["v"] or 0
        )

        return {
            'open_positions': open_positions,
            'daily_trades': today_trades,
            'daily_pnl': daily_pnl,
            'total_exposure': float(total_exposure),
            'drawdown': float(portfolio.current_drawdown or 0),
            'strategy_allocation_pct': strategy_allocation_pct,
            'instrument_exposure_pct': instrument_exposure_pct,
            'consecutive_losses': consecutive_losses,
            'max_consecutive_losses': 0,
            'weekly_pnl': weekly_pnl,
            'monthly_pnl': monthly_pnl,
        }

    @staticmethod
    def _validate_risk_for_order(strategy, account, instrument, side, quantity, target_price):
        stats = PaperExecutionService._compute_risk_stats(account, strategy, instrument, side, quantity, target_price)
        strategy_stats = {
            **stats,
            "open_positions": PaperPosition.objects.filter(account=account, strategy=strategy).count(),
            "daily_trades": PaperOrder.objects.filter(
                account=account,
                strategy=strategy,
                status=OrderStatus.FILLED,
                executed_at__date=timezone.localdate(),
            ).count(),
            "consecutive_losses": stats["consecutive_losses"],
        }
        
        evaluator = RiskEvaluator(PortfolioService.get_or_create_portfolio(account.user).total_value or 0)

        ok, msg = evaluator.check_strategy_limits(strategy, strategy_stats)
        if not ok:
            PaperExecutionService._record_violation(
                account.user,
                strategy,
                ViolationType.MAX_TRADES if "daily trades" in msg.lower() else ViolationType.POSITION_SIZE,
                f"Strategy limits violation: {msg}",
            )
            raise ValueError(f"Strategy limits violation: {msg}")

        risk_profile = PortfolioRiskProfile.objects.filter(user=account.user).first()

        portfolio_eval = evaluator.evaluate_portfolio_risk(risk_profile, stats)
        if portfolio_eval.get('breached'):
            breach = portfolio_eval.get('breaches', [{}])[0]
            message = breach.get('message', 'Portfolio risk limit breached')
            PaperExecutionService._record_violation(
                account.user,
                strategy,
                breach.get("violation_type") or ViolationType.EXPOSURE,
                f"Portfolio risk violation: {message}",
                threshold_value=breach.get("threshold_value"),
                actual_value=breach.get("actual_value"),
                action_taken=breach.get("action_taken") or ViolationAction.BLOCKED,
                severity=breach.get("severity") or Severity.CRITICAL,
            )
            raise ValueError(f"Portfolio risk violation: {message}")

        auto_disable_rules = getattr(strategy, "auto_disable_rules", None)
        if auto_disable_rules:
            auto_disable_eval = evaluator.evaluate_auto_disable_rules(
                auto_disable_rules.filter(is_active=True), strategy_stats
            )
            if auto_disable_eval.get('should_disable'):
                disable_match = auto_disable_eval.get('matches', [{}])[0]
                message = disable_match.get('message', 'Strategy auto-disable triggered')
                PaperExecutionService._record_violation(
                    account.user,
                    strategy,
                    ViolationType.CONSECUTIVE_LOSS,
                    f"Strategy auto-disable triggered: {message}",
                    threshold_value=disable_match.get("threshold"),
                    actual_value=disable_match.get("actual_value"),
                    action_taken=ViolationAction.DISABLED,
                    severity=Severity.CRITICAL,
                )
                if strategy.status == StrategyStatus.ACTIVE:
                    strategy.status = StrategyStatus.PAUSED
                    strategy.save(update_fields=["status", "updated_at"])
                raise ValueError(f"Strategy auto-disable triggered: {message}")

    @staticmethod
    def execute_strategy_order(
        *,
        strategy,
        account,
        instrument,
        side,
        quantity,
        order_type='MARKET',
        price=None,
        trigger_price=None,
        product_type=ProductType.INTRADAY,
        order_tag="strategy_execution",
    ):
        if not strategy:
            raise ValueError("Strategy is required for strategy order execution")
        if account.user != strategy.user:
            raise ValueError("Paper account and strategy user mismatch")

        allocation = CapitalAllocation.objects.filter(portfolio__user=account.user, strategy=strategy).first()
        if not allocation:
            raise ValueError("No portfolio allocation found for this strategy")

        target_price = price
        if target_price is None and order_type == 'MARKET':
            target_price = PaperExecutionService.resolve_market_price(instrument)
        elif target_price is None and trigger_price is not None:
            target_price = Decimal(str(trigger_price))

        if target_price is None:
            raise ValueError("Price cannot be resolved for order")

        PaperExecutionService._validate_risk_for_order(
            strategy=strategy,
            account=account,
            instrument=instrument,
            side=side,
            quantity=quantity,
            target_price=target_price,
        )

        required_capital = Decimal(str(quantity)) * Decimal(str(target_price))
        if allocation.available_amount < required_capital:
            entry_config = _related_or_none(strategy, "entry_order_config")
            allow_partial_entry = bool(getattr(entry_config, "allow_partial_entry", False))
            if not allow_partial_entry:
                raise ValueError(f"Insufficient strategy allocation: required={required_capital}, available={allocation.available_amount}")

            quantity = int(Decimal(str(allocation.available_amount)) / Decimal(str(target_price)))
            if quantity < 1:
                raise ValueError(f"Insufficient strategy allocation: required={required_capital}, available={allocation.available_amount}")
            required_capital = Decimal(str(quantity)) * Decimal(str(target_price))

        if order_type == 'MARKET':
            return PaperExecutionService.execute_market_order(
                account=account, instrument=instrument, strategy=strategy, side=side, quantity=quantity,
                product_type=product_type, order_tag=order_tag, fallback_price=target_price,
            )
        else:
            order = PaperOrder.objects.create(
                account=account, strategy=strategy, instrument=instrument, order_type=order_type,
                product_type=product_type, side=side, quantity=quantity, price=price,
                trigger_price=trigger_price, status=OrderStatus.PENDING, order_tag=order_tag,
            )
            return order

    @staticmethod
    def resolve_market_price(instrument, fallback_price=None):
        return StrategyMarketDataService.get_quote(instrument, fallback_price=fallback_price)

    @staticmethod
    def sync_account(account):
        positions = PaperPosition.objects.filter(account=account)
        unrealized_pnl = sum((Decimal(str(pos.unrealized_pnl or 0)) for pos in positions), Decimal("0"))
        margin_used = sum((Decimal(str(pos.margin_blocked or 0)) for pos in positions), Decimal("0"))
        account.unrealized_pnl = unrealized_pnl
        account.margin_used = margin_used
        account.margin_available = max(Decimal("0"), Decimal(str(account.current_balance)) - margin_used)
        account.total_pnl = Decimal(str(account.realized_pnl)) + unrealized_pnl
        account.save(update_fields=["unrealized_pnl", "margin_used", "margin_available", "total_pnl", "updated_at"])
        return account

    @staticmethod
    @transaction.atomic
    def execute_market_order(
        *,
        account,
        instrument,
        side,
        quantity,
        strategy=None,
        order_type=OrderType.MARKET,
        product_type=ProductType.INTRADAY,
        order_tag="",
        fallback_price=None,
        executed_at=None,
        exit_reason="MANUAL_CLOSE",
    ):
        executed_at = executed_at or timezone.now()
        quantity = int(quantity)
        price = PaperExecutionService.resolve_market_price(instrument, fallback_price=fallback_price)
        order = PaperOrder.objects.create(
            account=account, strategy=strategy, instrument=instrument, order_type=order_type,
            product_type=product_type, side=side, quantity=quantity, price=price,
            avg_fill_price=price, filled_quantity=quantity, status=OrderStatus.FILLED,
            executed_at=executed_at, order_tag=order_tag,
        )

        remaining = quantity
        opposite_side = Side.SELL if side == Side.BUY else Side.BUY
        opposite_position = (
            PaperPosition.objects.filter(account=account, instrument=instrument, side=opposite_side)
            .order_by("opened_at")
            .first()
        )
        strategy_config = None
        if strategy:
            strategy_config = cache.get(f"strategy_config_{strategy.id}") or strategy.to_execution_dict()

        if opposite_position:
            close_quantity = min(opposite_position.quantity, remaining)
            gross_pnl = (
                (price - opposite_position.avg_price) * close_quantity
                if opposite_position.side == Side.BUY
                else (opposite_position.avg_price - price) * close_quantity
            )
            net_pnl = gross_pnl

            PaperTrade.objects.create(
                account=account, strategy=strategy or opposite_position.strategy, instrument=instrument,
                side=opposite_position.side, quantity=close_quantity, entry_price=opposite_position.avg_price,
                entry_time=opposite_position.opened_at, exit_price=price, exit_time=executed_at,
                exit_order=order, exit_reason=exit_reason, gross_pnl=gross_pnl,
                net_pnl=net_pnl,
                pnl_pct=((net_pnl / (opposite_position.avg_price * close_quantity)) * 100) if opposite_position.avg_price else 0,
                holding_duration_seconds=max(int((executed_at - opposite_position.opened_at).total_seconds()), 0),
            )

            margin_released = (
                Decimal(str(opposite_position.margin_blocked or 0))
                * Decimal(str(close_quantity))
                / Decimal(str(opposite_position.quantity))
            )
            account.realized_pnl += net_pnl
            account.today_pnl += net_pnl
            account.current_balance += net_pnl
            opposite_position.quantity -= close_quantity
            opposite_position.margin_blocked = max(Decimal("0"), Decimal(str(opposite_position.margin_blocked)) - margin_released)
            if opposite_position.quantity > 0:
                opposite_position.save(update_fields=["quantity", "margin_blocked", "updated_at"])
                if opposite_position.strategy_id:
                    trade_state = StrategyRuntimeState.mark_open(
                        "paper",
                        opposite_position.strategy_id,
                        opposite_position.instrument_id,
                        position_id=opposite_position.id,
                        side=opposite_position.side,
                        quantity=opposite_position.quantity,
                        avg_price=opposite_position.avg_price,
                        config=cache.get(f"strategy_config_{opposite_position.strategy_id}") or opposite_position.strategy.to_execution_dict(),
                        opened_at=opposite_position.opened_at,
                    )
                    StrategyRuntimeState.update_position_state(
                        "paper-position",
                        opposite_position.id,
                        {
                            "phase": trade_state.get("phase"),
                            "entry_time": trade_state.get("entry_time"),
                            "protected_stop_price": trade_state.get("protected_stop_price"),
                            "protected_target_price": trade_state.get("protected_target_price"),
                        },
                    )
            else:
                if opposite_position.strategy_id:
                    StrategyRuntimeState.mark_closed(
                        "paper",
                        opposite_position.strategy_id,
                        opposite_position.instrument_id,
                        reason=exit_reason,
                    )
                PaperStrategyEngine._clear_position_state(opposite_position)
                opposite_position.delete()
            remaining -= close_quantity

        if remaining > 0:
            position = PaperPosition.objects.filter(account=account, instrument=instrument, side=side).first()
            if position:
                total_quantity = position.quantity + remaining
                total_cost = (Decimal(str(position.avg_price)) * position.quantity) + (price * remaining)
                if strategy and position.strategy_id is None:
                    position.strategy = strategy
                position.quantity = total_quantity
                position.avg_price = total_cost / total_quantity if total_quantity else price
                position.current_price = price
                position.margin_blocked = Decimal(str(position.margin_blocked)) + (price * remaining)
                position.save(update_fields=["strategy", "quantity", "avg_price", "current_price", "margin_blocked", "last_updated", "updated_at"])
                trade_state = {}
                trade_strategy_id = strategy.id if strategy else position.strategy_id
                if trade_strategy_id:
                    trade_state = StrategyRuntimeState.mark_open(
                        "paper",
                        trade_strategy_id,
                        instrument.id,
                        position_id=position.id,
                        side=position.side,
                        quantity=position.quantity,
                        avg_price=position.avg_price,
                        config=strategy_config or {},
                        opened_at=position.opened_at,
                    )
                StrategyRuntimeState.update_position_state(
                    "paper-position",
                    position.id,
                    {
                        "phase": trade_state.get("phase") if trade_state else StrategyRuntimeState.OPEN,
                        "entry_time": trade_state.get("entry_time") or position.opened_at.isoformat() if position.opened_at else executed_at.isoformat(),
                        "peak_price": float(position.current_price or position.avg_price or price),
                        "protected_stop_price": trade_state.get("protected_stop_price"),
                        "protected_target_price": trade_state.get("protected_target_price"),
                    },
                )
            else:
                position = PaperPosition.objects.create(
                    account=account, strategy=strategy, instrument=instrument, side=side,
                    quantity=remaining, avg_price=price, current_price=price, margin_blocked=price * remaining,
                )
                trade_state = {}
                trade_strategy_id = strategy.id if strategy else position.strategy_id
                if trade_strategy_id:
                    trade_state = StrategyRuntimeState.mark_open(
                        "paper",
                        trade_strategy_id,
                        instrument.id,
                        position_id=position.id,
                        side=position.side,
                        quantity=position.quantity,
                        avg_price=position.avg_price,
                        config=strategy_config or {},
                        opened_at=position.opened_at,
                    )
                StrategyRuntimeState.update_position_state(
                    "paper-position",
                    position.id,
                    {
                        "phase": trade_state.get("phase") if trade_state else StrategyRuntimeState.OPEN,
                        "entry_time": trade_state.get("entry_time") or position.opened_at.isoformat() if position.opened_at else executed_at.isoformat(),
                        "peak_price": float(price),
                        "protected_stop_price": trade_state.get("protected_stop_price"),
                        "protected_target_price": trade_state.get("protected_target_price"),
                    },
                )

        account.today_trades += 1
        account.save(update_fields=["realized_pnl", "today_pnl", "current_balance", "today_trades", "updated_at"])
        PaperExecutionService.sync_account(account)

        allocation = CapitalAllocation.objects.filter(portfolio__user=account.user, strategy=strategy).first()
        if allocation:
            allocation.utilized_amount = PortfolioService._allocation_utilized_amount(allocation)
            allocation.save(update_fields=["utilized_amount", "updated_at"])

        PortfolioService.sync_from_paper_account(account)
        return order

    @staticmethod
    def close_position(position, reason="MANUAL_CLOSE"):
        return PaperExecutionService.execute_market_order(
            account=position.account, instrument=position.instrument, strategy=position.strategy,
            side=Side.SELL if position.side == Side.BUY else Side.BUY, quantity=position.quantity,
            product_type=ProductType.INTRADAY, order_tag="paper_manual_close",
            fallback_price=position.current_price or position.avg_price, exit_reason=reason,
        )

    @staticmethod
    @transaction.atomic
    def fill_pending_order(order, fill_price=None, executed_at=None, exit_reason="Strategy Order Filled"):
        if order.status not in {OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIAL_FILL}:
            return order

        executed_at = executed_at or timezone.now()
        resolved_price = fill_price if fill_price is not None else order.price or order.trigger_price
        if resolved_price is None:
            resolved_price = PaperExecutionService.resolve_market_price(order.instrument)
        fill_price = Decimal(str(resolved_price))
        
        payload = {
            "account": order.account,
            "instrument": order.instrument,
            "strategy": order.strategy,
            "side": order.side,
            "quantity": order.quantity,
            "order_type": order.order_type,
            "product_type": order.product_type,
            "order_tag": order.order_tag or "strategy_fill",
        }
        order.delete()
        return PaperExecutionService.execute_market_order(
            fallback_price=fill_price, executed_at=executed_at, exit_reason=exit_reason, **payload,
        )

    @staticmethod
    def process_pending_strategy_orders(symbol, quote=None, quote_already_cached=False):
        normalized_symbol = MarketDataStreamer.normalize_symbol(symbol)
        if quote and not quote_already_cached:
            MarketDataStreamer.update_quote(normalized_symbol, quote)

        live_price = None
        if quote and quote.get("price") is not None:
            live_price = Decimal(str(quote.get("price")))

        pending_orders = PaperOrder.objects.filter(
            instrument__sym_ticker=normalized_symbol,
            status__in=PaperExecutionService.STRATEGY_ORDER_STATUSES,
        ).select_related("instrument", "strategy", "account")

        processed = False
        for order in pending_orders:
            fill_price = live_price
            if fill_price is None:
                try:
                    fill_price = PaperExecutionService.resolve_market_price(order.instrument, fallback_price=order.price or order.trigger_price)
                except ValueError:
                    continue

            should_fill = False
            if order.order_type == OrderType.MARKET:
                should_fill = True
            elif order.order_type == OrderType.LIMIT:
                if order.side == Side.BUY:
                    should_fill = fill_price <= Decimal(str(order.price or 0))
                else:
                    should_fill = fill_price >= Decimal(str(order.price or 0))
            elif order.order_type in {OrderType.STOP_MARKET, OrderType.STOP_LIMIT}:
                trigger = Decimal(str(order.trigger_price or order.price or 0))
                if order.side == Side.BUY:
                    should_fill = fill_price >= trigger
                else:
                    should_fill = fill_price <= trigger

            if should_fill:
                PaperExecutionService.fill_pending_order(
                    order,
                    fill_price=fill_price,
                    executed_at=timezone.now(),
                )
                processed = True
        return processed


class PaperStrategyEngine:
    """Real-time strategy rule evaluation for paper trading using Unified Executor"""

    @staticmethod
    def _legacy_state_key(position):
        model_label = getattr(getattr(position, "_meta", None), "db_table", "paper_position")
        position_id = getattr(position, "id", position)
        return f"paper:position-state:{model_label}:{position_id}"

    @staticmethod
    def _clear_position_state(position):
        cache.delete(PaperStrategyEngine._legacy_state_key(position))
        position_id = getattr(position, "id", position)
        StrategyRuntimeState.clear_position_state("paper-position", position_id)

    @staticmethod
    def _get_strategy_runtime_stats(strategy, account, instrument, timestamp, entry_side=None):
        if entry_side is None:
            try:
                config = cache.get(f"strategy_config_{strategy.id}") or strategy.to_execution_dict()
                entry_side = (config.get("entry_order_config") or {}).get("entry_side", Side.BUY)
            except Exception:
                entry_side = Side.BUY
        latest_exit = PaperTrade.objects.filter(account=account, strategy=strategy, instrument=instrument).order_by("-exit_time").first()
        latest_entry = (
            PaperOrder.objects.filter(
                account=account,
                strategy=strategy,
                instrument=instrument,
                side=entry_side,
                status=OrderStatus.FILLED,
            )
            .exclude(executed_at__isnull=True)
            .order_by("-executed_at")
            .first()
        )
        total_today_trades = PaperTrade.objects.filter(account=account, strategy=strategy, exit_time__date=timestamp.date()).count()
        instrument_today_trades = PaperTrade.objects.filter(account=account, strategy=strategy, instrument=instrument, exit_time__date=timestamp.date()).count()

        return {
            "daily_trades": total_today_trades,
            "instrument_daily_trades": instrument_today_trades,
            "last_exit_time": latest_exit.exit_time if latest_exit else None,
            "last_entry_time": latest_entry.executed_at if latest_entry else None,
        }


    @staticmethod
    def _get_multi_timeframe_data(config, instrument):
        return StrategyMarketDataService.get_multi_timeframe_data(config, instrument)

    @staticmethod
    def execute_live_strategy(strategy, account=None, symbol=None):
        if not strategy.paper_trading_enabled or strategy.status != StrategyStatus.ACTIVE:
            return False

        if account is None:
            account = PortfolioService.ensure_paper_account_for_strategy(PortfolioService.get_or_create_portfolio(strategy.user), strategy)

        from strategy_engine.executor import StrategyExecutor
        config = cache.get(f"strategy_config_{strategy.id}") or strategy.to_execution_dict()
        executor = StrategyExecutor(config)
        
        timestamp = timezone.now()
        no_trade_zone = executor.is_in_no_trade_zone(timestamp)

        watchlist = strategy.watchlist_instruments.select_related('instrument')
        if symbol:
            watchlist = watchlist.filter(instrument__sym_ticker=symbol)

        refreshed = False
        for watch in watchlist:
            instrument = watch.instrument

            try:
                with StrategyRuntimeState.execution_lock("paper", strategy.id, instrument.id):
                    trade_state = StrategyRuntimeState.trade_state("paper", strategy.id, instrument.id)
                    base_timeframe, mtf_data = PaperStrategyEngine._get_multi_timeframe_data(config, instrument)
                    candle_df = mtf_data.get(base_timeframe)
                    if candle_df is None or candle_df.empty:
                        continue

                    executor = StrategyExecutor(config, mtf_data=mtf_data)

                    last_price = float(candle_df['close'].iloc[-1])
                    signal_df = executor.completed_signal_frame(candle_df)
                    if signal_df is None or signal_df.empty:
                        continue
                    from django.db import models
                    position = PaperPosition.objects.filter(
                        account=account, strategy=strategy
                    ).filter(
                        models.Q(instrument=instrument) |
                        models.Q(instrument__underlying_symbol=instrument.symbol)
                    ).first()
                    entry_side = executor.entry_config.get("entry_side", Side.BUY)
                    stats = PaperStrategyEngine._get_strategy_runtime_stats(
                        strategy,
                        account,
                        instrument,
                        timestamp,
                        entry_side=entry_side,
                    )

                    if position:
                        state = StrategyRuntimeState.build_position_state(
                            config=config,
                            position=position,
                            side=position.side,
                            avg_price=position.avg_price,
                            current_price=position.current_price or position.avg_price,
                            opened_at=position.opened_at,
                            identifier=position.id,
                            scope="paper-position",
                        )
                        should_exit, reason = executor.evaluate_exit_logic(state, candle_df, timestamp)
                        
                        # Check for reverse entry if enabled
                        reverse_enabled = config.get("reentry_rule", {}).get("allow_reverse_entry", False)
                        if not should_exit and reverse_enabled and not no_trade_zone:
                            entry_signals = executor.evaluate_entry_signals(signal_df)
                            if entry_signals.iloc[-1]:
                                if entry_side != position.side:
                                    should_exit = True
                                    reason = "Reverse Entry Signal"
                        
                        StrategyRuntimeState.update_position_state(
                            "paper-position",
                            position.id,
                            {
                                "trailing_stop": state.get("trailing_stop"),
                                "peak_price": state.get("peak_price"),
                            },
                        )

                        if should_exit:
                            StrategyRuntimeState.mark_exit_pending(
                                "paper",
                                strategy.id,
                                instrument.id,
                                reason=reason,
                            )
                            PaperExecutionService.close_position(position, reason=reason)
                            PaperStrategyEngine._clear_position_state(position)
                            refreshed = True
                            # If it was a reverse entry, we allow re-entry in the same tick
                            if reason == "Reverse Entry Signal":
                                position = None

                    if not position:  # Using if not position because it might have been set to None above
                        if no_trade_zone:
                            continue

                        evaluator = RiskEvaluator(account.current_balance)
                        
                        # Check Strategy-specific limits (Max trades, Max positions)
                        ok, msg = evaluator.check_strategy_limits(config, stats)
                        if not ok: continue
                        
                        # Check Portfolio-wide risk
                        ok, msg = evaluator.check_portfolio_risk(config.get("risk_profile", {}), stats)
                        if not ok: continue

                        can_enter, reason = executor.can_enter(stats, timestamp)
                        if not can_enter: continue
                        if trade_state.get("phase") in {StrategyRuntimeState.ENTRY_PENDING, StrategyRuntimeState.EXIT_PENDING}:
                            continue

                        signals = executor.evaluate_entry_signals(signal_df)
                        if signals.iloc[-1]:
                            # Step 1: Resolve execution instrument
                            from instruments.services import InstrumentResolver
                            exec_instrument, exec_side = InstrumentResolver.resolve(
                                watch, entry_side, spot_price=float(last_price)
                            )

                            # Step 2: Iterate over each resolution
                            for exec_instrument, exec_side, sizing_config in resolutions:
                                from marketdata.access import StrategyMarketDataService
                                exec_price = StrategyMarketDataService.get_quote(exec_instrument, fallback_price=last_price)
                                lot_size = getattr(exec_instrument, 'lot_size', 1) or 1
    
                                if not sizing_config:
                                    sizing_config = config
    
                                # Step 4: Calculate quantity
                                quantity = evaluator.calculate_quantity(sizing_config, exec_price, stats=stats, lot_size=lot_size)
    
                                if PaperOrder.objects.filter(
                                    account=account,
                                    strategy=strategy,
                                    instrument=exec_instrument,
                                    status__in=PaperExecutionService.STRATEGY_ORDER_STATUSES,
                                ).exists():
                                    continue
    
                                current_candle = candle_df.iloc[-1] if executor.candle_completion_rule in ("ON_CLOSE", "ON_OPEN") else signal_df.iloc[-1]
                                order_type, resolved_entry_price, trigger_price = executor.resolve_entry_order(
                                    signal_df.iloc[-1],
                                    execution_candle=current_candle,
                                )
                                
                                # Force market if instrument changed
                                if exec_instrument.id != instrument.id:
                                    order_type = OrderType.MARKET
                                    resolved_entry_price = exec_price
                                    trigger_price = None
    
                                StrategyRuntimeState.mark_entry_pending(
                                    "paper",
                                    strategy.id,
                                    instrument.id,
                                    side=exec_side,
                                    order_type=order_type,
                                    requested_price=float(resolved_entry_price) if resolved_entry_price is not None else None,
                                    trigger_price=float(trigger_price) if trigger_price is not None else None,
                                )
                                order = PaperExecutionService.execute_strategy_order(
                                    strategy=strategy,
                                    account=account,
                                    instrument=exec_instrument,
                                    side=exec_side,
                                    quantity=max(int(quantity), 1),
                                    order_type=order_type,
                                    price=Decimal(str(resolved_entry_price)) if resolved_entry_price is not None else None,
                                    trigger_price=Decimal(str(trigger_price)) if trigger_price is not None else None,
                                    order_tag=f"strategy_entry_{timestamp.strftime('%H%M%S')}",
                                )
                                StrategyRuntimeState.mark_entry_pending(
                                    "paper",
                                    strategy.id,
                                    instrument.id,
                                    side=exec_side,
                                    order_id=getattr(order, "id", None),
                                    order_type=order_type,
                                    requested_price=float(resolved_entry_price) if resolved_entry_price is not None else None,
                                    trigger_price=float(trigger_price) if trigger_price is not None else None,
                                )
                                refreshed = True
            except RuntimeError as e:
                logger.warning(f"Paper execution lock skipped for {strategy.name} - {instrument.sym_ticker}: {e}")

        if refreshed:
            PaperExecutionService.sync_account(account)
        return refreshed

    @staticmethod
    def execute_live_tick(symbol, quote=None, quote_already_cached=False):
        normalized_symbol = MarketDataStreamer.normalize_symbol(symbol)
        if quote and not quote_already_cached:
            MarketDataStreamer.update_quote(normalized_symbol, quote)

        processed = PaperExecutionService.process_pending_strategy_orders(
            normalized_symbol,
            quote=quote,
            quote_already_cached=quote_already_cached,
        )

        strategies = Strategy.objects.filter(
            paper_trading_enabled=True,
            status=StrategyStatus.ACTIVE,
            capital_allocation__is_active=True,
            watchlist_instruments__instrument__sym_ticker=normalized_symbol,
        ).distinct()

        for strategy in strategies:
            try:
                result = PaperStrategyEngine.execute_live_strategy(strategy, symbol=normalized_symbol)
                processed = processed or bool(result)
            except Exception:
                logger.exception('Error running live strategy %s for symbol %s', strategy.name, normalized_symbol)

        return processed
