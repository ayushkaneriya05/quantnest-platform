"""Incremental market features shared by independent strategy evaluations.

A node consumes one completed candle at a time. Recursive indicators retain their
accumulators; finite-window indicators retain only the window they need. Every
published value carries its candle completion, so a delayed evaluator cannot read
future values from another session's faster evaluation.
"""
from collections import deque
from datetime import datetime, timedelta
from math import exp, floor, isfinite, nan, sqrt

from common.enums import CandlePatternType, OperandType

from .types import Candle


class Average:
    """SMA-seeded recursive average; missing nested inputs restart its warmup."""
    def __init__(self, period: int, alpha: float):
        self.period, self.alpha = period, alpha
        self.count, self.total, self.value = 0, 0.0, nan

    def update(self, value: float) -> float:
        if not isfinite(value):
            self.count, self.total, self.value = 0, 0.0, nan
            return nan
        if self.count < self.period:
            self.count += 1
            self.total += value
            if self.count == self.period:
                self.value = self.total / self.period
        else:
            self.value += self.alpha * (value - self.value)
        return self.value


class Window:
    def __init__(self, size: int):
        self.values = deque(maxlen=max(size, 1))

    def update(self, value: float) -> float:
        self.values.append(value)
        return self.mean()

    def ready(self) -> bool:
        return len(self.values) == self.values.maxlen and all(isfinite(v) for v in self.values)

    def mean(self) -> float:
        return sum(self.values) / len(self.values) if self.ready() else nan

    def weighted(self) -> float:
        if not self.ready():
            return nan
        n = len(self.values)
        return sum((i + 1) * value for i, value in enumerate(self.values)) / (n * (n + 1) / 2)


def price_source(kind: str, candle: Candle) -> float:
    if kind == OperandType.HL2:
        return (candle.high + candle.low) / 2
    if kind == OperandType.HLC3:
        return (candle.high + candle.low + candle.close) / 3
    if kind == OperandType.OHLC4:
        return (candle.open + candle.high + candle.low + candle.close) / 4
    return getattr(candle, kind.lower())


class Feature:
    """A resolved operand with fixed parameters and bounded published history."""
    def __init__(self, kind: str, parameters: dict, *, calendar, capacity: int, source=None):
        self.kind, self.parameters, self.calendar, self.source = kind, parameters, calendar, source
        p = parameters
        self.period = int(p.get('period', p.get('k_period', 14)))
        self.history = deque(maxlen=capacity)
        self.bars = deque(maxlen=max(self.period + 1, int(p.get('senkou', 52)), int(p.get('kijun', 26)) + 1, 64))
        self.windows, self.averages = {}, {}
        self.previous, self.value = None, nan
        self.group = None
        self.total_price, self.total_volume = 0.0, 0.0
        self.week, self.week_high, self.week_low = None, -float('inf'), float('inf')
        self.previous_week_high, self.previous_week_low = nan, nan
        self.direction, self.lower, self.upper = 1, nan, nan
        self.acceleration, self.extreme = float(p.get('af', 0.02)), nan
        self.delayed = deque(maxlen=int(p.get('kijun', 26)) + 1)
        self.pattern = None
        self.alma_weights = ()
        if kind == OperandType.ALMA:
            n = self.period
            weights = [exp(-((i - floor(0.85 * (n - 1))) ** 2) / (2 * (n / 6) ** 2)) for i in range(n)]
            self.alma_weights = tuple(weight / sum(weights) for weight in weights)
        if kind == OperandType.CANDLE_PATTERN and p['pattern'] != CandlePatternType.DOJI:
            # Resolve the installed native pattern once, before the hot path.
            import talib
            names = {
                CandlePatternType.DOJI: 'CDLDOJI', CandlePatternType.HAMMER: 'CDLHAMMER',
                CandlePatternType.SHOOTING_STAR: 'CDLSHOOTINGSTAR',
                CandlePatternType.ENGULFING_BULLISH: 'CDLENGULFING',
                CandlePatternType.ENGULFING_BEARISH: 'CDLENGULFING',
                CandlePatternType.HARAMI_BULLISH: 'CDLHARAMI', CandlePatternType.HARAMI_BEARISH: 'CDLHARAMI',
                CandlePatternType.MORNING_STAR: 'CDLMORNINGSTAR', CandlePatternType.EVENING_STAR: 'CDLEVENINGSTAR',
                CandlePatternType.MARUBOZU: 'CDLMARUBOZU', CandlePatternType.PIERCING_LINE: 'CDLPIERCING',
            }
            self.pattern = getattr(talib, names[p['pattern']])

    def average(self, name: str, value: float, period: int, *, wilder: bool = False) -> float:
        if name not in self.averages:
            self.averages[name] = Average(period, 1 / period if wilder else 2 / (period + 1))
        return self.averages[name].update(value)

    def window(self, name: str, value: float, size: int) -> Window:
        if name not in self.windows:
            self.windows[name] = Window(size)
        window = self.windows[name]
        window.update(value)
        return window

    def at(self, at: datetime, shift: int = 0) -> float:
        for timestamp, value in reversed(self.history):
            if timestamp <= at:
                if shift == 0:
                    return value
                shift -= 1
        return nan

    def update(self, candle: Candle) -> float:
        if self.history and candle.closed_at <= self.history[-1][0]:
            if candle.closed_at == self.history[-1][0]:
                return self.value
            raise ValueError('Completed feature candles must arrive in increasing order.')
        if self.source is not None:
            source = self.source.update(candle)
        else:
            source = price_source(self.parameters.get('source', OperandType.CLOSE), candle)
        self.bars.append(candle)
        value = self._calculate(candle, source)
        self.previous, self.value = candle, float(value)
        self.history.append((candle.closed_at, self.value))
        return self.value

    def _calculate(self, bar: Candle, source: float) -> float:
        kind, p, n, previous = self.kind, self.parameters, self.period, self.previous
        if kind in (OperandType.OPEN, OperandType.HIGH, OperandType.LOW, OperandType.CLOSE,
                    OperandType.VOLUME, OperandType.HL2, OperandType.HLC3, OperandType.OHLC4):
            return price_source(kind, bar)
        if kind == OperandType.CANDLE_BODY_SIZE:
            body = abs(bar.close - bar.open)
            return (body / (bar.high - bar.low) * 100 if bar.high != bar.low else 0.0) if p['mode'] == 'PERCENTAGE' else body
        if kind in (OperandType.CURRENT_DAY_OPEN, OperandType.PREV_WEEK_HIGH, OperandType.PREV_WEEK_LOW, OperandType.VWAP):
            day = self.calendar.session_bounds(bar.closed_at - timedelta(microseconds=1))[0].date()
            week = day - timedelta(days=day.weekday())
            if week != self.week:
                adjacent = self.week is not None and week - self.week == timedelta(days=7)
                self.previous_week_high = self.week_high if adjacent else nan
                self.previous_week_low = self.week_low if adjacent else nan
                self.week, self.week_high, self.week_low = week, bar.high, bar.low
            else:
                self.week_high, self.week_low = max(self.week_high, bar.high), min(self.week_low, bar.low)
            if kind == OperandType.PREV_WEEK_HIGH:
                return self.previous_week_high
            if kind == OperandType.PREV_WEEK_LOW:
                return self.previous_week_low
            if kind == OperandType.CURRENT_DAY_OPEN:
                if self.group != day:
                    self.group, self.value = day, bar.open
                return self.value
            anchor = p['anchor']
            group = day if anchor == 'D' else week if anchor == 'W' else day.replace(day=1)
            if self.group != group:
                self.group, self.total_price, self.total_volume = group, 0.0, 0.0
            self.total_price += (bar.high + bar.low + bar.close) / 3 * bar.volume
            self.total_volume += bar.volume
            return self.total_price / self.total_volume if self.total_volume else nan
        if kind == OperandType.PIVOT_POINT:
            return (previous.high + previous.low + previous.close) / 3 if previous else nan
        if kind == OperandType.CANDLE_PATTERN:
            if p['pattern'] == CandlePatternType.DOJI:
                average = self.window('doji_range', bar.high - bar.low, 10).mean()
                return float(abs(bar.close - bar.open) < average * 0.1)
            import numpy as np
            columns = [np.fromiter((getattr(b, name) for b in self.bars), dtype=float)
                       for name in ('open', 'high', 'low', 'close')]
            result = int(self.pattern(*columns)[-1])
            name = p['pattern']
            if name in (CandlePatternType.ENGULFING_BULLISH, CandlePatternType.HARAMI_BULLISH):
                return float(result == 100)
            if name in (CandlePatternType.ENGULFING_BEARISH, CandlePatternType.HARAMI_BEARISH):
                return float(result == -100)
            return float(result != 0)

        values = self.window('source', source, n)
        if kind == OperandType.SMA:
            return values.mean()
        if kind == OperandType.EMA:
            return self.average('ema', source, n)
        if kind == OperandType.WMA:
            return values.weighted()
        if kind == OperandType.HMA:
            short = self.window('half', source, max(n // 2, 1)).weighted()
            return self.window('root', 2 * short - values.weighted(), max(int(sqrt(n)), 1)).weighted()
        if kind == OperandType.ALMA:
            if not values.ready():
                return nan
            return sum(value * weight for value, weight in zip(values.values, self.alma_weights))
        if kind == OperandType.KAMA:
            history = self.window('kama_source', source, n + 1)
            if not isfinite(self.value):
                return values.mean()
            if not history.ready():
                return nan
            rows = list(history.values)
            volatility = sum(abs(b - a) for a, b in zip(rows, rows[1:]))
            efficiency = abs(rows[-1] - rows[0]) / volatility if volatility else 0.0
            alpha = (efficiency * (2 / 3 - 2 / 31) + 2 / 31) ** 2
            return self.value + alpha * (source - self.value)
        if kind in (OperandType.DEMA, OperandType.TEMA):
            first = self.average('first', source, n)
            second = self.average('second', first, n)
            if kind == OperandType.DEMA:
                return 2 * first - second
            return 3 * first - 3 * second + self.average('third', second, n)
        if kind == OperandType.ROC:
            history = self.window('roc', source, n + 1)
            return 100 * (source / history.values[0] - 1) if history.ready() and history.values[0] else nan
        if kind == OperandType.RSI:
            history = self.window('rsi_source', source, 2)
            difference = source - history.values[0] if history.ready() else nan
            gain = self.average('gain', max(difference, 0), n, wilder=True)
            loss = self.average('loss', max(-difference, 0), n, wilder=True)
            return 100 * gain / (gain + loss) if gain + loss > 0 else (0.0 if gain + loss == 0 else nan)
        if kind == OperandType.MACD:
            fast = self.average('fast', source, int(p['fast_period']))
            slow = self.average('slow', source, int(p['slow_period']))
            line = fast - slow
            signal = self.average('signal', line, int(p['signal_period']))
            return {'MACD_LINE': line, 'MACD_SIGNAL': signal, 'MACD_HISTOGRAM': line - signal}[p['output_line']]
        if kind == OperandType.BOLLINGER_BANDS:
            middle = values.mean()
            variance = sum((v - middle) ** 2 for v in values.values) / n if values.ready() else nan
            distance = sqrt(variance) * float(p['std_dev'])
            return {'UPPER': middle + distance, 'MIDDLE': middle, 'LOWER': middle - distance}[p['output_line']]
        if kind == OperandType.OBV:
            direction = 1 if previous is None or bar.close > previous.close else -1 if bar.close < previous.close else 0
            return (self.value if isfinite(self.value) else 0.0) + direction * bar.volume
        if kind == OperandType.ICHIMOKU_CLOUD:
            def mid(length):
                rows = list(self.bars)[-length:]
                return (max(b.high for b in rows) + min(b.low for b in rows)) / 2 if len(rows) == length else nan
            conversion, base = mid(int(p['tenkan'])), mid(int(p['kijun']))
            line = p['output_line']
            value = {'TENKAN': conversion, 'KIJUN': base, 'SENKOU_A': (conversion + base) / 2,
                     'SENKOU_B': mid(int(p['senkou'])), 'CHIKOU': bar.close}[line]
            self.delayed.append(value)
            return self.delayed[0] if line in ('SENKOU_A', 'SENKOU_B', 'CHIKOU') and len(self.delayed) == self.delayed.maxlen else (nan if line in ('SENKOU_A', 'SENKOU_B', 'CHIKOU') else value)
        if kind == OperandType.PARABOLIC_SAR:
            if previous is None:
                return nan
            if not isfinite(self.extreme):
                self.direction = -1 if previous.low - bar.low > max(bar.high - previous.high, 0) else 1
                self.extreme = previous.low if self.direction < 0 else previous.high
                self.value = previous.close
            level = self.value + self.acceleration * (self.extreme - self.value)
            reverse = bar.high > level if self.direction < 0 else bar.low < level
            extreme = min(self.extreme, bar.low) if self.direction < 0 else max(self.extreme, bar.high)
            if extreme != self.extreme:
                self.extreme = extreme
                self.acceleration = min(self.acceleration + float(p['af']), float(p['max_af']))
            level = max(previous.high, level) if self.direction < 0 else min(previous.low, level)
            if reverse:
                level, self.direction, self.acceleration = self.extreme, -self.direction, float(p['af'])
                self.extreme = bar.low if self.direction < 0 else bar.high
            return level

        high = self.window('high', bar.high, n)
        low = self.window('low', bar.low, n)
        highest, lowest = (max(high.values), min(low.values)) if high.ready() and low.ready() else (nan, nan)
        if kind == OperandType.DONCHIAN_CHANNEL:
            return {'UPPER': highest, 'MIDDLE': (highest + lowest) / 2, 'LOWER': lowest}[p['output_line']]
        if kind == OperandType.WILLIAMS_R:
            return -100 * (highest - bar.close) / (highest - lowest) if highest > lowest else nan
        if kind == OperandType.STOCHASTIC:
            raw = 100 * (bar.close - lowest) / (highest - lowest) if highest > lowest else nan
            k = self.window('smooth_k', raw, int(p['smooth'])).mean()
            d = self.window('smooth_d', k, int(p['d_period'])).mean()
            return d if p['output_line'] == 'D' else k
        typical = (bar.high + bar.low + bar.close) / 3
        if kind == OperandType.CCI:
            prices = self.window('typical', typical, n)
            mean = prices.mean()
            deviation = sum(abs(v - mean) for v in prices.values) / n if prices.ready() else nan
            return (typical - mean) / (0.015 * deviation) if deviation > 0 else nan
        if kind == OperandType.MFI:
            prior = (previous.high + previous.low + previous.close) / 3 if previous else typical
            positive = self.window('positive_flow', typical * bar.volume if typical > prior else 0.0, n)
            negative = self.window('negative_flow', typical * bar.volume if typical < prior else 0.0, n)
            total = positive.mean() + negative.mean()
            return 100 * positive.mean() / total if total > 0 else nan
        true_range = max(bar.high - bar.low, abs(bar.high - previous.close), abs(bar.low - previous.close)) if previous else nan
        atr = self.average('atr', true_range, n, wilder=True)
        if kind == OperandType.ATR:
            return atr
        if kind == OperandType.KELTNER_CHANNEL:
            middle = self.average('center', source, n)
            spread = self.average('range_ema', true_range, n) * float(p['multiplier'])
            return {'UPPER': middle + spread, 'MIDDLE': middle, 'LOWER': middle - spread}[p['output_line']]
        if kind == OperandType.SUPERTREND:
            lower, upper = (bar.high + bar.low) / 2 - atr * float(p['multiplier']), (bar.high + bar.low) / 2 + atr * float(p['multiplier'])
            if bar.close > self.upper:
                self.direction = 1
            elif bar.close < self.lower:
                self.direction = -1
            else:
                if self.direction > 0 and lower < self.lower:
                    lower = self.lower
                if self.direction < 0 and upper > self.upper:
                    upper = self.upper
            self.lower, self.upper = lower, upper
            return lower if self.direction > 0 else upper
        if kind in (OperandType.ADX, OperandType.DMI):
            up, down = (bar.high - previous.high, previous.low - bar.low) if previous else (nan, nan)
            plus = self.average('plus', up if up > max(down, 0) else 0.0, n, wilder=True)
            minus = self.average('minus', down if down > max(up, 0) else 0.0, n, wilder=True)
            plus_di, minus_di = (100 * plus / atr, 100 * minus / atr) if atr > 0 else (nan, nan)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if plus_di + minus_di > 0 else nan
            adx = self.average('adx', dx, n, wilder=True)
            return {'ADX': adx, 'PLUS_DI': plus_di, 'MINUS_DI': minus_di}[p['output_line']]
        raise ValueError(f'No numerical implementation for {kind}.')
