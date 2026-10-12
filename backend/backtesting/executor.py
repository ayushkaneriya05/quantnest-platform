"""Historical adapter: vectorize entries while sharing rule and exit semantics."""
from rules_engine.evaluator import RuleEvaluator
from trading_domain.strategy import StrategyProgram


class BacktestStrategyExecutor(StrategyProgram):
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)

    def evaluate_entry_signals(self, candles):
        groups = self._active_groups("ENTRY")
        if not groups:
            return {}
        evaluator = RuleEvaluator(candles, mtf_data=self.mtf_data,
                                  indicator_engine=self.indicator_engine,
                                  mtf_indicator_engines=self.mtf_indicator_engines)
        signals = [evaluator.evaluate_group(group) for group in groups]
        combined = signals[0]
        for signal in signals[1:]:
            combined = combined & signal if self.entry_config.get("entry_group_operator", "OR") == "AND" else combined | signal
        return {timestamp: True for timestamp, matched in combined.items() if matched}
