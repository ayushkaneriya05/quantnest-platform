"""Checks for benchmark accounting; trading execution is exercised by the CLI."""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from quantnest_runtime.latency_benchmark import Recorder, distribution, _forbidden


class LatencyAccountingTests(unittest.TestCase):
    def test_empty_statistics_are_unavailable(self):
        self.assertEqual(distribution([])["count"], 0)
        self.assertIsNone(distribution([])["p95_ms"])

    def test_percentiles_use_nearest_rank(self):
        result = distribution(range(1, 101))
        self.assertEqual((result["p50_ms"], result["p95_ms"], result["p99_ms"]), (50, 95, 99))

    def test_warmup_ticks_are_acknowledged_but_not_measured(self):
        recorder = Recorder()
        recorder.ready["A"] = (0, time.perf_counter_ns())
        recorder.expected_ticks[0] = 1
        recorder.pending_ticks["A"].append((1, time.time()))
        recorder.tick(SimpleNamespace(symbol="A"), Mock(), 100)
        self.assertEqual(recorder.tick_counts[0], 1)
        self.assertEqual(dict(recorder.ticks), {})

    def test_measured_tick_preserves_sequence_and_calls_real_check(self):
        recorder, original = Recorder(), Mock()
        recorder.ready["A"] = (1, time.perf_counter_ns())
        recorder.expected_ticks[1] = 1
        recorder.pending_ticks["A"].append((9, time.time()))
        actor = SimpleNamespace(symbol="A")
        recorder.tick(actor, original, 100)
        original.assert_called_once_with(actor, 100)
        self.assertEqual(recorder.ticks[1]["A"][0]["sequence"], 9)
        self.assertGreaterEqual(recorder.ticks[1]["A"][0]["ready_ms"], 0)

    def calculation_result(self, wave=1):
        now = time.perf_counter_ns()
        return {"entry": (False, None, None), "exit": (False, None, "EXIT_ALL", {}),
                "_benchmark": {"wave": wave, "ready_ns": now - 4000, "submitted_ns": now - 3000,
                               "started_ns": now - 2000, "finished_ns": now - 1000}}

    def test_calculation_separates_admission_pool_and_compute_time(self):
        recorder = Recorder()
        recorder.expected_calculations[1] = 1
        recorder.calculation(SimpleNamespace(symbol="A"), Mock(), self.calculation_result())
        result = recorder.calculations["A"][0]
        for stage in ("admission_ms", "pool_wait_ms", "compute_ms"):
            self.assertAlmostEqual(result[stage], .001)
        self.assertEqual(recorder.calculation_counts[1], 1)

    def test_inconsistent_process_clocks_are_rejected(self):
        result = self.calculation_result()
        result["_benchmark"]["started_ns"] = result["_benchmark"]["submitted_ns"] - 1
        with self.assertRaisesRegex(AssertionError, "timestamps are inconsistent"):
            Recorder().calculation(SimpleNamespace(symbol="A"), Mock(), result)

    def test_order_producing_fixture_is_rejected_before_application(self):
        result, original = self.calculation_result(), Mock()
        result["exit"] = (True, "Unexpected", "EXIT_ALL", {})
        with self.assertRaisesRegex(AssertionError, "unexpectedly proposed an order"):
            Recorder().calculation(SimpleNamespace(symbol="A"), original, result)
        original.assert_not_called()

    def test_external_io_guard_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "External I/O"):
            _forbidden()


if __name__ == "__main__":
    unittest.main()
