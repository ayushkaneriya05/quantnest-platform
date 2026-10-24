"""API -> durable command -> owner -> ledger -> existing read models.

Provider prices and session clocks are controlled here; no broker request or
market-data service is started. Django isolates all records in its test database.
"""
from datetime import timedelta
from decimal import Decimal
from queue import Queue
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from common.enums import ExecutionMode, ExecutionCommandType, InstrumentType, OrderType, Side, TerminalOrderStatus
from instruments.models import Instrument
from trading.models import Account, Position, TradeHistory
from trading.serializers import AccountSerializer, OrderSerializer, PositionSerializer
from users.models import User

from .controller import Controller
from .models import Command
from .repository import persist_transition, restore_account
from .tests import Calendar
from .types import Tick
from .worker import Worker

D = Decimal


class TestCalendar(Calendar):
    def load_holidays(self, *args, **kwargs):
        pass


class TerminalBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='execution-check', email='execution-check@example.invalid')
        self.account = Account.objects.create(user=self.user, balance=1000, starting_balance=1000)
        self.instrument = Instrument.objects.create(fy_token='execution-check', symbol='EXAMPLE',
            name='Example stock', sym_ticker='NSE:EXAMPLE-EQ', exchange='NSE', instrument_type=InstrumentType.STOCK)
        self.key = ExecutionMode.TERMINAL, self.account.pk
        self.inbox, self.output = Queue(), Queue()
        self.worker = Worker(0, [self.inbox], self.output)
        self.controller = Controller([self.inbox], self.output)
        self.patches = [
            patch('execution.worker.Worker.subscribe', return_value=True),
            patch('marketdata.calendar.MarketSessionCalendar.for_instrument', return_value=TestCalendar()),
            patch('trading.services.TradingOrderService.require_session', return_value=TestCalendar()),
            patch('execution.controller.latest_observation', side_effect=lambda symbol: {
                'sequence': 2, 'generation': 1, 'observed_at': timezone.now(), 'reference_price': D(100)}),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for item in reversed(self.patches):
            item.stop()
        self.worker.close()
        self.controller.pool.shutdown(wait=True)
        self.controller.brokers.shutdown(wait=True)

    def drain(self):
        """Run the actual message handlers without starting external services."""
        for _ in range(20):
            self.controller.poll_commands()
            while not self.inbox.empty() or self.worker.local:
                self.worker.handle(self.worker.local.popleft() if self.worker.local else self.inbox.get_nowait())
            while not self.output.empty():
                self.controller.receive(self.output.get_nowait())
            if self.inbox.empty() and not self.worker.local and not Command.objects.filter(applied_at__isnull=True).exists():
                return
        self.fail('Commands did not drain.')

    def create_order(self, side=Side.BUY, quantity=2, **values):
        serializer = OrderSerializer(data={'sym_ticker': self.instrument.sym_ticker, 'transaction_type': side,
            'quantity': quantity, 'order_type': OrderType.MARKET, **values},
            context={'request': SimpleNamespace(user=self.user)})
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def observe(self, price, sequence):
        owner = self.worker.owners[self.key]
        at = timezone.now() + timedelta(milliseconds=1)
        results, more = owner.observe(Tick(self.instrument.sym_ticker, sequence, at, at.timestamp(), price, generation=1))
        self.assertFalse(more)
        for result in results:
            self.worker.publish(owner, result)
        self.drain()
        return results

    def test_manual_round_trip_commits_and_restores(self):
        order = self.create_order()
        self.assertFalse(Position.objects.filter(account=self.account).exists())
        self.drain()
        order.refresh_from_db()
        self.assertEqual(order.reserved_cash, D(200))
        self.observe(100, 4)
        order.refresh_from_db()
        self.assertEqual(order.status, TerminalOrderStatus.COMPLETE)
        self.assertEqual(Position.objects.get(account=self.account).quantity, 2)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, D(800))
        self.create_order(Side.SELL, reduce_only=True)
        self.drain()
        results = self.observe(110, 6)
        self.assertFalse(Position.objects.filter(account=self.account).exists())
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, D(1020))
        self.assertEqual(TradeHistory.objects.filter(order__account=self.account).count(), 2)
        # Lost writer acknowledgements do not repeat fills or cash effects.
        self.assertIsNone(persist_transition(results[-1]))
        self.assertEqual(restore_account(self.key).balance, D(1020))
        self.assertFalse(Command.objects.exclude(error='').exists())

    def test_invalid_account_settings_do_not_change_saved_configuration(self):
        self.drain()
        serializer = AccountSerializer(self.account, data={'futures_margin_pct': 30}, partial=True,
            context={'request': SimpleNamespace(user=self.user)})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.account.refresh_from_db()
        self.assertEqual(self.account.futures_margin_pct, D(20))
        self.drain()
        self.account.refresh_from_db()
        self.assertEqual(self.account.futures_margin_pct, D(30))

    def test_amend_cancel_and_protection_are_owner_commands(self):
        order = self.create_order(order_type=OrderType.LIMIT, price='95')
        self.drain()
        serializer = OrderSerializer(order, data={'price': '99'}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.drain()
        order.refresh_from_db()
        self.assertEqual(order.price, D(99))
        self.observe(98, 4)
        position = Position.objects.get(account=self.account)
        serializer = PositionSerializer(position, data={'stop_loss': '90'}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.drain()
        position.refresh_from_db()
        self.assertEqual(position.stop_loss, D(90))
        # Protection signals on this tick and fills on a later observation.
        self.observe(89, 6)
        self.assertTrue(Position.objects.filter(account=self.account).exists())
        self.observe(88, 8)
        self.assertFalse(Position.objects.filter(account=self.account).exists())

    def test_invalid_admission_rejects_read_model_without_reserving_money(self):
        order = self.create_order(quantity=20)
        self.drain()
        order.refresh_from_db()
        self.assertEqual(order.status, TerminalOrderStatus.REJECTED)
        self.assertIn('capital', order.rejection_reason)
        self.assertEqual(restore_account(self.key).balance, D(1000))

    def test_protection_cancels_working_manual_order_before_it_can_fill(self):
        self.create_order(stop_loss='90')
        self.drain()
        self.observe(100, 4)
        waiting = self.create_order(order_type=OrderType.LIMIT, price='85')
        self.drain()
        self.observe(80, 6)
        waiting.refresh_from_db()
        self.assertEqual(waiting.status, TerminalOrderStatus.CANCELLED)
        self.assertEqual(Position.objects.get(account=self.account).quantity, 2)
        self.observe(79, 8)
        self.assertFalse(Position.objects.filter(account=self.account).exists())


class StrategyPersistenceTests(TestCase):
    """Both execution modes write existing portfolio models through one ledger."""
    def setUp(self):
        from strategies.models import Strategy, StrategyVersion
        from .tests import configuration
        self.user = User.objects.create(username='strategy-boundary', email='strategy-boundary@example.invalid')
        self.instrument = Instrument.objects.create(fy_token='strategy-boundary', symbol='EXAMPLE',
            name='Example', sym_ticker='NSE:EXAMPLE-EQ', exchange='NSE', instrument_type=InstrumentType.STOCK)
        self.strategy = Strategy.objects.create(user=self.user, name='Boundary check')
        self.version = StrategyVersion.objects.create(strategy=self.strategy, version_number=1, config_snapshot=configuration())

    def make_state(self, mode):
        from common.enums import ExecutionSessionStatus
        from .types import Account as FinancialAccount
        from .repository import initialize_account
        from .preparation import contract_from_instrument
        if mode == ExecutionMode.PAPER:
            from paper_trading.models import Portfolio, CapitalAllocation, PaperAccount, PaperTradingSession
            portfolio = Portfolio.objects.create(user=self.user)
            allocation = CapitalAllocation.objects.create(portfolio=portfolio, strategy=self.strategy,
                deployed_version=self.version, allocated_amount=1000)
            record = PaperAccount.objects.create(user=self.user, allocation=allocation, current_balance=1000)
            session = PaperTradingSession.objects.create(user=self.user, strategy=self.strategy,
                allocation=allocation, account=record, status=ExecutionSessionStatus.RUNNING)
        else:
            from brokers.models import BrokerCredential
            from live_trading.models import LiveStrategyAllocation, TradingSession
            record = BrokerCredential.objects.create(user=self.user, broker_name='FYERS', client_id='test-boundary')
            allocation = LiveStrategyAllocation.objects.create(user=self.user, strategy=self.strategy,
                deployed_version=self.version, broker_credential=record, allocated_capital=1000)
            session = TradingSession.objects.create(user=self.user, strategy=self.strategy,
                allocation=allocation, broker_credential=record, status=ExecutionSessionStatus.RUNNING)
        state = FinancialAccount((mode, record.pk), D(1000), versions={session.pk: self.version.pk},
            statuses={session.pk: ExecutionSessionStatus.RUNNING}, broker_available=D(1000), broker_observed_at=timezone.now())
        initialize_account(state)
        return state, (mode, session.pk, self.instrument.pk), contract_from_instrument(self.instrument)

    def request(self, state, unit, *, closing=False):
        from uuid import uuid4
        from common.enums import OrderIntent
        from .ledger import position_view
        from .types import Intent
        return Intent(str(uuid4()), state.key, unit, self.version.pk, position_view(state, unit).revision,
            2, timezone.now(), Side.SELL if closing else Side.BUY, 'EXIT' if closing else 'ENTRY', D(100),
            quantity=2, intent=OrderIntent.EXIT if closing else OrderIntent.ENTRY)

    def test_paper_round_trip_and_duplicate_writer(self):
        from paper_trading.models import PaperAccount, PaperPosition, PaperTrade
        from .ledger import accept_intent, acknowledge, apply_fill
        from .types import Fill
        state, unit, contract = self.make_state(ExecutionMode.PAPER)
        for closing, price in [(False, D(100)), (True, D(110))]:
            request = self.request(state, unit, closing=closing)
            persist_transition(accept_intent(state, request, contract))
            result = apply_fill(state, Fill(request.identity, 2, price, timezone.now()))
            persist_transition(result)
            acknowledge(state, result.revision)
        self.assertFalse(PaperPosition.objects.exists())
        self.assertEqual(PaperAccount.objects.get(pk=state.key[1]).current_balance, D(1020))
        self.assertEqual(PaperTrade.objects.get().net_pnl, D(20))
        self.assertIsNone(persist_transition(result))
        self.assertEqual(PaperTrade.objects.count(), 1)

    def test_live_partial_reports_persist_order_position_trade_and_slippage(self):
        from common.enums import OrderStatus
        from live_trading.models import ExecutionLog, LiveOrder, LivePosition, LiveTrade, SlippageRecord
        from .ledger import accept_intent, acknowledge
        from .owner import AccountOwner
        state, unit, contract = self.make_state(ExecutionMode.LIVE)
        owner = AccountOwner(state)
        request = self.request(state, unit)
        persist_transition(accept_intent(state, request, contract))
        self.assertEqual(LiveOrder.objects.get().status, 'UNKNOWN')
        for quantity, price, status in [(1, D(100), OrderStatus.PARTIAL_FILL), (2, D(101), OrderStatus.FILLED)]:
            result = owner.broker_observation(request.identity, broker_id='broker-entry', status=status,
                quantity=quantity, average=price, at=timezone.now())
            persist_transition(result)
            acknowledge(state, result.revision)
        self.assertEqual(LivePosition.objects.get().avg_price, D(101))
        self.assertEqual(SlippageRecord.objects.get().slippage_amount, D(2))
        exit_request = self.request(state, unit, closing=True)
        persist_transition(accept_intent(state, exit_request, contract))
        result = owner.broker_observation(exit_request.identity, broker_id='broker-exit', status=OrderStatus.FILLED,
            quantity=2, average=D(110), at=timezone.now())
        persist_transition(result)
        self.assertFalse(LivePosition.objects.exists())
        self.assertEqual(LiveTrade.objects.get().realized_pnl, D(18))
        self.assertEqual(ExecutionLog.objects.count(), 5)

    def test_live_reserved_capital_includes_contract_multiplier(self):
        from live_trading.models import LiveStrategyAllocation
        from .ledger import accept_intent
        state, unit, contract = self.make_state(ExecutionMode.LIVE)
        persist_transition(accept_intent(state, self.request(state, unit), contract))
        self.instrument.qty_multiplier = D(5)
        self.instrument.save(update_fields=['qty_multiplier'])
        allocation = LiveStrategyAllocation.objects.get()
        self.assertEqual(allocation.reserved_capital, D(1000))
        annotated = LiveStrategyAllocation.objects.with_totals().get()
        self.assertEqual(annotated.annotated_reserved_capital, allocation.reserved_capital)

    def test_live_summary_counts_cancelled_partial_fills_in_seven_queries(self):
        from live_trading.models import LiveOrder
        from live_trading.services import LiveExecutionService
        from .ledger import accept_intent
        state, unit, contract = self.make_state(ExecutionMode.LIVE)
        persist_transition(accept_intent(state, self.request(state, unit), contract))
        LiveOrder.objects.update(status='CANCELLED', filled_quantity=1)
        with patch('live_trading.services.cache.get_many', return_value={}), self.assertNumQueries(7):
            summary = LiveExecutionService.session_summary(self.user)
        self.assertEqual(summary['today_fills'], 1)
        self.assertEqual(summary['cancelled_orders'], 1)
        self.assertEqual(summary['open_orders'], 0)

    def test_zero_broker_equity_warns_once_and_stopped_allocation_clears(self):
        from brokers.models import BrokerCredential, BrokerFundsSnapshot
        from live_trading.models import LiveStrategyAllocation, TradingSession
        from live_trading.services import LiveExecutionService
        self.make_state(ExecutionMode.LIVE)
        credential = BrokerCredential.objects.get()
        BrokerFundsSnapshot.objects.create(credential=credential, net_equity=0)
        with patch('live_trading.services.NotificationService.notify') as notify:
            LiveExecutionService._refresh_broker_allocation_health(credential)
            allocation = LiveStrategyAllocation.objects.get()
            self.assertTrue(allocation.is_over_allocated)
            modified = allocation.updated_at
            LiveExecutionService._refresh_broker_allocation_health(credential)
            allocation.refresh_from_db()
            self.assertEqual(allocation.updated_at, modified)
            notify.assert_called_once()
            TradingSession.objects.update(status='STOPPED')
            LiveExecutionService._refresh_broker_allocation_health(credential)
            allocation.refresh_from_db()
            self.assertFalse(allocation.is_over_allocated)
            self.assertEqual(allocation.breach_reason, '')

    def test_empty_paper_analytics_is_one_query(self):
        from paper_trading.views import PaperTradeViewSet
        view = PaperTradeViewSet()
        view.request = SimpleNamespace(user=self.user)
        with self.assertNumQueries(1):
            data = view.analytics(view.request).data
        self.assertEqual(data['total_trades'], 0)
        self.assertEqual(data['win_rate'], 0)
        self.assertEqual(data['avg_winner'], 0)
        self.assertEqual(data['avg_loser'], 0)

    def test_broker_submission_follows_commit_and_never_replays_unknown_orders(self):
        from live_trading.models import LiveOrder
        from .ledger import accept_intent
        from .messages import Persist
        state, unit, contract = self.make_state(ExecutionMode.LIVE)
        request = self.request(state, unit)
        result = accept_intent(state, request, contract)
        controller = Controller([Queue()], Queue())
        try:
            def submitted(function, identity):
                # The broker boundary observes the durable UNKNOWN record.
                self.assertEqual(LiveOrder.objects.get(pk=identity).status, 'UNKNOWN')
                self.assertEqual(restore_account(state.key).revision, result.revision)
            with patch.object(controller.brokers, 'submit', side_effect=submitted) as submit:
                controller.receive(Persist(result))
                controller.receive(Persist(result))
                self.assertEqual(submit.call_count, 1)
            # A new controller sees recovered identities. Even a new status
            # transition for UNKNOWN must reconcile, never resend placement.
            controller.submitted.clear()
            controller.recovered_orders.add(request.identity)
            from .ledger import order_transition
            with patch.object(controller.brokers, 'submit') as submit:
                controller.receive(Persist(order_transition(state, state.orders[request.identity])))
                submit.assert_not_called()
        finally:
            controller.pool.shutdown(wait=True)
            controller.brokers.shutdown(wait=True)

    def test_provider_history_and_tick_reach_paper_fill_and_live_submission(self):
        """Use real ingestion, SHM, preparation, evaluation and persistence boundaries."""
        import os
        import tempfile
        from contextlib import nullcontext
        from datetime import time as clock
        from unittest.mock import Mock
        import numpy as np
        from common.enums import OperandType
        from marketdata.calendar import MarketSessionCalendar
        from marketdata.candles import read_source
        from marketdata.contracts import HistoryRequest, OHLCV
        from marketdata.fyers import FyersLiveFeedClient
        from marketdata.history import ensure_history
        from marketdata.shared_memory import SharedMemoryManager
        from live_trading.models import LiveOrder
        from paper_trading.models import PaperOrder
        from .compiler import compile_strategy
        from .controller import broker_call
        from .engine import EvaluationUnit
        from .ledger import acknowledge
        from .market import _prepare_symbol
        from .owner import AccountOwner
        from .tests import configuration

        cal = MarketSessionCalendar('NSE', 'UTC', clock(0), clock(23, 59, 59), trading_weekdays=range(7))
        config = configuration(OperandType.LTP)
        program = compile_strategy(config, self.version.pk, calendar=cal)
        now = timezone.now()
        end = now.replace(second=0, microsecond=0)
        count = max(program.sources.values()) + 10
        start = end - timedelta(minutes=count)
        history = [dict(time=start+timedelta(minutes=i), open=99, high=99, low=99, close=99, volume=10)
                   for i in range(count)]
        redis = Mock()
        redis.lock.side_effect = lambda *args, **kwargs: nullcontext()
        provider = Mock(history_window_days={'1m': 30}, history=Mock(return_value=history))
        request = HistoryRequest(self.instrument, '1m', start, end, cal)
        with patch('marketdata.providers.provider', return_value=provider), \
                patch('marketdata.history.runtime_redis', return_value=redis), \
                patch('marketdata.history.data_revision', return_value=0):
            self.assertTrue(ensure_history(request).complete)
            frame = read_source(request).frame

        for mode in (ExecutionMode.PAPER, ExecutionMode.LIVE):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix='quantnest-pipeline-') as directory, \
                    patch.dict(os.environ, {'QUANTNEST_RUNTIME_DIR': directory}):
                state, unit_key, contract = self.make_state(mode)
                state.sizing[unit_key] = config['position_sizing_rule']
                writer = SharedMemoryManager(contract.symbol, '1m', max_size=512, create=True)
                try:
                    writer.replace_history(np.column_stack((frame.loc[:, list(OHLCV)].to_numpy(dtype=float),
                                                            frame.index.as_unit('s').asi8)))
                    ready = dict(connected=True, subscribed={contract.symbol},
                        prepared={contract.symbol: {'ready': True, 'depths': program.sources}})
                    with patch('marketdata.live_feed.LiveMarketDataRegistry.get_state', return_value=ready):
                        prepared = _prepare_symbol(contract.symbol, [program])
                    with patch('marketdata.live_feed.threading.Thread.start'):
                        feed = FyersLiveFeedClient()
                    feed.shm_managers[contract.symbol] = writer
                    feed.mark_connected()
                    at = timezone.now()
                    feed._on_message(dict(type='sf', symbol=contract.symbol, ltp=101, chp=1,
                                          last_traded_time=at.timestamp(), vol_traded_today=100))
                    rows, lost, _, generation = writer.read_observations(prepared.cursor, 1)
                    self.assertFalse(lost)
                    sequence, event, received, price, volume = rows[0]
                    tick = Tick(contract.symbol, int(sequence)*2, at, received, price, volume=volume, generation=generation)
                    unit = EvaluationUnit(unit_key, state.key, program)
                    owner = AccountOwner(state)
                    owner.calendars[contract.symbol] = cal
                    owner.programs[unit_key] = program
                    with self.assertNumQueries(0):
                        intent = unit.evaluate(prepared.graph, tick)
                        self.assertIsNotNone(intent)
                        result = owner.accept(intent, contract)
                    persist_transition(result)
                    acknowledge(state, result.revision)
                    if mode == ExecutionMode.LIVE:
                        order = LiveOrder.objects.get(request_id=intent.identity)
                        with patch('execution.controller.close_old_connections'), \
                                patch('brokers.services.BrokerService.place_order',
                                    return_value={'broker_order_id': 'isolated-broker-order', 'status': 'PLACED'}) as place:
                            broker_call(order.pk)
                        payload = place.call_args.args[1]
                        self.assertEqual(payload['instrument'], contract.symbol)
                        self.assertEqual(payload['quantity'], 2)
                        self.assertEqual(payload['order_tag'], f'QN{order.pk}')
                        self.assertTrue(Command.objects.filter(mode=mode, kind=ExecutionCommandType.BROKER).exists())
                    else:
                        # The entry signal cannot also fill its own order.
                        self.assertEqual(owner.observe(tick)[0], [])
                        next_tick = Tick(contract.symbol, int(sequence)*2+2, at+timedelta(milliseconds=1),
                                         received+.001, 102, generation=generation)
                        transitions, _ = owner.observe(next_tick)
                        for transition in transitions:
                            persist_transition(transition)
                        self.assertEqual(PaperOrder.objects.get(request_id=intent.identity).avg_fill_price, D(102))
                finally:
                    writer.close()


class WorkerProcessTests(TestCase):
    def test_shared_memory_tick_reaches_spawned_worker_and_fills_next_observation(self):
        """Exercise the real IPC/SHM path with an isolated directory and account."""
        import multiprocessing
        import os
        import tempfile
        import time
        from datetime import time as clock_time
        from common.enums import CandleTimeframe, OperandType, ExecutionSessionStatus
        from marketdata.calendar import MarketSessionCalendar
        from marketdata.shared_memory import SharedMemoryManager
        from .compiler import FeatureGraph, compile_strategy
        from .launcher import child
        from .market import PreparedSymbol
        from .messages import Committed, Control, InstallAccount, InstallUnit, Persist, SaveControl
        from .tests import account, configuration, CONTRACT, KEY
        from .types import Candle, PositionView

        context = multiprocessing.get_context('spawn')
        inbox, output, stop = context.Queue(), context.Queue(), context.Event()
        process = None
        with tempfile.TemporaryDirectory(prefix='quantnest-worker-check-') as directory, patch.dict(os.environ,
                {'QUANTNEST_RUNTIME_DIR': directory, 'DEBUG': 'False'}):
            writer = SharedMemoryManager(CONTRACT.symbol, CandleTimeframe.M1, max_size=128, create=True)
            try:
                calendar = MarketSessionCalendar('NSE', 'UTC', clock_time(0), clock_time(23, 59, 59),
                    trading_weekdays=range(7))
                program = compile_strategy(configuration(OperandType.LTP), 1, calendar=calendar)
                graph = FeatureGraph(calendar, capacity=256)
                graph.register(program)
                now = timezone.now()
                for offset in range(max(program.counts.values()), 0, -1):
                    end = now.replace(second=0, microsecond=0) - timedelta(minutes=offset)
                    graph.append(CandleTimeframe.M1, Candle(end-timedelta(minutes=1), end, 99, 99, 99, 99, 10))
                state = account()
                process = context.Process(target=child, args=(0, [inbox], output, stop))
                process.start()
                inbox.put(InstallAccount(state, {1: CONTRACT}, {CONTRACT.symbol: calendar}, {KEY: program}))
                inbox.put(InstallUnit(KEY, state.key, program, PositionView(), ExecutionSessionStatus.RUNNING,
                    {'symbol': CONTRACT.symbol}))
                inbox.put(PreparedSymbol(CONTRACT.symbol, graph, {}, 0, 0, {CandleTimeframe.M1: 0}, now))
                inbox.put(Control(1, state.key, ExecutionCommandType.BALANCE, {'delta': D(0), 'session_id': 1}))
                # The control acknowledgement proves the worker opened the buffer
                # before the test publishes ticks; no startup sleeps are needed.
                self.assertIsInstance(output.get(timeout=20), SaveControl)
                inbox.put(Committed(state.key, 1))

                def next_transition():
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        message = output.get(timeout=max(.1, deadline-time.monotonic()))
                        if isinstance(message, Persist):
                            inbox.put(Committed(state.key, message.transition.revision))
                            return message.transition
                    self.fail('Worker did not emit a financial transition.')

                writer.update_current_candle(101, 1)
                accepted = next_transition()
                self.assertIsNone(accepted.fill)
                self.assertEqual(accepted.order.quantity, 2)
                writer.update_current_candle(102, 1)
                filled = next_transition()
                self.assertEqual(filled.fill.price, D(102))
                self.assertEqual(filled.position.quantity, 2)
                self.assertTrue(process.is_alive())
            finally:
                stop.set()
                if process is not None:
                    process.join(timeout=10)
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=3)
                writer.close()
                for queue in (inbox, output):
                    queue.cancel_join_thread()
                    queue.close()


class AllowanceBoundaryTests(TestCase):
    def test_public_enforces_all_three_allowance_kinds(self):
        from commercial.usage import (CommercialRestriction, get_account_policy,
            require_inventory_capacity, require_request_limits, reserve_usage, settle_usage)
        from commercial.models import UsageBucket
        user = User.objects.create(username='public-allowance', email='public-allowance@example.invalid')
        with override_settings(QUANTNEST_DEPLOYMENT_MODE='public'):
            policy = get_account_policy(user)
            with self.assertRaises(CommercialRestriction):
                require_inventory_capacity(user, policy=policy, strategies=policy['limits']['strategies']+1)
            with self.assertRaises(CommercialRestriction):
                require_request_limits(user, policy=policy, research_instruments=policy['limits']['research_instruments']+1)
            reservation = reserve_usage(user, 'research_turns', 'first', {}, resource=SimpleNamespace(pk=1),
                amount=policy['limits']['research_turns'], policy=policy)
            with self.assertRaises(CommercialRestriction):
                reserve_usage(user, 'research_turns', 'second', {}, resource=SimpleNamespace(pk=2), policy=policy)
            settle_usage(reservation, failed=True)
            settle_usage(reservation, failed=True)
            bucket = UsageBucket.objects.get(user=user)
            self.assertEqual((bucket.used, bucket.reserved), (0, 0))

    def test_development_records_and_private_does_not_limit_or_record(self):
        from commercial.usage import get_account_policy, require_inventory_capacity, require_request_limits, reserve_usage
        from commercial.models import UsageReservation
        user = User.objects.create(username='unlimited-allowance', email='unlimited-allowance@example.invalid')
        for mode in ('development', 'private'):
            with self.subTest(mode=mode), override_settings(QUANTNEST_DEPLOYMENT_MODE=mode):
                policy = get_account_policy(user)
                require_inventory_capacity(user, policy=policy, strategies=10000)
                require_request_limits(user, policy=policy, research_instruments=10000)
                result = reserve_usage(user, 'research_turns', mode, {}, resource=SimpleNamespace(pk=1),
                    amount=10000, policy=policy)
                self.assertEqual(result is None, mode == 'private')
        self.assertEqual(UsageReservation.objects.filter(user=user).count(), 1)

    def test_public_catalog_does_not_reference_retired_worker_capacity(self):
        from rest_framework.test import APIRequestFactory
        from commercial.views import get_public_catalog
        with override_settings(QUANTNEST_DEPLOYMENT_MODE='public', BILLING_ENABLED=True):
            response = get_public_catalog(APIRequestFactory().get('/api/v1/public/catalog/'))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data['plans']['pro']['checkout_available'])
