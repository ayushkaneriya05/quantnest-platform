
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from brokers.models import BrokerCredential
from brokers.services import BrokerService
from common.enums import OrderStatus, NotificationType
from execution.order_reports import ACTIVE
from notifications.services import NotificationService
from execution.lifecycle import request_session_refresh

from .models import ExecutionLog, LiveOrder, LivePosition, LiveStrategyAllocation, LiveTrade, SlippageRecord, TradingSession

logger = logging.getLogger(__name__)


class LiveExecutionService:
    """Live deployment commands, broker funds and read-only summaries.

    Numerical decisions and financial fills belong to the shared execution kernel.
    """

    @staticmethod
    @transaction.atomic
    def update_allocation(allocation, allocation_amount: Decimal):
        if not allocation:
            raise ValueError('Allocation not found')
        funds = LiveExecutionService.sync_funds(allocation.broker_credential)
        BrokerCredential.objects.select_for_update().get(pk=allocation.broker_credential_id)
        allocation = LiveStrategyAllocation.objects.select_for_update().get(pk=allocation.pk)
        values = LiveExecutionService._allocation_terms(allocation.broker_credential, funds,
            allocation_amount, exclude_id=allocation.pk)
        committed = max(allocation.invested_value + allocation.reserved_capital - allocation.realized_pnl, Decimal('0'))
        if values['allocated_capital'] < committed:
            raise ValueError('Allocation cannot be reduced below committed position and order capital')
        from execution.models import Command
        from execution.repository import enqueue
        from common.enums import ExecutionMode, ExecutionCommandType
        if Command.objects.filter(mode=ExecutionMode.LIVE, account_id=allocation.broker_credential_id,
                applied_at__isnull=True, payload__has_key='allocation_changes').exists():
            raise ValueError('Wait for the previous capital change to finish.')
        enqueue(ExecutionMode.LIVE, allocation.broker_credential_id, ExecutionCommandType.REFRESH,
            {'session_id': allocation.session.pk, 'allocation_changes': values})
        return allocation


    @staticmethod
    def _allocation_terms(credential, funds, amount: Decimal, exclude_id=None):
        equity = Decimal(funds["net_equity"])
        if equity <= 0:
            raise ValueError("Fresh positive broker equity is required.")
        others = LiveStrategyAllocation.objects.filter(broker_credential=credential).exclude(pk=exclude_id)
        allocated = others.aggregate(total=Sum("allocated_capital"))["total"] or Decimal("0")
        if allocated + amount > equity:
            raise ValueError("Allocation exceeds broker equity remaining after other allocations.")
        return {"allocated_capital": amount, "broker_equity_reference": equity}

    @staticmethod
    @transaction.atomic
    def deploy_session(user, strategy, version, allocation_amount: Decimal, broker_credential):
        """Admit and create one strategy/broker deployment atomically."""
        from execution.lifecycle import require_execution_scope
        from common.enums import ExecutionScope
        from strategies.models import Strategy
        from strategies.services import StrategyDeploymentService
        require_execution_scope(ExecutionScope.LIVE)
        if not user.is_active or strategy.user_id != user.pk or broker_credential.user_id != user.pk:
            raise ValueError("Select your own active user account, strategy and broker account.")
        if version.strategy_id != strategy.pk:
            raise ValueError("Select a saved version of this strategy.")
        BrokerCredential.objects.select_for_update().get(pk=broker_credential.pk)
        strategy = Strategy.objects.select_for_update().get(pk=strategy.pk)
        if strategy.status != "ACTIVE" or not strategy.live_trading_enabled:
            raise ValueError("Activate this strategy and enable Live trading before deployment.")
        if LiveStrategyAllocation.objects.filter(strategy=strategy, broker_credential=broker_credential).exists():
            raise ValueError("A live deployment already exists for this strategy and broker account. Manage the existing session.")
        StrategyDeploymentService.validate_snapshot(version.config_snapshot, "live")
        BrokerService.ensure_session(broker_credential)
        funds = LiveExecutionService.sync_funds(broker_credential)
        allocation = LiveStrategyAllocation.objects.create(
            user=user, strategy=strategy, broker_credential=broker_credential, deployed_version=version,
            **LiveExecutionService._allocation_terms(broker_credential, funds, allocation_amount),
        )
        session = TradingSession.objects.create(
            user=user, strategy=strategy, broker_credential=broker_credential, allocation=allocation,
            status="RUNNING", started_at=timezone.now(),
        )
        request_session_refresh("live", session)
        NotificationService.notify(
            user=user, title="Live strategy deployed",
            message=f"Strategy '{strategy.name}' has been deployed to Live trading.",
            type=NotificationType.INFO,
            data={"session_id": str(session.pk), "strategy_id": str(strategy.pk),
                  "strategy_name": strategy.name, "module": "live"},
            dedupe_key=f"live-session:{session.pk}:RUNNING:{session.updated_at.isoformat()}",
        )
        return session

    @staticmethod
    @transaction.atomic
    def pause_session(session):
        session = TradingSession.objects.select_for_update().get(pk=session.pk)
        if session.status != 'RUNNING':
            raise ValueError('Only running sessions can be paused.')
        session.status = "PAUSED"
        session.error_message = ""
        session.save(update_fields=["status", "error_message", "updated_at"])

        NotificationService.notify(
            user=session.user,
            title="Live Strategy Paused",
            message=f"Strategy '{session.strategy.name}' has been paused.",
            type=NotificationType.WARNING,
            data={"session_id": str(session.id), "strategy_id": str(session.strategy_id), "strategy_name": session.strategy.name, "module": "live"},
            dedupe_key=f"live-session:{session.id}:PAUSED:{session.updated_at.isoformat()}"
        )
        request_session_refresh("live", session)
        return session


    @staticmethod
    @transaction.atomic
    def stop_session(session, close_positions=False):
        session = TradingSession.objects.select_for_update().get(pk=session.pk)
        session.status, session.error_message, session.ended_at = "STOPPING", "", None
        session.save(update_fields=["status", "error_message", "ended_at", "updated_at"])
        request_session_refresh("live", session, close_positions=close_positions)
        return session

    @staticmethod
    @transaction.atomic
    def resume_session(session):
        from execution.lifecycle import require_execution_scope
        from common.enums import ExecutionScope
        require_execution_scope(ExecutionScope.LIVE)
        BrokerService.ensure_session(session.broker_credential)
        LiveExecutionService.sync_funds(session.broker_credential)
        BrokerCredential.objects.select_for_update().get(pk=session.broker_credential_id)
        LiveStrategyAllocation.objects.select_for_update().get(pk=session.allocation_id)
        session = TradingSession.objects.select_for_update().get(pk=session.pk)
        if session.status not in {'PAUSED', 'STOPPED', 'ERROR'}:
            raise ValueError('Only paused, stopped or failed sessions can be resumed.')
        from strategies.services import StrategyDeploymentService
        StrategyDeploymentService.validate_snapshot(session.allocation.deployed_version.config_snapshot, 'live')
        if session.strategy.status != 'ACTIVE' or not session.strategy.live_trading_enabled:
            raise ValueError('Activate the strategy and enable live trading before resuming this session.')
        was_stopped = session.status == "STOPPED"

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
            type=NotificationType.INFO,
            data={"session_id": str(session.id), "strategy_id": str(session.strategy_id), "strategy_name": session.strategy.name, "module": "live"},
            dedupe_key=f"live-session:{session.id}:RUNNING:{session.updated_at.isoformat()}"
        )
        request_session_refresh("live", session)
        return session

    @staticmethod
    @transaction.atomic
    def _refresh_broker_allocation_health(credential):
        """Refresh warnings in one pass; unchanged allocations need no write."""
        from brokers.models import BrokerFundsSnapshot
        BrokerCredential.objects.select_for_update().get(pk=credential.pk)
        funds = BrokerFundsSnapshot.objects.filter(credential=credential).first()
        if funds is None:
            return
        equity, cumulative = funds.net_equity, Decimal('0')
        changed = []
        allocations = LiveStrategyAllocation.objects.filter(broker_credential=credential).select_related(
            'session', 'strategy', 'user').order_by('created_at', 'pk')
        for allocation in allocations:
            previous = allocation.is_over_allocated
            running = getattr(allocation, 'session', None) is not None and allocation.session.status != 'STOPPED'
            if running:
                cumulative += allocation.allocated_capital
            over = running and cumulative > equity
            reason = (f'Cumulative allocation ({cumulative}) exceeds broker equity ({equity}).'
                      if over else '')
            values = (over, reason, equity)
            if values == (allocation.is_over_allocated, allocation.breach_reason, allocation.broker_equity_reference):
                continue
            allocation.is_over_allocated, allocation.breach_reason, allocation.broker_equity_reference = values
            allocation.updated_at = timezone.now()
            changed.append(allocation)
            if over and not previous:
                try:
                    NotificationService.notify(user=allocation.user, title='Live Allocation Over-allocated',
                        message=f"Allocation for '{allocation.strategy.name}' exceeds broker equity. {reason}",
                        type=NotificationType.CRITICAL,
                        data={'allocation_id': str(allocation.pk), 'broker_credential_id': str(credential.pk),
                              'strategy_id': str(allocation.strategy_id), 'strategy_name': allocation.strategy.name,
                              'cumulative_allocated': str(cumulative), 'broker_equity': str(equity), 'module': 'live'})
                except Exception:
                    logger.exception('Failed dispatching over-allocation notification for allocation %s', allocation.pk)
        LiveStrategyAllocation.objects.bulk_update(changed,
            ['is_over_allocated', 'breach_reason', 'broker_equity_reference', 'updated_at'])


    @staticmethod
    def sync_funds(credential):
        """Fetch fresh funds and cache - uses BrokerService abstraction."""
        from execution.models import AccountCheckpoint
        from execution.repository import enqueue
        from common.enums import ExecutionCommandType, ExecutionMode
        revision = AccountCheckpoint.objects.filter(mode=ExecutionMode.LIVE, account_id=credential.pk).values_list("revision", flat=True).first() or 0
        requested_at = timezone.now()
        funds_payload = BrokerService.get_funds(credential)
        snapshot = BrokerService.record_funds_snapshot(credential, funds_payload)
        payload = {
            "snapshot_id": snapshot.id,
            "cash_balance": str(snapshot.cash_balance),
            "available_margin": str(snapshot.available_margin),
            "used_margin": str(snapshot.used_margin),
            "collateral": str(snapshot.collateral),
            "withdrawable_balance": str(snapshot.withdrawable_balance) if snapshot.withdrawable_balance is not None else None,
            "net_equity": str(snapshot.net_equity),
            "realized_pnl": str(snapshot.realized_pnl),
            "unrealized_pnl": str(snapshot.unrealized_pnl) if snapshot.unrealized_pnl is not None else None,
            "snapshot_time": snapshot.snapshot_time.isoformat(),
        }
        enqueue(ExecutionMode.LIVE, credential.pk, ExecutionCommandType.FUNDS,
            {"equity": str(snapshot.net_equity), "available": str(snapshot.available_margin),
             "at": requested_at.isoformat(), "revision": revision})
        return payload


    @staticmethod
    def session_summary(user):
        """Return a read-only snapshot; broker I/O runs in the funds sync task."""
        today = timezone.localdate()
        sessions = TradingSession.objects.filter(user=user)
        positions = LivePosition.objects.filter(user=user, quantity__gt=0)
        orders = LiveOrder.objects.filter(user=user)
        session_counts = sessions.aggregate(
            running=Count('id', filter=Q(status='RUNNING')),
            paused=Count('id', filter=Q(status='PAUSED')),
            errors=Count('id', filter=Q(status='ERROR')),
            brokers=Count('broker_credential', distinct=True),
        )
        credential_ids = list(BrokerCredential.objects.filter(user=user, is_active=True).values_list("pk", flat=True))
        health_by_key = cache.get_many([f"live_ws_health:{pk}" for pk in credential_ids])
        broker_summaries = []
        for credential_id in credential_ids:
            health = health_by_key.get(f"live_ws_health:{credential_id}") or {}
            status = health.get("status", "unknown")
            updated_at = parse_datetime(health.get("updated_at", ""))
            if status not in {"authentication_required", "unknown"} and (
                not updated_at or (timezone.now() - updated_at).total_seconds() > 90
            ):
                status = "unknown"
            broker_summaries.append({"credential_id": credential_id, "order_websocket_status": status})

        closed_trades = LiveTrade.objects.filter(user=user)
        closed_trade_stats = closed_trades.aggregate(
            total=Count("id"),
            winning=Count("id", filter=Q(realized_pnl__gt=0)),
            losing=Count("id", filter=Q(realized_pnl__lt=0)),
            realized=Sum("realized_pnl"),
            realized_today=Sum('realized_pnl', filter=Q(exit_time__date=today)),
            today=Count('id', filter=Q(exit_time__date=today)),
            winning_today=Count('id', filter=Q(exit_time__date=today, realized_pnl__gt=0)),
        )
        realized_pnl = closed_trade_stats["realized"] or Decimal("0")
        realized_today = closed_trade_stats['realized_today'] or Decimal('0')
        avg_execution_latency = ExecutionLog.objects.filter(order__user=user, latency_ms__gt=0).aggregate(value=Avg("latency_ms"))["value"]
        avg_slippage = SlippageRecord.objects.filter(order__user=user).aggregate(value=Avg("slippage_pct"))["value"]
        order_counts = orders.aggregate(
            total=Count('id'),
            today=Count('id', filter=Q(placed_at__date=today)),
            today_fills=Count('id', filter=Q(placed_at__date=today, filled_quantity__gt=0)),
            filled=Count("id", filter=Q(status=OrderStatus.FILLED)),
            partial=Count("id", filter=Q(status=OrderStatus.PARTIAL_FILL)),
            active=Count("id", filter=Q(status__in=ACTIVE)),
            rejected=Count("id", filter=Q(status=OrderStatus.REJECTED)),
            cancelled=Count("id", filter=Q(status=OrderStatus.CANCELLED)),
            expired=Count("id", filter=Q(status=OrderStatus.EXPIRED)),
            unknown=Count("id", filter=Q(status="UNKNOWN")),
        )
        position_counts = positions.aggregate(
            total=Count('id'),
            unrealized=Sum("unrealized_pnl"),
            profitable=Count("id", filter=Q(unrealized_pnl__gt=0)),
            losing=Count("id", filter=Q(unrealized_pnl__lt=0)),
        )
        return {
            "generated_at": timezone.now().isoformat(),
            "running_sessions": session_counts['running'],
            "paused_sessions": session_counts['paused'],
            "error_sessions": session_counts['errors'],
            "open_positions": position_counts['total'],
            "open_orders": order_counts["active"],
            "rejected_orders": order_counts["rejected"],
            "total_orders": order_counts['total'],
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
            "today_orders": order_counts['today'],
            "today_fills": order_counts['today_fills'],
            "unrealized_pnl": str(position_counts["unrealized"] or Decimal("0")),
            "realized_pnl": str(realized_pnl),
            "realized_today": str(realized_today),
            "day_pnl": str(realized_today + (position_counts["unrealized"] or Decimal("0"))),
            "closed_trades_today": closed_trade_stats['today'],
            "winning_trades_today": closed_trade_stats['winning_today'],
            "avg_execution_latency_ms": avg_execution_latency,
            "avg_slippage_pct": avg_slippage,
            "active_brokers": session_counts['brokers'],
            "broker_accounts": broker_summaries,
        }

