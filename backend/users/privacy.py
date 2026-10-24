"""Owned, bounded exports and safe account shutdown preconditions."""
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from commercial.usage import reject_request


def shutdown_account(user, *, erase=False):
    """Freeze account admission under the same locks as execution; never force exits."""
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.utils import timezone
    from brokers.models import BrokerCredential, BrokerSession
    from paper_trading.models import PaperAccount, PaperTradingSession
    from live_trading.models import TradingSession
    from trading.models import Account
    from backtesting.models import BacktestRun, MonteCarloRun
    from execution.lifecycle import request_session_refresh
    from commercial.models import UsageReservation
    from commercial.usage import settle_usage
    from users.sessions import revoke_sessions
    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(pk=user.pk)
        list(BrokerCredential.objects.select_for_update().filter(user=user).order_by("pk"))
        list(PaperAccount.objects.select_for_update().filter(user=user).order_by("pk"))
        list(Account.objects.select_for_update().filter(user=user).order_by("pk"))
        require_settled_account(user)
        from commercial.models import Subscription
        if Subscription.objects.filter(user=user, cancel_at_end=False).exclude(provider_id__isnull=True).exclude(provider_id="").exists():
            reject_request("account_renewal_active", "Cancel automatic renewal in Billing and Usage before disabling or deleting your account.")
        user.is_active = False
        for scope, model in (("paper", PaperTradingSession), ("live", TradingSession)):
            for session in model.objects.select_for_update().filter(user=user).exclude(status="STOPPED").order_by("pk"):
                session.status, session.ended_at, session.error_message = "STOPPED", timezone.now(), "Account disabled."
                session.save(update_fields=["status", "ended_at", "error_message", "updated_at"])
                request_session_refresh(scope, session)
        BrokerCredential.objects.filter(user=user).update(is_active=False)
        BrokerSession.objects.filter(credential__user=user).update(is_valid=False)
        BacktestRun.objects.filter(user=user, status__in=["PENDING", "QUEUED", "RUNNING"]).update(status="CANCELLED")
        MonteCarloRun.objects.filter(backtest_run__user=user, status__in=["PENDING", "QUEUED", "RUNNING"]).update(status="CANCELLED")
        from research.models import ResearchRun
        ResearchRun.objects.filter(user=user, status__in=["QUEUED", "RUNNING", "PENDING"]).update(status="CANCELLED")
        # Cancellation refunds each outstanding reservation once.
        for reservation in UsageReservation.objects.filter(user=user, state="reserved"):
            settle_usage(reservation, failed=True)
        revoke_sessions(user)
        if erase:
            from allauth.account.models import EmailAddress
            from allauth.socialaccount.models import SocialAccount
            from django_otp import devices_for_user
            from users.models import BackupCode
            from strategies.models import Strategy
            from customer_support.models import ErasureRequest
            ErasureRequest.objects.get_or_create(user=user)
            EmailAddress.objects.filter(user=user).delete()
            SocialAccount.objects.filter(user=user).delete()
            BackupCode.objects.filter(user=user).delete()
            for device in devices_for_user(user):
                device.delete()
            BrokerSession.objects.filter(credential__user=user).update(access_token="")
            BrokerCredential.objects.filter(user=user).update(api_secret="")
            Strategy.objects.filter(user=user).update(visibility="PRIVATE")
            avatar = user.avatar
            if avatar:
                transaction.on_commit(lambda: avatar.storage.delete(avatar.name))
            user.avatar = None
            user.email = f"deleted_{user.pk}@example.invalid"
            user.username = f"deleted_user_{user.pk}"
            user.first_name = user.last_name = user.bio = ""
            user.is_2fa_enabled = False
            user.set_unusable_password()
        user.save()
        return user


def get_account_exposure(user):
    from live_trading.models import LivePosition, LiveOrder
    from paper_trading.models import PaperPosition, PaperOrder
    from trading.models import Position, Order
    return {
        "live_positions": LivePosition.objects.filter(user=user, quantity__gt=0).count(),
        "live_orders": LiveOrder.objects.filter(user=user, status__in=["PENDING", "PLACED", "PARTIAL_FILL", "UNKNOWN"]).count(),
        "paper_positions": PaperPosition.objects.filter(account__user=user, quantity__gt=0).count(),
        "paper_orders": PaperOrder.objects.filter(account__user=user, status__in=["PENDING", "PLACED", "PARTIAL_FILL", "UNKNOWN"]).count(),
        "terminal_positions": Position.objects.filter(account__user=user).exclude(quantity=0).count(),
        "terminal_orders": Order.objects.filter(account__user=user, status="OPEN").count(),
    }


def require_settled_account(user):
    """Require settled positions and orders before account shutdown."""
    exposure = get_account_exposure(user)
    if any(exposure.values()):
        reject_request("account_execution_active", "Settle open exposure and pending orders before disabling or deleting the account. Protective execution remains available.", resources=exposure)


class ExportThrottle(UserRateThrottle):
    rate = "2/day"
    scope = "account-export"


class AccountExportView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ExportThrottle]
    def post(self, request):
        from strategies.models import Strategy
        from strategies.services import StrategySnapshotService
        from research.models import ResearchRun
        from trade_journal.models import JournalEntry
        from commercial.models import Invoice, RefundRequest
        from customer_support.models import Ticket
        from backtesting.models import BacktestRun, BacktestTrade, MonteCarloRun, MonteCarloResult
        from strategies.models import StrategyVersion
        from trading.models import Order, Position, ClosedPositionLog
        from paper_trading.models import PaperOrder, PaperPosition, PaperTrade
        from live_trading.models import LiveOrder, LivePosition, LiveTrade
        user = request.user
        queries = {
            "research": ResearchRun.objects.filter(user=user).values("id", "session_id", "prompt", "request", "result", "evidence", "status", "as_of"),
            "invoices": Invoice.objects.filter(user=user).values("number", "snapshot", "issued_at"),
            "refunds": RefundRequest.objects.filter(user=user).values("id", "reason", "status", "credit_note", "created_at"),
            "support": Ticket.objects.filter(user=user).values("id", "request_type", "subject", "body", "status", "created_at"),
            "journal": JournalEntry.objects.filter(user=user).values("id", "source", "title", "notes", "mistake_tags", "lessons_learned", "execution_quality"),
            "strategy_versions": StrategyVersion.objects.filter(strategy__user=user).values("id", "strategy_id", "version_number", "config_snapshot", "change_notes", "created_at"),
            "backtests": BacktestRun.objects.filter(user=user).values("id", "strategy_id", "name", "status", "start_date", "end_date", "config_snapshot", "parameters", "initial_capital", "data_quality", "diagnostics"),
            "backtest_trades": BacktestTrade.objects.filter(run__user=user).values(),
            "monte_carlo": MonteCarloRun.objects.filter(backtest_run__user=user).values(),
            "monte_carlo_results": MonteCarloResult.objects.filter(monte_carlo_run__backtest_run__user=user).values(),
            "terminal_orders": Order.objects.filter(account__user=user).values(),
            "terminal_positions": Position.objects.filter(account__user=user).values(),
            "terminal_closes": ClosedPositionLog.objects.filter(account__user=user).values(),
            "paper_orders": PaperOrder.objects.filter(account__user=user).values(),
            "paper_positions": PaperPosition.objects.filter(account__user=user).values(),
            "paper_trades": PaperTrade.objects.filter(account__user=user).values(),
            "live_orders": LiveOrder.objects.filter(user=user).values("id", "session_id", "instrument_id", "side", "quantity", "filled_quantity", "avg_fill_price", "status", "intent", "created_at", "updated_at"),
            "live_positions": LivePosition.objects.filter(user=user).values("id", "instrument_id", "side", "quantity", "avg_price"),
            "live_trades": LiveTrade.objects.filter(user=user).values(),
        }
        if any(query.count() > 1000 for query in queries.values()) or Strategy.objects.filter(user=user).count() > 100:
            reject_request("export_range_required", "This account needs a scoped export. Contact support for a bounded export of the remaining records.")
        data = {name: list(query) for name, query in queries.items()}
        data["account"] = {"username": user.username, "email": user.email, "first_name": user.first_name, "last_name": user.last_name}
        data["strategies"] = [StrategySnapshotService._serialize_strategy(row) for row in Strategy.objects.filter(user=user)]
        content = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False).encode()
        if len(content) > 10 * 1024 * 1024:
            reject_request("export_size_limit", "The export exceeds 10 MiB. Request a scoped export through support.")
        response = HttpResponse(content, content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="quantnest-account-export.json"'
        response["Cache-Control"] = "no-store"
        return response
