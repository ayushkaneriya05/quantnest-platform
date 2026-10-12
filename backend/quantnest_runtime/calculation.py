"""Bounded CPU work: immutable input, cached frames/indicators, no order side effects."""
import os
from collections import OrderedDict
from datetime import datetime, timezone

PROGRAMS = OrderedDict()
INDICATORS = OrderedDict()


def initialize():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
    import django
    django.setup()


def evaluate(task):
    from marketdata.shared_memory import SharedMemoryManager
    from strategy_engine.data_feed import DataPreprocessor
    from trading_domain.strategy import StrategyProgram
    from rules_engine.indicators import IndicatorEngine
    key = task["configuration_key"]
    program = PROGRAMS.get(key)
    if program is None:
        program = StrategyProgram(task["config"], session_minutes=task["calendar"].session_minutes)
        PROGRAMS[key] = program
        while len(PROGRAMS) > 128:
            PROGRAMS.popitem(last=False)
    program.active_event_cache = task["events"]
    shm = SharedMemoryManager(task["symbol"], "1m")
    try:
        frame, timestamp = DataPreprocessor.build_mtf_data(
            shm, program, task["calendar"], datetime.fromtimestamp(task["as_of"], timezone.utc))
        if frame is None:
            return {"empty": True}
        engines = {}
        for tf, data in program.mtf_data.items():
            indicator_key = (task["symbol"], tf, shm.history_revision, len(data),
                             data.index[-1] if not data.empty else None)
            engine = INDICATORS.get(indicator_key)
            if engine is None:
                engine = IndicatorEngine(data)
                INDICATORS[indicator_key] = engine
            engines[tf] = engine
        while len(INDICATORS) > 128:
            INDICATORS.popitem(last=False)
        program.mtf_indicator_engines = engines
        program.indicator_engine = engines[program.base_timeframe]
        position = task["position"]
        exit_result = program.evaluate_exit_logic(position, frame) if position else (False, None, "EXIT_ALL", {})
        decision_time = datetime.fromtimestamp(task["as_of"], timezone.utc)
        entry = program.evaluate_entry_logic(frame, decision_time, task["state"], task["risk"]) if not position else (False, None, None)
        return {"exit": exit_result, "entry": entry, "price": float(frame.iloc[-1]["close"]),
                "timestamp": timestamp.isoformat(), "completed_at": datetime.now(timezone.utc).timestamp()}
    finally:
        # Programs retain configuration only. Cache budgets own analytical frames.
        from django.conf import settings
        program.mtf_data, program.mtf_indicator_engines = {}, {}
        program.indicator_engine = None
        budget = settings.CALCULATION_CACHE_MB * 1024 * 1024
        def size(engine):
            return int(engine.df.memory_usage(index=True, deep=True).sum()) + sum(
                int(series.memory_usage(index=True, deep=True)) for series in engine._indicators_cached.values())
        used = sum(size(engine) for engine in INDICATORS.values())
        while INDICATORS and used > budget:
            _, engine = INDICATORS.popitem(last=False)
            used -= size(engine)
        shm.close()
