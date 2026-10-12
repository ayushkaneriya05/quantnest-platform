"""Bounded in-process latency samples; export occurs on the control thread."""
import math
import threading
from collections import defaultdict, deque


class RuntimeMetrics:
    def __init__(self):
        self._samples = defaultdict(lambda: deque(maxlen=2048))
        self._counts = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, stage, milliseconds):
        with self._lock:
            self._samples[stage].append(max(float(milliseconds), 0))
            self._counts[stage] += 1

    def export(self):
        with self._lock:
            result = {}
            for stage, values in self._samples.items():
                samples = sorted(values)
                def percentile(p):
                    return samples[min(len(samples) - 1, max(0, math.ceil(len(samples) * p) - 1))]
                result[stage] = {"count": self._counts[stage], "sample_count": len(samples),
                                 "p50_ms": percentile(0.50), "p95_ms": percentile(0.95), "p99_ms": percentile(0.99)}
            return result


metrics = RuntimeMetrics()
