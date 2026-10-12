from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from notifications.models import Notification
from common.models import RuntimeOutbox
from strategies.models import Strategy, StrategyVersion
from instruments.models import Instrument
from .models import CapitalAllocation, FundTransaction, PaperAccount, PaperTradingSession, Portfolio
from .services import PaperExecutionService


class PaperAccountTransactionTests(TransactionTestCase):
    """Use autocommit so PostgreSQL catches row locks outside transactions."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="paper-transactions")
        self.strategy = Strategy.objects.create(
            user=self.user, name="Paper strategy", status="ACTIVE", paper_trading_enabled=True,
            auto_version_enabled=False,
        )
        instrument = Instrument.objects.create(fy_token="paper-transaction-fixture", symbol="FIXTURE",
            sym_ticker="NSE:FIXTURE-EQ", name="Fixture", exchange="NSE", instrument_type="STOCK")
        version = StrategyVersion.objects.get(strategy=self.strategy, version_number=1)
        version.config_snapshot["watchlist_instruments"] = [{"instrument_id": instrument.pk,
            "execution_routes": [{"route_type": "DIRECT"}]}]
        version.save(update_fields=["config_snapshot"])
        self.portfolio = Portfolio.objects.create(user=self.user, current_capital=1000)
        self.allocation = CapitalAllocation.objects.create(
            portfolio=self.portfolio, strategy=self.strategy, allocated_amount=200, deployed_version=version,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.funds = self.enterContext(patch("paper_trading.services.cache_api.update_session_funds"))

    def account(self, linked=True, balance=200):
        return PaperAccount.objects.create(
            user=self.user, allocation=self.allocation if linked else None,
            initial_balance=200, current_balance=balance,
        )

    def deploy(self, account):
        return PaperExecutionService.deploy_session(
            self.user, self.strategy, self.allocation, account, include_charges=False,
        )

    def test_create_account_and_stopped_session_from_autocommit(self):
        self.assertFalse(connection.in_atomic_block)
        response = self.client.post("/api/v1/portfolio/portfolios/create_paper_account/", {
            "allocation_id": self.allocation.pk, "name": "Test account", "include_charges": False,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        account = PaperAccount.objects.get(allocation=self.allocation)
        session = PaperTradingSession.objects.get(account=account)
        self.assertEqual(session.status, "STOPPED")
        self.assertEqual(account.current_balance, Decimal("200"))
        self.funds.assert_not_called()
        self.assertTrue(RuntimeOutbox.objects.filter(topic="cache", payload__method="update_session_funds").exists())
        self.assertFalse(RuntimeOutbox.objects.filter(topic="control").exists())

    def test_failed_deployment_rolls_back_new_account(self):
        response = self.client.post("/api/v1/portfolio/portfolios/create_paper_account/", {
            "allocation_id": self.allocation.pk, "slippage_pct": -1,
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(PaperAccount.objects.exists())
        self.assertFalse(PaperTradingSession.objects.exists())
        self.assertFalse(FundTransaction.objects.exists())
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.current_capital, Decimal("1000"))
        self.funds.assert_not_called()
        self.assertFalse(RuntimeOutbox.objects.exists())

    def test_failed_deployment_rolls_back_existing_account_balance_adjustment(self):
        account = self.account(balance=50)
        response = self.client.post("/api/v1/portfolio/portfolios/create_paper_account/", {
            "allocation_id": self.allocation.pk, "slippage_pct": -1,
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        account.refresh_from_db()
        self.portfolio.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal("50"))
        self.assertEqual(self.portfolio.current_capital, Decimal("1000"))
        self.assertFalse(FundTransaction.objects.exists())

    def test_direct_deployment_publishes_only_after_commit(self):
        account = self.account()
        self.assertFalse(connection.in_atomic_block)
        session = self.deploy(account)
        self.assertTrue(PaperTradingSession.objects.filter(pk=session.pk, status="RUNNING").exists())
        self.funds.assert_not_called()
        self.assertTrue(RuntimeOutbox.objects.filter(topic="control", aggregate_key=f"paper:{session.pk}").exists())
        self.assertTrue(RuntimeOutbox.objects.filter(topic="cache", payload__method="update_session_funds").exists())

    def test_outer_rollback_discards_session_notification_and_runtime_updates(self):
        account = self.account()
        notification_count = Notification.objects.count()
        outbox_count = RuntimeOutbox.objects.count()
        with self.assertRaisesMessage(ValueError, "cancel transaction"):
            with transaction.atomic():
                self.deploy(account)
                self.funds.assert_not_called()
                self.assertGreater(RuntimeOutbox.objects.count(), outbox_count)
                raise ValueError("cancel transaction")
        self.assertFalse(PaperTradingSession.objects.exists())
        self.assertEqual(Notification.objects.count(), notification_count)
        self.funds.assert_not_called()
        self.assertEqual(RuntimeOutbox.objects.count(), outbox_count)

    def test_delete_linked_account_returns_capital_once(self):
        account = self.account()
        response = self.client.delete(f"/api/v1/paper/accounts/{account.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(PaperAccount.objects.filter(pk=account.pk).exists())
        self.assertFalse(CapitalAllocation.objects.filter(pk=self.allocation.pk).exists())
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.current_capital, Decimal("1200"))
        self.assertEqual(FundTransaction.objects.get().amount, Decimal("200"))

    def test_delete_detached_account_supports_null_allocation(self):
        account = self.account(linked=False)
        response = self.client.delete(f"/api/v1/paper/accounts/{account.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(PaperAccount.objects.filter(pk=account.pk).exists())
        self.assertTrue(CapitalAllocation.objects.filter(pk=self.allocation.pk).exists())
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.current_capital, Decimal("1200"))

    def test_delete_rejects_running_session(self):
        account = self.account()
        self.deploy(account)
        response = self.client.delete(f"/api/v1/paper/accounts/{account.pk}/")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertTrue(PaperAccount.objects.filter(pk=account.pk).exists())
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.current_capital, Decimal("1000"))
