"""Deterministic acceptance checks for the shared execution kernel (no database)."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from common.enums import (CandleTimeframe, ComparisonOperator, ExecutionMode,
    ExecutionSessionStatus, InstrumentType, OperandType, OrderIntent, OrderType, Side)

from .compiler import FeatureGraph, compile_strategy
from .engine import EvaluationUnit
from .features import Feature
from .ledger import accept_intent, acknowledge, apply_fill, available, cancel_order
from .matching import match_order
from .matching import OrderBook
from .owner import AccountOwner
from .snapshots import decode, encode
from .preparation import PreparedMarket
from .replay import Replay
from .types import Account, Candle, Contract, Fill, Intent, Order, Tick

D = Decimal
AT = datetime(2026, 10, 21, 9, 20, tzinfo=timezone.utc)
CONTRACT = Contract(1, 'NSE:EXAMPLE-EQ', 'Example', InstrumentType.STOCK, 'NSE', 10, D('.05'), 1, D(1))
KEY = ExecutionMode.PAPER, 1, 1


class RuntimeLauncherTests(TestCase):
    def test_execution_alias_delegates_without_initializing_twice(self):
        from quantnest_runtime import cli
        with patch('sys.argv', ['quantnest_runtime', 'execution']), \
                patch.object(cli, 'initialize') as initialize, \
                patch('execution.launcher.main') as launch, \
                patch.object(cli, 'singleton') as provider:
            cli.main()
        launch.assert_called_once_with()
        initialize.assert_not_called()
        provider.assert_not_called()

    def test_provider_startup_uses_a_local_thread_event(self):
        from threading import Event
        from quantnest_runtime import cli
        with patch('sys.argv', ['quantnest_runtime', 'market-data']), \
                patch.object(cli, 'initialize') as initialize, \
                patch.object(cli.signal, 'signal'), \
                patch.object(cli, 'singleton') as provider:
            cli.main()
        initialize.assert_called_once_with()
        service, stop = provider.call_args.args
        self.assertEqual(service, 'market-data')
        self.assertIsInstance(stop, Event)


class Calendar:
    zone = timezone.utc
    session_minutes = 375
    trading_weekdays = (0, 1, 2, 3, 4)

    def is_open(self, at):
        return True

    def session_bounds(self, at):
        return at.replace(hour=9, minute=15), at.replace(hour=15, minute=30)


def configuration(kind=OperandType.CLOSE, comparison=ComparisonOperator.GREATER):
    return {'time_rule': {'timezone': 'UTC', 'candle_timeframe': CandleTimeframe.M1},
        'entry_order_config': {'entry_side': Side.BUY}, 'exit_order_config': {},
        'position_sizing_rule': {'sizing_method': 'FIXED', 'fixed_quantity': 2, 'capital_percentage': 10},
        'watchlist_instruments': [{'instrument_id': 1}],
        'rule_groups': [{'rule_type': 'ENTRY', 'rules': [{'operand_a_type': kind,
            'operand_a_params': {}, 'comparison': comparison, 'operand_b_type': OperandType.CONSTANT,
            'operand_b_params': {'value': 100}}]}]}


def account():
    return Account((ExecutionMode.PAPER, 1), D(1000), versions={1: 1},
        statuses={1: ExecutionSessionStatus.RUNNING}, sizing={KEY: {'sizing_method': 'FIXED', 'fixed_quantity': 2}})


def intent(identity='first', *, revision=0, side=Side.BUY, quantity=2, manual=False, exiting=False):
    return Intent(identity, (ExecutionMode.PAPER, 1), KEY, 1, revision, 1, AT, side,
        'test', D(100), quantity=quantity, manual=manual,
        intent=OrderIntent.EXIT if exiting else OrderIntent.ENTRY)


class LedgerTests(TestCase):
    def test_costs_settle_at_close_using_actual_holding_dates(self):
        from common.costs import CHARGE_PROFILE_FIELDS
        profile = dict.fromkeys(CHARGE_PROFILE_FIELDS, '0')
        profile.update(stt_eq_delivery_pct='0.1', stt_eq_intraday_pct='0.025')
        for days, entry_tax in [(0, 0), (1, .2)]:
            with self.subTest(days=days):
                state = account()
                state.profiles[1] = profile
                accept_intent(state, intent(), CONTRACT)
                result = apply_fill(state, Fill('first', 2, D(100), AT))
                acknowledge(state, result.revision)
                self.assertEqual(state.charges_paid, D(0))
                accept_intent(state, intent('exit', revision=1, side=Side.SELL, exiting=True), CONTRACT)
                result = apply_fill(state, Fill('exit', 2, D(110), AT+timedelta(days=days)))
                self.assertEqual(result.trade.charges['entry_charges']['stt'], entry_tax)
                self.assertEqual(state.charges_paid, D(str(result.trade.charges['total_charges'])))

    def test_cancelled_reservation_waits_for_writer_acknowledgement(self):
        state = account()
        accept_intent(state, intent(), CONTRACT)
        result = cancel_order(state, 'first')
        self.assertEqual(available(state, 1), D(800))
        acknowledge(state, result.revision)
        self.assertEqual(available(state, 1), D(1000))

    def test_broker_cumulative_reports_are_idempotent(self):
        state = account()
        state.key = (ExecutionMode.LIVE, 1)
        state.broker_available, state.broker_observed_at = D(1000), AT
        unit = (ExecutionMode.LIVE, 1, 1)
        state.sizing[unit] = state.sizing.pop(KEY)
        request = replace(intent(), account=state.key, unit=unit)
        accept_intent(state, request, CONTRACT)
        owner = AccountOwner(state)
        first = owner.broker_observation('first', broker_id='owned', status='PARTIAL_FILL', quantity=1,
            average=D(100), at=AT)
        acknowledge(state, first.revision)
        repeated = owner.broker_observation('first', broker_id='owned', status='PARTIAL_FILL', quantity=1,
            average=D(100), at=AT)
        self.assertIsNone(repeated.fill)
        last = owner.broker_observation('first', broker_id='owned', status='FILLED', quantity=2,
            average=D(101), at=AT)
        self.assertEqual(last.fill.price, D(102))
        self.assertEqual(last.position.average, D(101))
        old = owner.broker_observation('first', broker_id='owned', status='PLACED', quantity=0,
            average=D(0), at=AT)
        self.assertEqual(old.order.status, 'FILLED')
        self.assertIsNone(old.fill)

    def test_funds_reserved_before_fill_and_released_after_ack(self):
        state = account()
        accepted = accept_intent(state, intent(), CONTRACT)
        self.assertEqual(available(state, 1), D(800))
        acknowledge(state, accepted.revision)
        opened = apply_fill(state, Fill('first', 2, D(100), AT))
        acknowledge(state, opened.revision)
        self.assertEqual(state.balance, D(1000))
        self.assertEqual(available(state, 1), D(800))
        accept_intent(state, intent('exit', revision=1, side=Side.SELL, exiting=True), CONTRACT)
        closed = apply_fill(state, Fill('exit', 2, D(110), AT + timedelta(minutes=1)))
        self.assertEqual(state.balance, D(1020))
        self.assertEqual(available(state, 1), D(800))
        acknowledge(state, closed.revision)
        self.assertEqual(available(state, 1), D(1020))
        self.assertEqual(closed.trade.gross, D(20))

    def test_stale_position_or_version_cannot_enter(self):
        state = account()
        with self.assertRaisesRegex(ValueError, 'Position changed'):
            accept_intent(state, intent(revision=1), CONTRACT)
        with self.assertRaisesRegex(ValueError, 'version changed'):
            accept_intent(state, replace(intent(), version=2), CONTRACT)

    def test_manual_reversal_and_full_strategy_exit(self):
        state = account()
        accept_intent(state, intent(), CONTRACT)
        acknowledge(state, apply_fill(state, Fill('first', 2, D(100), AT)).revision)
        accept_intent(state, intent('reverse', revision=1, side=Side.SELL, quantity=5, manual=True), CONTRACT)
        result = apply_fill(state, Fill('reverse', 5, D(110), AT))
        self.assertEqual(result.trade.quantity, 2)
        self.assertEqual(result.position.quantity, -3)
        self.assertEqual(result.position.average, D(110))
        self.assertEqual(result.position.lots[0].quantity, 3)
        acknowledge(state, result.revision)
        result = accept_intent(state, intent('close', revision=2, quantity=1, exiting=True), CONTRACT)
        self.assertEqual(result.order.quantity, 3)

    def test_partial_fills_and_cancel_preserve_exposure(self):
        state = account()
        accept_intent(state, intent(), CONTRACT)
        result = apply_fill(state, Fill('first', 1, D(100), AT))
        self.assertEqual(result.order.remaining, 1)
        result = cancel_order(state, 'first')
        self.assertEqual(result.position.quantity, 1)
        self.assertEqual(result.order.reserved, D(0))

    def test_multiple_manual_closes_do_not_reuse_collateral(self):
        state = account()
        accept_intent(state, intent(), CONTRACT)
        acknowledge(state, apply_fill(state, Fill('first', 2, D(100), AT)).revision)
        accept_intent(state, intent('close1', revision=1, side=Side.SELL, manual=True, exiting=True), CONTRACT)
        with self.assertRaisesRegex(ValueError, 'already reserve'):
            accept_intent(state, intent('close2', revision=1, side=Side.SELL, manual=True, exiting=True), CONTRACT)

    def test_checkpoint_round_trip_keeps_decimal_and_keys(self):
        state = account()
        accept_intent(state, intent(), CONTRACT)
        apply_fill(state, Fill('first', 2, D('100.05'), AT))
        restored = decode(encode(state))
        self.assertEqual(restored, state)
        self.assertIsInstance(restored.positions[KEY].average, Decimal)


class MatchingTests(TestCase):
    def test_indexed_book_defers_signal_tick_without_spinning(self):
        book = OrderBook()
        order = self.order(OrderType.MARKET, sequence=2)
        book.put(order)
        fills, _, more = book.match(self.tick(100, 2))
        self.assertEqual(fills, [])
        self.assertFalse(more)
        fills, _, more = book.match(self.tick(100, 4))
        self.assertEqual(len(fills), 1)
        self.assertFalse(more)

    def test_indexed_sell_stop_limit_waits_after_gap(self):
        book = OrderBook()
        order = self.order(OrderType.STOP_LIMIT, Side.SELL, trigger=D(95), price=D(94))
        book.put(order)
        self.assertFalse(book.match(self.tick(96, 2))[0])
        fills, activated, more = book.match(self.tick(90, 4))
        self.assertEqual(len(activated), 1)
        self.assertFalse(fills or more)
        self.assertEqual(book.match(self.tick(94, 6))[0][0].price, D(94))

    def order(self, kind, side=Side.BUY, **kwargs):
        return Order('one', KEY, CONTRACT, side, 2, AT, 'test', order_type=kind, **kwargs)

    def tick(self, price, sequence=2):
        return Tick(CONTRACT.symbol, sequence, AT, AT.timestamp(), price)

    def test_limit_both_sides(self):
        self.assertIsNotNone(match_order(self.order(OrderType.LIMIT, price=D(100)), self.tick(99)))
        self.assertIsNone(match_order(self.order(OrderType.LIMIT, price=D(100)), self.tick(101)))
        self.assertIsNotNone(match_order(self.order(OrderType.LIMIT, Side.SELL, price=D(100)), self.tick(101)))

    def test_all_order_types_on_both_sides_and_exact_boundaries(self):
        for side in (Side.BUY, Side.SELL):
            for kind in OrderType.values:
                with self.subTest(side=side, kind=kind):
                    order = self.order(kind, side, price=D(100), trigger=D(100))
                    if kind in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT):
                        self.assertIsNone(match_order(order, self.tick(99 if side == Side.BUY else 101)))
                    elif kind == OrderType.LIMIT:
                        self.assertIsNone(match_order(order, self.tick(101 if side == Side.BUY else 99)))
                    fill = match_order(order, self.tick(100, 4))
                    self.assertEqual(fill.price, D(100))
                    self.assertEqual(fill.quantity, 2)

    def test_final_and_unknown_orders_never_simulate_fills(self):
        from common.enums import OrderStatus
        for status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED, 'UNKNOWN'):
            with self.subTest(status=status):
                self.assertIsNone(match_order(self.order(OrderType.MARKET, status=status), self.tick(100)))

    def test_stop_limit_retains_trigger_and_waits_for_limit(self):
        order = self.order(OrderType.STOP_LIMIT, trigger=D(105), price=D(106))
        self.assertIsNone(match_order(order, self.tick(104)))
        self.assertIsNone(order.activated_at)
        self.assertIsNone(match_order(order, self.tick(108)))
        self.assertEqual(order.activated_at, AT)
        self.assertEqual(order.order_type, OrderType.STOP_LIMIT)
        self.assertEqual(match_order(order, self.tick(106)).price, D(106))

    def test_order_never_uses_the_signal_observation(self):
        order = self.order(OrderType.MARKET, sequence=2)
        self.assertIsNone(match_order(order, self.tick(100, 2)))
        self.assertIsNotNone(match_order(order, self.tick(100, 3)))

    def test_adverse_slippage_respects_limit(self):
        order = self.order(OrderType.LIMIT, price=D(100), slippage_pct=D(1))
        self.assertEqual(match_order(order, self.tick(99.9)).price, D(100))


class EvaluationTests(TestCase):
    def test_first_connection_generation_also_resets_cross(self):
        program, graph = self.prepared(configuration(OperandType.LTP, ComparisonOperator.CROSSES_ABOVE))
        unit = EvaluationUnit(KEY, (ExecutionMode.PAPER, 1), program)
        unit.evaluate(graph, Tick(CONTRACT.symbol, 2, AT, AT.timestamp(), 99, generation=0))
        self.assertIsNone(unit.evaluate(graph, Tick(CONTRACT.symbol, 4, AT, AT.timestamp(), 101, generation=1)))

    def test_reward_risk_rejects_missing_initial_stop(self):
        config = configuration()
        config['rule_groups'][0]['rule_type'] = 'TARGET'
        config['rule_groups'][0]['rules'][0]['operand_a_type'] = OperandType.POSITION_RR_RATIO
        with self.assertRaisesRegex(ValueError, 'stop-loss'):
            compile_strategy(config, 1, calendar=Calendar())

    def test_restored_cross_state_and_reconnect(self):
        program, graph = self.prepared(configuration(OperandType.LTP, ComparisonOperator.CROSSES_ABOVE))
        unit = EvaluationUnit(KEY, (ExecutionMode.PAPER, 1), program)
        unit.evaluate(graph, Tick(CONTRACT.symbol, 2, AT, AT.timestamp(), 99, generation=1))
        restored = EvaluationUnit(KEY, unit.account, program)
        restored.restore(decode(encode(unit.checkpoint())))
        self.assertIsNotNone(restored.evaluate(graph, Tick(CONTRACT.symbol, 4, AT, AT.timestamp(), 101, generation=1)))
        # A reconnect has no observed crossing between the two generations.
        restored = EvaluationUnit(KEY, unit.account, program)
        restored.restore(decode(encode(unit.checkpoint())))
        self.assertIsNone(restored.evaluate(graph, Tick(CONTRACT.symbol, 4, AT, AT.timestamp(), 101, generation=2)))

    def test_clock_event_does_not_repeat_ltp_cross(self):
        program, graph = self.prepared(configuration(OperandType.LTP, ComparisonOperator.CROSSES_ABOVE))
        unit = EvaluationUnit(KEY, (ExecutionMode.PAPER, 1), program)
        unit.evaluate(graph, Tick(CONTRACT.symbol, 2, AT, AT.timestamp(), 99))
        unit.evaluate(graph, Tick(CONTRACT.symbol, 4, AT, AT.timestamp(), 101))
        unit.pending = ''
        self.assertIsNone(unit.evaluate(graph, Tick(CONTRACT.symbol, 5, AT, AT.timestamp(), 101,
            closed_at=AT+timedelta(seconds=1))))

    def test_graph_and_streaming_indicator_outputs_match(self):
        import numpy as np
        import pandas as pd
        import talib
        from common.enums import INDICATOR_OPERANDS, get_operand_parameter_config, get_operand_parameter_defaults
        rng = np.random.default_rng(7)
        close = 100 + np.cumsum(rng.normal(0, .5, 350))
        frame = pd.DataFrame({'open': close+.1, 'high': close+.7, 'low': close-.6,
            'close': close, 'volume': rng.integers(100, 500, len(close))},
            index=pd.date_range(AT, periods=len(close), freq='min'))
        def graph_values(kind, params):
            config = configuration(kind)
            config['rule_groups'][0]['rules'][0]['operand_a_params'] = params
            program = compile_strategy(config, 1, calendar=Calendar())
            graph = FeatureGraph(Calendar(), capacity=len(frame))
            graph.register(program)
            feature = program.groups[0].rules[0].left.feature
            result = []
            for at, row in frame.iterrows():
                graph.append(CandleTimeframe.M1, Candle(at-timedelta(minutes=1), at,
                    row.open, row.high, row.low, row.close, row.volume))
                result.append(graph.features[feature].at(at))
            return result
        for kind in INDICATOR_OPERANDS:
            variants = [get_operand_parameter_defaults(kind)]
            for spec in get_operand_parameter_config(kind):
                if spec['key'] in ('output_line', 'anchor', 'pattern') and spec.get('options'):
                    variants = [{**p, spec['key']: choice['value']} for p in variants for choice in spec['options']]
            for params in variants:
                with self.subTest(kind=kind, params=params):
                    node = Feature(kind, params, calendar=Calendar(), capacity=500)
                    actual = [node.update(Candle(at-timedelta(minutes=1), at, row.open, row.high, row.low,
                        row.close, row.volume)) for at, row in frame.iterrows()]
                    np.testing.assert_allclose(actual, graph_values(kind, params), equal_nan=True)
        for line, function in [('PLUS_DI', talib.PLUS_DI), ('MINUS_DI', talib.MINUS_DI)]:
            result = graph_values(OperandType.DMI, {'period': 14, 'output_line': line})
            reference = function(frame.high.to_numpy(), frame.low.to_numpy(), frame.close.to_numpy(), 14)
            np.testing.assert_allclose(result[250:], reference[250:], atol=1e-5)
    def prepared(self, config):
        program = compile_strategy(config, 1, calendar=Calendar())
        graph = FeatureGraph(Calendar(), capacity=200)
        graph.register(program)
        count = max(program.counts.values())
        for i in range(count):
            at = AT - timedelta(minutes=count-i)
            graph.append(CandleTimeframe.M1, Candle(at-timedelta(minutes=1), at, 99, 99, 99, 99, 1))
        return program, graph

    def test_ltp_reads_tick_and_close_reads_completed_bar(self):
        for kind, expected in ((OperandType.LTP, True), (OperandType.CLOSE, False)):
            program, graph = self.prepared(configuration(kind))
            unit = EvaluationUnit(KEY, (ExecutionMode.PAPER, 1), program)
            found = unit.evaluate(graph, Tick(CONTRACT.symbol, 1, AT, AT.timestamp(), 101))
            self.assertEqual(found is not None, expected)

    def test_independent_units_receive_same_tick(self):
        program, graph = self.prepared(configuration(OperandType.LTP))
        units = [EvaluationUnit((ExecutionMode.PAPER, n, 1), (ExecutionMode.PAPER, n), program) for n in (1, 2)]
        tick = Tick(CONTRACT.symbol, 1, AT, AT.timestamp(), 101)
        self.assertTrue(all(unit.evaluate(graph, tick) is not None for unit in units))
        self.assertNotEqual(units[0].pending, units[1].pending)

    def test_cross_tracks_every_tick(self):
        program, graph = self.prepared(configuration(OperandType.LTP, ComparisonOperator.CROSSES_ABOVE))
        unit = EvaluationUnit(KEY, (ExecutionMode.PAPER, 1), program)
        self.assertIsNone(unit.evaluate(graph, Tick(CONTRACT.symbol, 1, AT, AT.timestamp(), 99)))
        self.assertIsNotNone(unit.evaluate(graph, Tick(CONTRACT.symbol, 2, AT, AT.timestamp(), 101)))

    def test_ema_is_incremental_and_future_values_are_hidden(self):
        feature = Feature(OperandType.EMA, {'period': 3}, calendar=Calendar(), capacity=10)
        for n in range(1, 6):
            at = AT + timedelta(minutes=n)
            feature.update(Candle(at-timedelta(minutes=1), at, n, n, n, n, 1))
        self.assertEqual(feature.value, 4)
        self.assertEqual(feature.at(AT+timedelta(minutes=3)), 2)

    def test_replay_fills_candle_signal_on_next_open(self):
        bars = []
        for i in range(-30, 3):
            at = AT + timedelta(minutes=i)
            price = 99 if i < 0 else 101+i
            bars.append(Candle(at, at+timedelta(minutes=1), price, price+.5, price-.5, price, 100))
        replay = Replay(identity=1, version=1, config=configuration(),
            markets=[PreparedMarket(CONTRACT, Calendar(), {CandleTimeframe.M1: bars})],
            start=AT, end=AT+timedelta(minutes=3), capital=D(1000), profile={}, slippage=D(0))
        list(replay.run())
        self.assertEqual(len(replay.trades), 1)
        self.assertEqual(replay.trades[0].entry_time, AT+timedelta(minutes=1))
        self.assertEqual(replay.trades[0].entry_price, D(102))
        self.assertEqual(replay.trades[0].exit_price, D(103))
        self.assertEqual(replay.account.balance, D(1002))
