"""Isolated execution, matching, recovery and PostgreSQL concurrency regressions."""
import os
import tempfile
import time
import uuid
import threading
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase


def configuration(ids=(1,)):
    return {
        "name": "Audit", "strategy_type": "INTRADAY", "market_type": "INDIAN",
        "exchange": "NSE", "instrument_type": "STOCK",
        "entry_order_config": {"entry_side": "BUY", "entry_group_operator": "OR"},
        "exit_order_config": {}, "time_rule": {"timezone": "Asia/Kolkata", "candle_timeframe": "1m"},
        "special_event_filter": {}, "auto_disable_rules": [],
        "position_sizing_rule": {"sizing_method": "FIXED", "fixed_quantity": 1},
        "watchlist_instruments": [{"instrument_id": i, "execution_routes": [{"route_type": "DIRECT"}]} for i in ids],
        "rule_groups": [{"name": "Entry", "rule_type": "ENTRY", "is_active": True,
            "logical_operator": "AND", "rules": [{"operand_a_type": "CLOSE", "operand_a_params": {},
            "comparison": "GT", "operand_b_type": "CONSTANT", "operand_b_params": {"value": 100}}]}],
    }


class DomainChecks(SimpleTestCase):
    def test_old_fill_projection_cannot_release_a_newer_pending_exit(self):
        from strategy_engine.context import PaperSessionContext
        context = PaperSessionContext.__new__(PaperSessionContext)
        context._runtime_l1_lock = threading.RLock()
        context._runtime_l1 = {1: {"phase": "EXIT_PENDING", "pending_request_id": "exit-2",
                                  "entry_time": "trade-1", "quantity": 1, "_version": 2}}
        context.apply_external_runtime_state(1, {"phase": "OPEN", "entry_time": "trade-1", "quantity": 1,
                                                "pending_request_id": None, "settled_request_id": "entry-1", "_version": 3})
        self.assertEqual(context.get_runtime_state(1)["phase"], "EXIT_PENDING")
        context.apply_external_runtime_state(1, {"phase": "CLOSED", "entry_time": "trade-1", "quantity": 0,
                                                "pending_request_id": None, "settled_request_id": "exit-2", "_version": 4})
        self.assertEqual(context.get_runtime_state(1)["phase"], "CLOSED")
        self.assertIsNone(context.get_runtime_state(1)["pending_request_id"])

    def test_new_trade_projection_waits_for_its_own_request_settlement(self):
        from strategy_engine.context import PaperSessionContext
        context = PaperSessionContext.__new__(PaperSessionContext)
        context._runtime_l1_lock = threading.RLock()
        context._runtime_l1 = {1: {"phase": "ENTRY_PENDING", "pending_request_id": "entry-2", "_version": 2}}
        context.apply_external_runtime_state(1, {"phase": "OPEN", "entry_time": "trade-2", "quantity": 1,
                                                "pending_request_id": None, "_version": 3})
        self.assertEqual(context.get_runtime_state(1)["phase"], "ENTRY_PENDING")
        context.apply_external_runtime_state(1, {"phase": "OPEN", "entry_time": "trade-2", "quantity": 1,
                                                "pending_request_id": None, "settled_request_id": "entry-2", "_version": 4})
        self.assertEqual(context.get_runtime_state(1)["phase"], "OPEN")

    def test_recovered_runtime_gate_rechecks_current_candle(self):
        from quantnest_runtime.execution import _apply_controls
        actor = SimpleNamespace(status="RUNNING", market_ready=True, runtime_ready=False,
                                last_candle=(1, 2), gap=False, events={}, program=SimpleNamespace())
        row = {"status": "RUNNING", "market_ready": True, "runtime_ready": True, "events": {}}
        _apply_controls(actor, row)
        self.assertEqual(actor.last_candle, ())
        actor.last_candle = (1, 2)
        _apply_controls(actor, row)
        self.assertEqual(actor.last_candle, (1, 2))

    def test_contract_tick_and_multiplier_accept_normalized_numeric_values(self):
        from trading_domain.contracts import Contract
        contract = Contract(1, "NSE", "STOCK", "INR", 0.05, multiplier=1.0)
        self.assertEqual(contract.price("100.04"), Decimal("100.00"))
        self.assertEqual(contract.notional(100, 2), Decimal("200"))

    def test_unimplemented_broker_adapters_cannot_act_as_live_connections(self):
        from brokers.services import BrokerService, FyersAdapter
        for name in ("UNKNOWN", "ZERODHA", "ANGEL"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                BrokerService.get_adapter(SimpleNamespace(broker_name=name))
        self.assertIsInstance(BrokerService.get_adapter(SimpleNamespace(broker_name="FYERS")), FyersAdapter)

    def test_cooldown_is_scoped_to_the_actor_instrument(self):
        from trading_domain.strategy import StrategyProgram
        config = configuration()
        config["entry_order_config"]["cooldown_seconds"] = 60
        frame = pd.DataFrame({"open": [101], "high": [102], "low": [100], "close": [101], "volume": [1]},
            index=pd.date_range("2026-10-05T09:16:00", periods=1, tz="Asia/Kolkata"))
        now = frame.index[-1]
        program = StrategyProgram(config)
        # Session risk totals may include another instrument's recent trade.
        self.assertTrue(program.evaluate_entry_logic(frame, now, {}, {"last_entry_time": now})[0])
        self.assertFalse(program.evaluate_entry_logic(frame, now, {"last_exit_time": now}, {})[0])
        self.assertFalse(program.can_enter({"entry_time": now.isoformat()}, now)[0])

    def test_cumulative_fill_incremental_price_and_duplicate(self):
        from trading_domain.orders import OrderState, observe_order
        first = observe_order(OrderState(10), status="PARTIAL_FILL", filled=4, average=100)
        second = observe_order(first.state, status="FILLED", filled=10, average=106)
        self.assertEqual((second.fill_quantity, second.fill_price), (6, Decimal("110")))
        self.assertEqual(observe_order(second.state, status="FILLED", filled=10, average=106).fill_quantity, 0)

    def test_out_of_order_fill_does_not_regress(self):
        from trading_domain.orders import OrderState, observe_order
        old = OrderState(10, 6, Decimal("600"), "PARTIAL_FILL")
        self.assertEqual(observe_order(old, status="PLACED", filled=4, average=100).state, old)

    def test_missing_average_does_not_consume_fill_cursor(self):
        from trading_domain.orders import OrderState, observe_order
        old = OrderState(10)
        observed = observe_order(old, status="FILLED", filled=10, average=0)
        self.assertTrue(observed.error)
        self.assertEqual(observed.state, old)

    def test_cost_correction_requires_reconciliation(self):
        from trading_domain.orders import OrderState, observe_order
        self.assertTrue(observe_order(OrderState(10, 4, Decimal("400"), "PARTIAL_FILL"),
            status="PARTIAL_FILL", filled=4, average=101).error)

    def test_incomplete_terminal_fill_is_rejected(self):
        from trading_domain.orders import OrderState, observe_order
        self.assertTrue(observe_order(OrderState(10), status="FILLED", filled=4, average=100).error)

    def test_book_limit_stop_and_modification(self):
        from trading_domain.matching import IndexedOrderBook
        book = IndexedOrderBook()
        def put(i, side, kind, price=100, trigger=None):
            book.upsert({"id": i, "status": "OPEN", "transaction_type": side,
                         "order_type": kind, "price": price, "trigger_price": trigger})
        put(1, "BUY", "LIMIT", 101)
        put(2, "SELL", "LIMIT", 99)
        put(3, "BUY", "STOP", trigger=101)
        put(1, "BUY", "LIMIT", 98)
        self.assertEqual(book.match(100)[0], [2])
        self.assertEqual(book.match(102)[0], [3])
        self.assertEqual(book.match(97)[0], [1])

    def test_stop_limit_activates_then_waits_for_limit(self):
        from trading_domain.matching import IndexedOrderBook
        book = IndexedOrderBook()
        book.upsert({"id": 1, "status": "OPEN", "transaction_type": "BUY",
                     "order_type": "STOP_LIMIT", "price": 101, "trigger_price": 102})
        self.assertEqual(book.match(103), ([], [1]))
        self.assertEqual(book.match(101)[0], [1])

    def test_book_batch_retains_eligible_orders(self):
        from trading_domain.matching import IndexedOrderBook
        book = IndexedOrderBook()
        for i in range(1, 11):
            book.upsert({"id": i, "status": "OPEN", "transaction_type": "BUY", "order_type": "MARKET"})
        matched = []
        while book.has_matches(100):
            matched.extend(book.match(100, limit=3)[0])
        self.assertEqual(matched, list(range(1, 11)))

    def test_shared_rule_program_matches_vectorized_backtest(self):
        from trading_domain.strategy import StrategyProgram
        from backtesting.executor import BacktestStrategyExecutor
        frame = pd.DataFrame({"open": [99, 100], "high": [100, 102], "low": [98, 99],
                              "close": [99, 101], "volume": [1, 2]},
                             index=pd.date_range("2026-10-05T09:15:00", periods=2, freq="min", tz="Asia/Kolkata"))
        realtime = StrategyProgram(configuration()).evaluate_entry_logic(frame, frame.index[-1], {}, {})[0]
        historical = BacktestStrategyExecutor(configuration()).evaluate_entry_signals(frame).get(frame.index[-1], False)
        self.assertEqual(realtime, historical)
        self.assertTrue(realtime)

    def test_hot_context_and_protection_have_no_redis_or_database_reads(self):
        from strategy_engine.context import PaperSessionContext
        from strategy_engine.engine import evaluate_protection
        with patch.object(PaperSessionContext, "_fetch_user_id", return_value=1):
            context = PaperSessionContext("1", "1")
        context._runtime_l1[1] = {"phase": "OPEN", "side": "BUY", "quantity": 10,
                                "avg_price": 100, "protected_stop_price": 95, "peak_price": 100}
        actor = SimpleNamespace(context=context, instrument=1, session="1", strategy="1", scope="paper",
                                version_id=1, lease=SimpleNamespace(key="owner", token="token"), generation=0)
        with patch("strategy_engine.runtime.StrategyRuntimeState.trade_state", side_effect=AssertionError("Network read")), \
             patch("strategy_engine.dispatcher.OrderDispatcher.dispatch_exit") as dispatch:
            evaluate_protection(actor, 94)
            dispatch.assert_called_once()
            self.assertEqual(context.get_runtime_state(1)["current_price"], 94)

    def test_hot_entry_handoff_uses_local_context_and_pinned_config(self):
        from strategy_engine.context import PaperSessionContext
        from strategy_engine.engine import apply_calculation
        from strategy_engine.router import StrategyOrderRouter
        from trading_domain.strategy import StrategyProgram
        from risk_management.metrics import empty_metrics
        now = datetime.now(timezone.utc)
        with patch.object(PaperSessionContext, "_fetch_user_id", return_value=1):
            context = PaperSessionContext("1", "1")
        context._runtime_l1[1] = {}
        context._cached_capital = 10000
        context._cached_risk_stats = empty_metrics(10000, now)
        context._execution_context_updated = time.monotonic()
        context.account_key = "paper:1"
        context.contracts = {1: {"lot_size": 1}}
        calendar = SimpleNamespace(zone=timezone.utc, session_minutes=375,
            is_trading_day=lambda day: True, session_open=lambda day: now - timedelta(hours=1),
            session_close=lambda day: now + timedelta(hours=1))
        actor = SimpleNamespace(context=context, instrument=1, session="1", strategy="1", scope="paper",
            version_id=12, lease=SimpleNamespace(key="owner", token="token"), generation=0,
            status="RUNNING", gap=False, market_ready=True, runtime_ready=True,
            config=configuration(), calendar=calendar, program=StrategyProgram(configuration()),
            watch={1: configuration()["watchlist_instruments"][0]},
            last_entry_candle="", market=Mock(is_tick_fresh=Mock(return_value=True),
                                           get_latest_price=Mock(return_value=101)))
        publisher = Mock()
        with patch.object(StrategyOrderRouter(), "_publisher", publisher, create=True), \
             patch("core.redis.runtime_redis", side_effect=AssertionError("Redis on hot path")), \
             patch("core.cache_view.cache_view.get_session_funds", side_effect=AssertionError("Remote funds")):
            apply_calculation(actor, {"exit": (False, None, "EXIT_ALL", {}), "entry": (True, "BUY", "Signal"),
                                      "timestamp": now.isoformat(), "price": 101})
        publisher.assert_called_once()
        request = publisher.call_args.args[0]
        self.assertEqual((request.qty, request.strategy_version_id, request.owner_token), (1, 12, "token"))

    def test_gateway_rejects_expired_entries_and_lost_owners(self):
        from strategy_engine.order_queue import validate_request, entry_is_allowed
        request = {"intent": "ENTRY", "expires_at": time.time() - 1, "owner_key": "owner", "owner_token": "token"}
        with self.assertRaisesMessage(ValueError, "deadline expired"):
            validate_request(request)
        request["intent"] = "EXIT"
        with patch("strategy_engine.order_queue._redis") as client:
            client.return_value.get.return_value = "token"
            validate_request(request)
            client.return_value.get.return_value = "other-owner"
            with self.assertRaisesMessage(ValueError, "ownership"):
                validate_request(request)
        self.assertFalse(entry_is_allowed("PAUSED", "ENTRY"))
        self.assertTrue(entry_is_allowed("STOPPING", "EXIT"))

    def test_auto_disable_uses_the_configuration_without_model_lookups(self):
        from risk_management.policy import evaluate_configuration
        from risk_management.metrics import empty_metrics
        now = datetime.now(timezone.utc)
        config = configuration()
        config["auto_disable_rules"] = [{"trigger_type": "CONSECUTIVE_LOSSES", "threshold_count": 2,
                                         "is_active": True, "auto_reenable": False}]
        stats = empty_metrics(10000, now)
        stats["consecutive_losses"] = 2
        self.assertTrue(evaluate_configuration(config, stats, 10000, now)["should_disable"])

    def test_local_market_ring_order_gap_and_receipt_age(self):
        from marketdata.shared_memory import SharedMemoryManager
        with tempfile.TemporaryDirectory(prefix="quantnest-audit-") as directory, \
             patch.dict(os.environ, {"QUANTNEST_RUNTIME_DIR": directory, "MARKET_TICK_CAPACITY": "1024"}):
            writer = SharedMemoryManager("AUDIT", "1m", create=True, max_size=4)
            reader = SharedMemoryManager("AUDIT", "1m")
            try:
                for i in range(1027):
                    writer.update_current_candle(100 + i / 1000, 1, received_time=time.time())
                rows, gap = reader.read_ticks(0, limit=2)
                self.assertTrue(gap)
                self.assertEqual(list(rows[:, 0]), [4, 5])
                self.assertTrue(reader.is_tick_fresh())
                writer.update_current_candle(100, 0, received_time=time.time() - 30)
                self.assertFalse(reader.is_tick_fresh())
            finally:
                reader.close()
                writer.close()


class DatabaseChecks(TestCase):
    def setUp(self):
        # Financial tests must never publish into a running execution service.
        client = MagicMock()
        client.get.return_value = None
        client.mget.side_effect = lambda keys: [None for _ in keys]
        client.scan_iter.side_effect = lambda **kwargs: iter(())
        client.eval.return_value = 1
        self.enterContext(patch("core.redis.runtime_redis", return_value=client))
        self.enterContext(patch("core.runtime_projection.runtime_redis", return_value=client))
        from instruments.models import Instrument
        from strategies.models import Strategy, StrategyVersion
        from brokers.models import BrokerCredential
        from live_trading.models import LiveStrategyAllocation, TradingSession
        self.user = get_user_model().objects.create_user(username="architecture-audit")
        self.instrument = Instrument.objects.create(fy_token="audit-a", symbol="AUDIT", name="Audit",
            sym_ticker="NSE:AUDIT-EQ", exchange="NSE", instrument_type="STOCK")
        self.strategy = Strategy.objects.create(user=self.user, name="Audit", status="ACTIVE", paper_trading_enabled=True,
                                                auto_version_enabled=False)
        self.config = configuration([self.instrument.pk])
        self.version, _ = StrategyVersion.objects.get_or_create(strategy=self.strategy, version_number=1,
            defaults={"config_snapshot": self.config})
        self.version.config_snapshot = self.config
        self.version.save(update_fields=["config_snapshot"])
        self.credential = BrokerCredential.objects.create(user=self.user, broker_name="FYERS", client_id="audit")
        self.allocation = LiveStrategyAllocation.objects.create(user=self.user, strategy=self.strategy,
            broker_credential=self.credential, deployed_version=self.version, allocated_capital=10000)
        self.session = TradingSession.objects.create(user=self.user, strategy=self.strategy,
            broker_credential=self.credential, allocation=self.allocation, status="RUNNING")
        self.enterContext(patch("notifications.services.NotificationService.notify"))

    def order(self, broker_id="B1", quantity=10, side="BUY", **kwargs):
        from live_trading.models import LiveOrder
        return LiveOrder.objects.create(user=self.user, strategy=self.strategy, session=self.session,
            allocation=self.allocation, broker_credential=self.credential, instrument=self.instrument,
            strategy_version=self.version, quantity=quantity, side=side, price=100,
            pending_quantity=quantity, status="UNKNOWN", broker_order_id=broker_id, **kwargs)

    def observation(self, identity="B1", filled=10, average=106, **kwargs):
        return {"broker_order_id": identity, "symbol": self.instrument.sym_ticker, "side": "BUY",
                "quantity": 10, "filled_quantity": filled, "avg_fill_price": average,
                "status": "FILLED" if filled == 10 else "PARTIAL_FILL", **kwargs}

    def test_live_cumulative_fills_modify_ledger_once(self):
        from live_trading.order_processor import apply_order_observation
        from live_trading.models import LivePosition
        self.order()
        apply_order_observation(self.credential, self.observation(filled=4, average=100))
        apply_order_observation(self.credential, self.observation())
        apply_order_observation(self.credential, self.observation())
        position = LivePosition.objects.get(allocation=self.allocation)
        self.assertEqual((position.quantity, position.avg_price), (10, Decimal("106")))

    def test_live_partial_and_final_exits_cannot_duplicate_realized_pnl(self):
        from live_trading.order_processor import apply_order_observation
        from live_trading.models import LivePosition, LiveTrade
        self.order()
        apply_order_observation(self.credential, self.observation(average=100))
        for identity, quantity in (("EXIT1", 4), ("EXIT2", 6)):
            self.order(broker_id=identity, quantity=quantity, side="SELL", intent="EXIT")
            update = self.observation(identity=identity, filled=quantity, average=110,
                                      side="SELL", quantity=quantity, status="FILLED")
            apply_order_observation(self.credential, update)
            apply_order_observation(self.credential, update)
        self.assertFalse(LivePosition.objects.filter(allocation=self.allocation).exists())
        self.assertEqual(LiveTrade.objects.filter(allocation=self.allocation).count(), 2)
        self.assertEqual(sum(LiveTrade.objects.values_list("realized_pnl", flat=True)), Decimal("100"))

    def test_verified_tag_retains_original_session(self):
        from live_trading.order_processor import apply_order_observation
        order = self.order(broker_id="")
        applied = apply_order_observation(self.credential, self.observation(order_tag=f"QN{order.pk}"))
        self.assertEqual((applied.pk, applied.session_id, applied.strategy_version_id),
                         (order.pk, self.session.pk, self.version.pk))

    def test_foreign_account_and_unknown_activity_never_create_owned_positions(self):
        from brokers.models import BrokerCredential
        from live_trading.order_processor import apply_order_observation
        from live_trading.models import LivePosition, BrokerAccountObservation
        order = self.order()
        other = BrokerCredential.objects.create(user=self.user, broker_name="FYERS", client_id="other")
        self.assertIsNone(apply_order_observation(other, self.observation(order_tag=f"QN{order.pk}")))
        self.assertFalse(LivePosition.objects.exists())
        self.assertEqual(BrokerAccountObservation.objects.filter(credential=other).count(), 1)

    def test_account_position_difference_does_not_overwrite_owned_quantity(self):
        from live_trading.order_processor import apply_order_observation, observe_account_position
        from live_trading.models import LivePosition
        self.order()
        apply_order_observation(self.credential, self.observation())
        observation = observe_account_position(self.credential, {"symbol": self.instrument.sym_ticker, "quantity": 50, "side": "BUY"})
        self.assertFalse(observation.matched)
        self.assertEqual(observation.expected_quantity, 10)
        self.assertEqual(LivePosition.objects.get().quantity, 10)

    def test_live_unknown_submission_is_not_retried(self):
        from live_trading.services import LiveExecutionService
        request = str(uuid.uuid4())
        funds = {"snapshot_time": datetime.now(timezone.utc).isoformat(), "available_margin": "10000"}
        with patch("core.cache_view.cache_view.get_funds", return_value=funds), \
             patch("brokers.services.BrokerService.place_order", side_effect=TimeoutError("mock transport")) as broker:
            def send():
                return LiveExecutionService._execute_market_order(self.session, self.allocation, self.instrument,
                    "BUY", 1, 100, request_id=request, expected_version_id=self.version.pk)
            first, second = send(), send()
            self.assertEqual(first.pk, second.pk)
            self.assertEqual(first.status, "UNKNOWN")
            broker.assert_called_once()

    def test_paper_entry_partial_exit_full_exit_and_request_deduplication(self):
        from paper_trading.models import Portfolio, CapitalAllocation, PaperAccount, PaperTradingSession, PaperOrder, PaperPosition, PaperTrade
        from paper_trading.services import PaperExecutionService
        portfolio = Portfolio.objects.create(user=self.user, current_capital=10000)
        allocation = CapitalAllocation.objects.create(portfolio=portfolio, strategy=self.strategy,
            deployed_version=self.version, allocated_amount=10000)
        account = PaperAccount.objects.create(user=self.user, allocation=allocation, initial_balance=10000, current_balance=10000)
        session = PaperTradingSession.objects.create(user=self.user, strategy=self.strategy,
            allocation=allocation, account=account, status="RUNNING", include_charges=False)
        request = str(uuid.uuid4())
        def send(side, quantity, price, **kwargs):
            with patch("marketdata.quote_store.QuoteStore.get_latest", return_value={"price": price}):
                return PaperExecutionService._execute_market_order(session, account, self.instrument, side,
                    quantity, strategy=self.strategy, expected_version_id=self.version.pk, **kwargs)
        first = send("BUY", 10, 100, request_id=request)
        self.assertEqual(send("BUY", 10, 100, request_id=request).pk, first.pk)
        send("SELL", 4, 110, intent="EXIT")
        self.assertEqual(PaperPosition.objects.get(account=account).quantity, 6)
        send("SELL", 6, 110, intent="EXIT")
        account.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal("10100"))
        self.assertEqual(account.margin_used, 0)
        self.assertFalse(PaperPosition.objects.filter(account=account).exists())
        self.assertEqual(PaperOrder.objects.filter(account=account).count(), 3)
        self.assertEqual(sum(PaperTrade.objects.values_list("net_pnl", flat=True)), 100)

    def test_outbox_database_failure_can_record_retry(self):
        from common.models import RuntimeOutbox
        from core.outbox import relay_batch
        row = RuntimeOutbox.objects.create(topic="cache", aggregate_key="audit", payload={})
        def fail(event):
            RuntimeOutbox.objects.create(pk=event.pk, topic="cache", aggregate_key="duplicate", payload={})
        with patch("core.outbox.deliver", side_effect=fail):
            self.assertEqual(relay_batch(), 0)
        row.refresh_from_db()
        self.assertEqual((row.attempts, row.error), (1, "IntegrityError"))

    def test_outbox_cleanup_succeeds_when_session_projection_is_already_absent(self):
        from common.models import RuntimeOutbox
        from core.cache_api import cache_api
        from core.outbox import cache_event, relay_batch
        row = cache_event("clear_session", "paper", "absent-session")
        with patch.object(cache_api._cache, "clear_session", return_value=False):
            self.assertEqual(relay_batch(), 1)
        row.refresh_from_db()
        self.assertIsNotNone(row.published_at)
        self.assertEqual(row.attempts, 1)
        self.assertEqual(row.error, "")
        self.assertFalse(RuntimeOutbox.objects.filter(published_at__isnull=True).exists())

    def test_outbox_cleanup_keeps_retryable_failure_on_cache_error(self):
        from core.cache_api import cache_api
        from core.outbox import cache_event, relay_batch
        row = cache_event("clear_session", "paper", "absent-session")
        with patch.object(cache_api._cache, "clear_session", side_effect=ConnectionError("cache unavailable")):
            self.assertEqual(relay_batch(), 0)
        row.refresh_from_db()
        self.assertIsNone(row.published_at)
        self.assertEqual(row.attempts, 1)

    def test_terminal_reservations_prevent_pending_capital_overcommit(self):
        from trading.models import Account, Order
        from trading.services import TradingOrderService
        from rest_framework.exceptions import ValidationError
        account = Account.objects.create(user=self.user, balance=1000)
        first = Order.objects.create(account=account, instrument=self.instrument, transaction_type="BUY",
            order_type="LIMIT", quantity=6, price=100)
        TradingOrderService.reserve_order(first)
        second = Order.objects.create(account=account, instrument=self.instrument, transaction_type="BUY",
            order_type="LIMIT", quantity=6, price=100)
        with self.assertRaises(ValidationError):
            TradingOrderService.reserve_order(second)
        self.assertEqual(TradingOrderService.pending_cash(account), Decimal("600"))

    def test_terminal_short_collateral_and_cover_have_correct_balance(self):
        from trading.models import Account, Order, Position
        from trading.services import TradingOrderService
        account = Account.objects.create(user=self.user, balance=1000)
        short = Order.objects.create(account=account, instrument=self.instrument, transaction_type="SELL",
            order_type="LIMIT", quantity=5, price=100)
        TradingOrderService.reserve_order(short)
        TradingOrderService.execute_order(short, Decimal("100"))
        account.refresh_from_db()
        self.assertEqual((account.balance, account.margin), (Decimal("1500"), Decimal("1000")))
        cover = Order.objects.create(account=account, instrument=self.instrument, transaction_type="BUY",
            order_type="LIMIT", quantity=5, price=90)
        TradingOrderService.reserve_order(cover)
        TradingOrderService.execute_order(cover, Decimal("90"))
        account.refresh_from_db()
        self.assertEqual((account.balance, account.margin, account.realized_pnl), (Decimal("1050"), 0, Decimal("50")))
        self.assertFalse(Position.objects.filter(account=account).exists())

    def test_terminal_protective_oco_cannot_reverse_a_closed_position(self):
        from trading.models import Account, Order, Position, TradeHistory
        from trading.services import TradingOrderService
        account = Account.objects.create(user=self.user, balance=9000)
        position = Position.objects.create(account=account, instrument=self.instrument, quantity=10,
            average_price=100, stop_loss=90, take_profit=110)
        TradingOrderService.sync_position_sl_tp_orders(position)
        stop = Order.objects.get(position_link=position, order_type="STOP")
        target = Order.objects.get(position_link=position, order_type="LIMIT")
        TradingOrderService.execute_order(stop, Decimal("90"))
        target.refresh_from_db()
        self.assertEqual(target.status, "CANCELLED")
        TradingOrderService.execute_order(target, Decimal("110"))
        self.assertFalse(Position.objects.filter(account=account).exists())
        self.assertEqual(TradeHistory.objects.filter(order__account=account).count(), 1)

    def test_outbox_rollback_leaves_no_publication(self):
        from core.outbox import enqueue
        from common.models import RuntimeOutbox
        with self.assertRaises(ValueError):
            with transaction.atomic():
                enqueue("runtime", "audit", {"state": "temporary"})
                raise ValueError("rollback")
        self.assertFalse(RuntimeOutbox.objects.filter(aggregate_key="audit").exists())

    def test_outbox_failed_aggregate_must_not_starve_unrelated_aggregates(self):
        from common.models import RuntimeOutbox
        from core.outbox import relay_batch
        RuntimeOutbox.objects.bulk_create([RuntimeOutbox(topic="cache", aggregate_key="bad", payload={}) for _ in range(100)])
        healthy = RuntimeOutbox.objects.create(topic="cache", aggregate_key="healthy", payload={})
        def deliver(event):
            if event.aggregate_key == "bad":
                raise ValueError("Permanent projection failure")
        with patch("core.outbox.deliver", side_effect=deliver):
            for _ in range(3):
                relay_batch()
        healthy.refresh_from_db()
        self.assertIsNotNone(healthy.published_at, "Unrelated aggregate starves behind 100 permanently blocked rows")

    def test_outbox_preserves_each_aggregates_order(self):
        from common.models import RuntimeOutbox
        from core.outbox import relay_batch
        rows = [RuntimeOutbox.objects.create(topic="cache", aggregate_key="ordered", payload={}) for _ in range(3)]
        seen = []
        with patch("core.outbox.deliver", side_effect=lambda event: seen.append(event.pk)):
            for _ in rows:
                relay_batch()
        self.assertEqual(seen, [row.pk for row in rows])

    def test_stopping_live_session_retains_unknown_order_obligations(self):
        from core.lifecycle import finalize_stop
        self.session.status = "STOPPING"
        self.session.save(update_fields=["status"])
        order = self.order()
        self.assertFalse(finalize_stop("live", self.session))
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "STOPPING")
        order.status = "CANCELLED"
        order.save(update_fields=["status"])
        self.assertTrue(finalize_stop("live", self.session))
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "STOPPED")

    def test_backtest_special_events_must_be_scoped_per_instrument(self):
        from instruments.models import Instrument
        from backtesting.models import BacktestRun
        from backtesting.engine import BacktestEngine
        other = Instrument.objects.create(fy_token="audit-b", symbol="OTHER", name="Other",
            sym_ticker="NSE:OTHER-EQ", exchange="NSE", instrument_type="STOCK")
        config = configuration([self.instrument.pk, other.pk])
        config["special_event_filter"] = {"avoid_earnings": True}
        run = BacktestRun.objects.create(user=self.user, strategy=self.strategy, name="Event audit",
            start_date=date(2026, 10, 5), end_date=date(2026, 10, 5), config_snapshot=config,
            initial_capital=10000, include_charges=False, slippage_pct=0)
        frame = pd.DataFrame({"open": [101, 101], "high": [102, 102], "low": [100, 100],
                              "close": [101, 101], "volume": [1, 1]},
                             index=pd.date_range("2026-10-05T09:15:00", periods=2, freq="min", tz="Asia/Kolkata"))
        engine = BacktestEngine(run_instance=run)
        def events(identity, start, end):
            return {date(2026, 10, 5): {"EARNINGS"}} if identity == self.instrument.pk else {}
        with patch("backtesting.engine.BacktestEngine._broadcast_progress_update"), \
             patch("marketdata.event_context.load_events", side_effect=events):
            engine.run_simulation({item.pk: {"instrument": item, "df": frame, "mtf_data": {"1m": frame}} for item in (self.instrument, other)})
        self.assertEqual(engine.context.diagnostics["entry_fills"], 1,
                         "The first instrument's earnings event incorrectly blocks the unaffected instrument")
        run.refresh_from_db()
        self.assertEqual(run.status, "COMPLETED", run.error_message)

    def test_backtest_reuses_partial_exit_state_when_evaluating_following_rules(self):
        from backtesting.models import BacktestRun
        from backtesting.engine import BacktestEngine
        config = deepcopy(self.config)
        config["position_sizing_rule"]["fixed_quantity"] = 10
        condition = config["rule_groups"][0]["rules"]
        config["rule_groups"] += [
            {"name": "Reduce", "rule_type": "TARGET", "is_active": True, "logical_operator": "AND",
             "action": "PARTIAL_EXIT", "action_params": {"exit_pct": 50}, "rules": condition},
            {"name": "Close", "rule_type": "EXIT", "is_active": True, "logical_operator": "AND",
             "action": "EXIT_ALL", "rules": condition},
        ]
        run = BacktestRun.objects.create(user=self.user, strategy=self.strategy, name="Exit state",
            start_date=date(2026, 10, 5), end_date=date(2026, 10, 5), config_snapshot=config,
            initial_capital=10000, include_charges=False, slippage_pct=0)
        frame = pd.DataFrame({"open": [101] * 4, "high": [102] * 4, "low": [100] * 4,
                              "close": [101] * 4, "volume": [1] * 4},
                             index=pd.date_range("2026-10-05T09:15:00", periods=4, freq="min", tz="Asia/Kolkata"))
        engine = BacktestEngine(run_instance=run)
        with patch("backtesting.engine.BacktestEngine._broadcast_progress_update"), \
             patch("marketdata.event_context.load_events", return_value={}):
            engine.run_simulation({self.instrument.pk: {"instrument": self.instrument, "df": frame,
                                                        "mtf_data": {"1m": frame}}})
        self.assertEqual(len(engine.context.closed_trades), 1)
        self.assertIn("EXIT group 'Close' met", engine.context.closed_trades[0]["exit_reason"])
        run.refresh_from_db()
        self.assertEqual(run.status, "COMPLETED", run.error_message)
        self.assertIn("EXIT group 'Close' met", run.trades.get().exit_reason)

    def test_backtest_signal_frames_share_candle_completion_times(self):
        from backtesting.models import BacktestRun
        from backtesting.engine import BacktestEngine
        config = deepcopy(self.config)
        rule = config["rule_groups"][0]["rules"][0]
        rule.update(comparison="LT", operand_b_type="CLOSE", operand_b_params={}, operand_b_timeframe="5m")
        run = BacktestRun.objects.create(user=self.user, strategy=self.strategy, name="Completion time",
            start_date=date(2026, 10, 5), end_date=date(2026, 10, 5), config_snapshot=config,
            initial_capital=10000, include_charges=False, slippage_pct=0)
        frame = pd.DataFrame({"open": [110] * 6, "high": [120] * 6, "low": [100] * 6,
                              "close": [110] * 6, "volume": [1] * 6},
                             index=pd.date_range("2026-10-05T09:15:00", periods=6, freq="min", tz="Asia/Kolkata"))
        higher = frame.iloc[[0]].copy()
        higher["close"] = 120
        engine = BacktestEngine(run_instance=run)
        with patch("backtesting.engine.BacktestEngine._broadcast_progress_update"), \
             patch("marketdata.access.StrategyMarketDataService.get_backtest_multi_timeframe_data",
                   return_value=("1m", {"1m": frame, "5m": higher}, {"complete": True})):
            data = engine.load_data()[self.instrument.pk]
        self.assertEqual(data["mtf_data"]["1m"].index[4], data["mtf_data"]["5m"].index[0])


class ConcurrentChecks(TransactionTestCase):
    def setUp(self):
        from django.db import connection
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL row locks are required")
        DatabaseChecks.setUp(self)

    def parallel(self, function):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from django.db import connections
        barrier = threading.Barrier(2)
        def invoke(index):
            try:
                barrier.wait(timeout=5)
                return function(index)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(invoke, [0, 1]))

    def test_concurrent_live_admission_reserves_account_capital(self):
        from live_trading.services import LiveExecutionService
        self.allocation.allocated_capital = 1000
        self.allocation.save()
        funds = {"snapshot_time": datetime.now(timezone.utc).isoformat(), "available_margin": "1000"}
        with patch("core.cache_view.cache_view.get_funds", return_value=funds), \
             patch("brokers.services.BrokerService.place_order", side_effect=lambda *args, **kwargs:
                   {"status": "PLACED", "broker_order_id": args[1]["order_tag"]}):
            def send(index):
                return LiveExecutionService._execute_market_order(self.session, self.allocation, self.instrument,
                    "BUY", 6, 100, request_id=str(uuid.uuid4()), expected_version_id=self.version.pk).status
            self.assertEqual(sorted(self.parallel(send)), ["PLACED", "REJECTED"])

    def test_concurrent_websocket_rest_snapshot_applies_fill_once(self):
        from live_trading.order_processor import apply_order_observation
        from live_trading.models import LivePosition
        DatabaseChecks.order(self)
        self.parallel(lambda index: apply_order_observation(self.credential, DatabaseChecks.observation(self)))
        self.assertEqual(LivePosition.objects.get(allocation=self.allocation).quantity, 10)

    def test_concurrent_terminal_attempts_apply_one_fill(self):
        from trading.models import Account, Order, Position, TradeHistory
        from trading.services import TradingOrderService
        account = Account.objects.create(user=self.user, balance=1000)
        order = Order.objects.create(account=account, instrument=self.instrument, transaction_type="BUY",
            order_type="LIMIT", quantity=5, price=100, reserved_cash=500)
        self.parallel(lambda index: TradingOrderService.execute_order(order, Decimal("100")))
        self.assertEqual(Position.objects.get(account=account).quantity, 5)
        self.assertEqual(TradeHistory.objects.filter(order=order).count(), 1)

    def test_concurrent_paper_entries_cannot_overspend(self):
        from paper_trading.models import Portfolio, CapitalAllocation, PaperAccount, PaperTradingSession
        from paper_trading.services import PaperExecutionService
        from instruments.models import Instrument
        other = Instrument.objects.create(fy_token="audit-c", symbol="OTHER", name="Other",
            sym_ticker="NSE:OTHER-EQ", exchange="NSE", instrument_type="STOCK")
        portfolio = Portfolio.objects.create(user=self.user, current_capital=1000)
        allocation = CapitalAllocation.objects.create(portfolio=portfolio, strategy=self.strategy,
            deployed_version=self.version, allocated_amount=1000)
        account = PaperAccount.objects.create(user=self.user, allocation=allocation, initial_balance=1000, current_balance=1000)
        session = PaperTradingSession.objects.create(user=self.user, strategy=self.strategy,
            allocation=allocation, account=account, status="RUNNING", include_charges=False)
        with patch("marketdata.quote_store.QuoteStore.get_latest", return_value={"price": 100}):
            def send(index):
                return PaperExecutionService._execute_market_order(session, account, [self.instrument, other][index],
                    "BUY", 6, strategy=self.strategy, request_id=str(uuid.uuid4()), expected_version_id=self.version.pk).status
            self.assertEqual(sorted(self.parallel(send)), ["FILLED", "REJECTED"])
