from datetime import datetime, timezone
from types import SimpleNamespace

from django.test import SimpleTestCase

from common.enums import Side
from .context import BacktestContext
from .execution_service import BacktestExecutionService


class BacktestExecutionTests(SimpleTestCase):
    def setUp(self):
        self.instrument = SimpleNamespace(id=7, instrument_type="EQUITY")
        self.context = BacktestContext(
            initial_capital=10000, include_charges=False,
        )
        self.entry_time = datetime(2026, 1, 5, 9, 15, tzinfo=timezone.utc)

    def test_partial_exits_aggregate_into_one_trade_per_entry(self):
        position = {
            "instrument": self.instrument,
            "instrument_type": "EQUITY",
            "side": Side.BUY,
            "quantity": 10,
            "initial_quantity": 10,
            "avg_price": 100.0,
            "entry_time": self.entry_time,
            "capital_used": 1000.0,
            "entry_slippage": 0.0,
            "max_profit": 50.0,
            "max_loss": 20.0,
        }
        self.context.update_position(self.instrument.id, position)

        first_closed = BacktestExecutionService._apply_fill_to_position(
            self.context, position, 4, 110, self.entry_time, exit_reason="Partial exit",
        )
        self.assertFalse(first_closed)
        self.assertEqual(self.context.closed_trades, [])

        second_closed = BacktestExecutionService._apply_fill_to_position(
            self.context, position, 6, 90, self.entry_time, exit_reason="Final exit",
        )
        self.assertTrue(second_closed)
        self.assertEqual(len(self.context.closed_trades), 1)
        trade = self.context.closed_trades[0]
        self.assertEqual(trade["quantity"], 10)
        self.assertEqual(trade["exit_price"], 98)
        self.assertEqual(trade["gross_pnl"], -20)
        self.assertEqual(trade["net_pnl"], -20)
        self.assertIn("Partial exit", trade["exit_reason"])
        self.assertIn("Final exit", trade["exit_reason"])

    def test_pending_order_waits_for_instrument_candle_and_fills_at_next_open(self):
        fill_time = self.entry_time.replace(minute=16)
        order = {
            "instrument": self.instrument,
            "side": Side.BUY,
            "quantity": 5,
            "strategy_config": {},
            "exit_reason": "strategy_entry",
            "slippage_pct": 0,
        }
        self.context.add_pending_order(order)
        fill_candle = {"open": 101, "high": 103, "low": 100, "close": 102}

        BacktestExecutionService.execute_pending_orders(self.context, {}, self.entry_time)
        self.assertEqual(len(self.context.get_pending_orders()), 1)
        self.assertIsNone(self.context.get_position(self.instrument.id))

        BacktestExecutionService.execute_pending_orders(self.context, {self.instrument.id: fill_candle}, fill_time)
        self.assertEqual(self.context.get_pending_orders(), [])
        self.assertEqual(self.context.get_position(self.instrument.id)["avg_price"], 101)
        self.assertEqual(self.context.diagnostics["entry_fills"], 1)

    def test_entry_is_rejected_when_next_open_exceeds_available_capital(self):
        fill_time = self.entry_time.replace(minute=16)
        self.context.current_capital = 1000
        self.context.add_pending_order({
            "instrument": self.instrument,
            "side": Side.BUY,
            "quantity": 10,
            "strategy_config": {},
            "exit_reason": "strategy_entry",
            "slippage_pct": 0,
        })
        fill_candle = {"open": 101, "high": 103, "low": 100, "close": 102}

        BacktestExecutionService.execute_pending_orders(self.context, {self.instrument.id: fill_candle}, fill_time)
        self.assertIsNone(self.context.get_position(self.instrument.id))
        self.assertEqual(self.context.get_pending_orders(), [])
        self.assertEqual(self.context.diagnostics["capital_rejections"], 1)
