"""Historical screens share execution semantics without live quotes or orders."""
from datetime import timedelta
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace

import pandas as pd

from common.enums import ComparisonOperator, OperandType
from execution.tests import AT, Calendar, configuration
from .evaluation import compile_conditions, evaluate_conditions


class ResearchEvaluationTests(TestCase):
    def frame(self, prices, *, end=AT, frequency='min'):
        return pd.DataFrame({'open': prices, 'high': prices, 'low': prices,
            'close': prices, 'volume': 100},
            index=pd.date_range(end=end, periods=len(prices), freq=frequency))

    def evaluate(self, config, frames, at=AT):
        return evaluate_conditions(compile_conditions(config, Calendar()), frames, as_of=at)[0]

    def test_crosses_use_two_completed_observations_and_ignore_future(self):
        config = configuration(OperandType.CLOSE, ComparisonOperator.CROSSES_ABOVE)
        frame = self.frame([99] * 29 + [101, 50], end=AT + timedelta(minutes=1))
        result = self.evaluate(config, {'1m': frame})
        self.assertEqual((result['a'], result['b'], result['passed']), (101, 100, True))
        result = self.evaluate(config, {'1m': frame}, AT + timedelta(minutes=1))
        self.assertFalse(result['passed'])

    def test_timeframes_close_together_and_unchanged_cross_does_not_repeat(self):
        config = configuration(OperandType.CLOSE, ComparisonOperator.CROSSES_ABOVE)
        config['rule_groups'][0]['rules'][0]['operand_a_timeframe'] = '5m'
        slow = self.frame([99] * 29 + [101], frequency='5min')
        fast = self.frame([200] * 31, end=AT + timedelta(minutes=1))
        self.assertTrue(self.evaluate(config, {'1m': fast, '5m': slow})['passed'])
        result = self.evaluate(config, {'1m': fast, '5m': slow}, AT + timedelta(minutes=1))
        self.assertEqual(result['a'], 101)
        self.assertFalse(result['passed'])

    def test_shift_and_nested_indicators_share_compiler(self):
        config = configuration(OperandType.SMA)
        config['rule_groups'][0]['rules'][0]['operand_a_params'] = {
            'period': 2, 'source': OperandType.SMA, 'source_params': {'period': 2}, 'shift': 1}
        result = self.evaluate(config, {'1m': self.frame(list(range(1, 61)))})
        self.assertEqual(result['a'], 58)

    def test_expression_uses_completed_values_and_invalid_math_is_reported(self):
        config = configuration(OperandType.MATH_EXPRESSION)
        expression = {'expression': 'price * 2', 'variables': {'price': {'type': OperandType.CLOSE}}}
        config['rule_groups'][0]['rules'][0]['operand_a_params'] = {'expression': expression}
        frames = {'1m': self.frame([75] * 30)}
        self.assertEqual(self.evaluate(config, frames)['a'], 150)
        expression['expression'] = 'price / 0'
        with self.assertRaisesRegex(ValueError, 'no valid value'):
            self.evaluate(config, frames)

    def test_tick_operands_are_not_silently_replaced_by_close(self):
        frames = {'1m': self.frame([101] * 30)}
        with self.assertRaisesRegex(ValueError, 'Use CLOSE instead of LTP'):
            self.evaluate(configuration(OperandType.LTP), frames)
        config = configuration(OperandType.MATH_EXPRESSION)
        config['rule_groups'][0]['rules'][0]['operand_a_params'] = {
            'expression': {'expression': 'price + 1', 'variables': {'price': {'type': OperandType.LTP}}}}
        with self.assertRaisesRegex(ValueError, 'Use CLOSE instead of LTP'):
            self.evaluate(config, frames)

    def test_insufficient_warmup_is_reported(self):
        with self.assertRaisesRegex(ValueError, 'Insufficient completed candles'):
            self.evaluate(configuration(), {'1m': self.frame([101, 102])})

    def test_invalid_tick_rule_is_rejected_before_history_fetch(self):
        from .tools import _closed_data
        with patch('research.tools.MarketSessionCalendar.for_instrument', return_value=Calendar()), \
                patch('research.tools.prepare_frames') as history:
            with self.assertRaisesRegex(ValueError, 'Use CLOSE instead of LTP'):
                _closed_data(SimpleNamespace(as_of=AT), SimpleNamespace(), configuration(OperandType.LTP))
        history.assert_not_called()

    def test_screen_results_cache_by_conditions_and_keep_existing_response(self):
        from .tools import market_rows
        config = configuration()
        config['rule_groups'][0]['logical_operator'] = 'AND'
        calendar = Calendar()
        calendar.signature = ('UTC',)
        frames = {'1m': self.frame([101] * 30)}
        quality = {'1m': {'revision': 1, 'updated_at': AT}}
        instrument = SimpleNamespace(pk=1, symbol='EXAMPLE', sym_ticker='NSE:EXAMPLE-EQ')
        cache = {}
        with patch('research.tools.Instrument.objects') as instruments, \
                patch('research.tools.ResearchRun.objects') as runs, \
                patch('research.tools.update_active_run'), \
                patch('research.tools._closed_data', side_effect=lambda run, item, rules: (
                    compile_conditions(rules, calendar), frames, quality)), \
                patch('research.tools.read_quote', return_value={'available': False}), \
                patch('research.tools.cache') as store, \
                patch('research.tools.evaluate_conditions', wraps=evaluate_conditions) as evaluate:
            instruments.filter.return_value.in_bulk.return_value = {1: instrument}
            runs.filter.return_value.exists.return_value = True
            store.get.side_effect = cache.get
            store.set.side_effect = lambda key, value, timeout: cache.__setitem__(key, value)
            run = SimpleNamespace(pk=1, as_of=AT)
            result = market_rows(run, config, instrument_ids=[1], charts=True)
            again = market_rows(run, config, instrument_ids=[1], charts=True)
            config['rule_groups'][0]['rules'][0]['operand_b_params']['value'] = 200
            changed = market_rows(run, config, instrument_ids=[1])
        self.assertEqual(result, again)
        self.assertEqual(result['matched'], 1)
        self.assertEqual(result['rows'][0]['operand_values'][0]['a'], 101)
        self.assertEqual(len(result['rows'][0]['chart']), 30)
        self.assertEqual(changed['matched'], 0)
        self.assertEqual(evaluate.call_count, 2)
