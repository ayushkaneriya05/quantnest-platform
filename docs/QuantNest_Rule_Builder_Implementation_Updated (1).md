# QuantNest Rule Builder — Stock-First Predicate, Expression, Event & Strategy State Implementation Specification

## 1. Purpose

This document is the build-ready implementation specification for expanding the QuantNest strategy builder from the current binary rule model:

`Operand A -> Comparison -> Operand B`

to a composable expression system capable of representing temporal, statistical, rolling-window, price-action, session, stateful, and event-sequence strategy logic while preserving existing rules.

The implementation target is the `algo-high-performance` branch of `ayushkaneriya05/quantnest-platform`.

The current architecture already provides:

- Universal operand enum and JSON parameters.
- Indicator engine with caching.
- Rule evaluator returning boolean Series.
- Rule groups with AND/OR.
- Multi-timeframe operands with forward-fill alignment.
- Strategy executor for entry and exit orchestration.
- Backtest engine with completed-candle signal evaluation and next-candle market execution.
- Paper/live execution layers that consume strategy decisions.
- Warm-up/market-data lookback analysis.

The goal is to add a new expression/predicate layer rather than rewrite the backtest or execution engines.

---


## 1A. Current Product Scope — STOCK FIRST

This release is intentionally designed around the data that QuantNest can reliably research and execute today.

### Current target asset class

**Stocks / Equity instruments only.**

The current market-data implementation stores canonical candles with:

```text
symbol
timeframe
time
open
high
low
close
volume
```

and the repository's canonical persistence path is designed around `1m` and `1D` candles. Supported higher timeframes are derived from those stock candles.

Therefore Release 1/2 must build the widest possible **stock/OHLCV strategy-language capability** rather than exposing unavailable F&O inputs.

### Allowed current-release data

The current builder may use:

```text
OPEN
HIGH
LOW
CLOSE
LTP / current price context
VOLUME

ALL CURRENT OHLCV-BASED INDICATORS
ROLLING STATISTICS
STATISTICAL TRANSFORMS DERIVED FROM OHLCV
CANDLE/PATTERN DATA DERIVED FROM OHLC
SESSION/DAY/WEEK/MONTH LEVELS DERIVED FROM STOCK CANDLES
OPENING-RANGE DATA DERIVED FROM STOCK CANDLES
MULTI-TIMEFRAME DATA DERIVED FROM STOCK CANDLES
POSITION STATE
STRATEGY STATE
EVENT ANCHORS
```

### Explicitly deferred

The following must **not** be exposed as current backtestable inputs:

```text
OPEN_INTEREST
CHANGE_IN_OI
OPTION_IV
DELTA
GAMMA
THETA
VEGA
PUT_CALL_RATIO
BID
ASK
ORDER_BOOK
DEPTH_IMBALANCE
FUTURES_BASIS
FUTURES_ROLLOVER
OPTION_CHAIN_SELECTION
```

These require a separate F&O/microstructure historical + live data pipeline.

### Data-availability principle

An operand is current-release eligible only when:

```text
historical stock data exists
AND
backtest can reproduce it
AND
paper/live can produce equivalent semantics
AND
timestamps are known
AND
warm-up/lookback is computable
AND
no-lookahead behavior is defined
```

If these conditions are not met, keep the capability hidden/disabled.


## 2. Repository Scope

All code changes must target branch:

`algo-high-performance`

Do not modify `main` unless explicitly requested.

Primary existing files reviewed:

### Backend

- `backend/common/enums.py`
- `backend/rules_engine/models.py`
- `backend/rules_engine/serializers.py`
- `backend/rules_engine/views.py`
- `backend/rules_engine/evaluator.py`
- `backend/rules_engine/indicators.py`
- `backend/rules_engine/math_utils.py`
- `backend/rules_engine/metadata.py`
- `backend/strategy_engine/executor.py`
- `backend/strategy_engine/exit_actions.py`
- `backend/backtesting/engine.py`
- `backend/risk_management/evaluator.py`

### Frontend

- `frontend/src/features/dashboard/pages/strategy/EntryRulesBuilder.jsx`
- `frontend/src/features/dashboard/pages/strategy/ExitRulesBuilder.jsx`
- `frontend/src/features/dashboard/pages/strategy/components/OperandSelector.jsx`
- `frontend/src/features/dashboard/pages/strategy/components/MathExpressionBuilder.jsx`
- `frontend/src/features/dashboard/pages/strategy/StrategyConfigNav.jsx`

The current `Rule` database model stores two operand types, parameter objects, two timeframe overrides, one comparison operator, and active status. The current evaluator resolves both operands and performs the comparison. The group evaluator then combines rule results using AND/OR. This specification preserves that behavior for legacy rules.

---

# 3. Current Architecture and Limitation

## 3.1 Existing rule model

Current logical shape:

```text
Rule
 |
 +-- operand_a
 +-- comparison
 +-- operand_b
```

A group contains multiple rules:

```text
Group
 |
 +-- Rule 1
 +-- Rule 2
 +-- Rule 3
 |
 +-- AND / OR
```

Groups themselves are combined by strategy entry/exit configuration operators.

## 3.2 Current operand capabilities

Current operand catalog already includes:

### Price and market data

- LTP
- OPEN
- HIGH
- LOW
- CLOSE
- VOLUME
- VWAP
- HL2
- HLC3
- OHLC4
- CURRENT_DAY_OPEN
- PREV_WEEK_HIGH
- PREV_WEEK_LOW

### Candle analysis

- CANDLE_PATTERN
- CANDLE_BODY_SIZE

### Indicators

- SMA
- EMA
- WMA
- HMA
- ALMA
- KAMA
- DEMA
- TEMA
- RSI
- ROC
- MACD
- BOLLINGER_BANDS
- SUPERTREND
- ADX
- DMI
- STOCHASTIC
- ATR
- CCI
- WILLIAMS_R
- OBV
- MFI
- PIVOT_POINT
- KELTNER_CHANNEL
- DONCHIAN_CHANNEL
- PARABOLIC_SAR
- ICHIMOKU_CLOUD

### Position state

- POSITION_PNL_PERCENTAGE
- POSITION_PNL_POINTS
- TRAILING_PEAK_OFFSET
- ENTRY_PRICE
- POSITION_RR_RATIO

### Math

- CONSTANT
- MATH_EXPRESSION

## 3.3 What is fundamentally missing

The missing capability is not more indicators. It is the ability to ask higher-order questions about a value or condition over time.

Examples:

```text
RISING(EMA20, 3)
TRUE_COUNT(CLOSE > EMA20, 5) >= 4
Z_SCORE(CLOSE, 50) < -2
PERCENTILE_RANK(VOLUME, 100) > 90
BREAKS_PREVIOUS_HIGH(HIGH, 20)
WITHIN_BARS(RSI_CROSS_ABOVE_30, 5)
```

The current binary rule structure evaluates all component rules at the same bar. It has no first-class concept of:

- rolling windows
- temporal persistence
- event age
- sequence state
- nested conditions
- statistical normalization
- session-derived dynamic levels

`MATH_EXPRESSION` is useful for arithmetic composition, but it is intentionally restricted and is not a general temporal expression language.

---

# 4. Target Architecture

The new architecture is:

```text
Frontend Builder
      |
      v
Rule Expression JSON
      |
      v
Expression Compiler / Evaluator
      |
      +------------------+
      |                  |
      v                  v
Series operands      Predicates / sequences
      |                  |
      +---------+--------+
                |
                v
         Boolean / numeric Series
                |
                v
          Rule Group AND/OR
                |
                v
        StrategyExecutor
                |
      +---------+---------+
      |         |         |
   Backtest    Paper      Live
```

The central concept is a recursive expression tree.

---

# 5. Expression Node Model

## 5.1 Node categories

Every expression node belongs to one of:

```text
OPERAND
TRANSFORM
COMPARISON
LOGICAL
PREDICATE
EVENT
ANCHOR
STATE_REFERENCE
SEQUENCE
```

`EVENT`, `ANCHOR`, `STATE_REFERENCE`, and `SEQUENCE` are mandatory additions for advanced setup/trigger strategies.

Generic pattern:

```text
EVENT
  -> CAPTURE values
  -> ARM setup
  -> WAIT
  -> TRIGGER
  -> ACTION
```

This is intentionally generic; it must not be hard-coded for one strategy.

### OPERAND

Returns a scalar/series.

Examples:

```text
CLOSE
EMA(20)
RSI(14)
POSITION_PNL_PERCENTAGE
```

### TRANSFORM

Consumes one or more expressions and returns a derived numeric series.

Examples:

```text
ROLLING_MAX
ROLLING_MIN
ROLLING_MEAN
ROLLING_STD
PERCENT_CHANGE
Z_SCORE
PERCENTILE_RANK
```

### COMPARISON

Returns a boolean series.

Examples:

```text
GT
LT
GTE
LTE
EQ
NEQ
CROSSES_ABOVE
CROSSES_BELOW
```

### LOGICAL

Combines boolean expressions.

Examples:

```text
AND
OR
NOT
```

### PREDICATE

Consumes one or more expressions and answers a higher-order question.

Examples:

```text
RISING
FALLING
TRUE_COUNT
CONSECUTIVE
BARS_SINCE
WITHIN_BARS
AT_HIGHEST
BREAKS_HIGH
```

### SEQUENCE

Represents ordered event logic and runtime memory.

Example:

```text
A
within 5 bars
B
within 3 bars
C
```

---

# 6. Canonical JSON Schema

Do not immediately remove the legacy flat rule columns. Introduce an optional expression payload first.

Recommended model field:

```python
expression = models.JSONField(null=True, blank=True)
```

Legacy rules remain valid when `expression` is null.

## 6.1 Example comparison

```json
{
  "node_type": "COMPARISON",
  "operator": "GT",
  "left": {
    "node_type": "OPERAND",
    "type": "CLOSE",
    "params": {},
    "timeframe": null
  },
  "right": {
    "node_type": "OPERAND",
    "type": "EMA",
    "params": {
      "period": 20,
      "source": "close"
    },
    "timeframe": null
  }
}
```

## 6.2 Example rolling transform

```json
{
  "node_type": "TRANSFORM",
  "type": "ROLLING_MAX",
  "params": {
    "window": 20,
    "include_current": false
  },
  "source": {
    "node_type": "OPERAND",
    "type": "HIGH",
    "params": {},
    "timeframe": null
  }
}
```

## 6.3 Example nested predicate

```json
{
  "node_type": "COMPARISON",
  "operator": "GTE",
  "left": {
    "node_type": "PREDICATE",
    "type": "TRUE_COUNT",
    "params": {
      "window": 5
    },
    "source": {
      "node_type": "COMPARISON",
      "operator": "GT",
      "left": {
        "node_type": "OPERAND",
        "type": "CLOSE"
      },
      "right": {
        "node_type": "OPERAND",
        "type": "EMA",
        "params": {
          "period": 20
        }
      }
    }
  },
  "right": {
    "node_type": "OPERAND",
    "type": "CONSTANT",
    "params": {
      "value": 4
    }
  }
}
```

## 6.4 Example logical expression

```json
{
  "node_type": "LOGICAL",
  "operator": "AND",
  "children": [
    {
      "node_type": "COMPARISON",
      "operator": "GT",
      "left": {
        "node_type": "OPERAND",
        "type": "CLOSE"
      },
      "right": {
        "node_type": "TRANSFORM",
        "type": "ROLLING_MAX",
        "params": {
          "window": 20,
          "include_current": false
        },
        "source": {
          "node_type": "OPERAND",
          "type": "HIGH"
        }
      }
    },
    {
      "node_type": "PREDICATE",
      "type": "RISING",
      "params": {
        "bars": 3
      },
      "source": {
        "node_type": "OPERAND",
        "type": "EMA",
        "params": {
          "period": 20
        }
      }
    }
  ]
}
```

---


# 6A. Event Anchor / Setup-State Engine

## 6A.1 Why this is required

Many important stock strategies are not same-bar comparisons. They have the form:

```text
detect event
→ remember event candle/value
→ wait for later condition
→ act using remembered values
```

Examples:

```text
EMA crossover → save crossover candle high/low → breakout
Opening range → save range → breakout
Breakout → save breakout level → retest
Candle pattern → save pattern range → trigger
Swing low/high → save swing values → retracement
```

A flat `A comparator B` rule cannot express the persistence of a value from a specific historical event.

## 6A.2 Anchor schema

Use a generic anchor object:

```json
{
  "name": "setup",
  "created_at": "timestamp",
  "created_bar_index": 12345,
  "values": {
    "high": 105.0,
    "low": 100.0,
    "close": 104.5,
    "range": 5.0
  },
  "status": "ARMED",
  "expires_after_bars": 10
}
```

## 6A.3 Example requested strategy

```text
SETUP:
    CLOSE crosses above EMA20
    AND EMA20 > EMA50

CAPTURE:
    setup.high = HIGH
    setup.low = LOW
    setup.range = HIGH - LOW

WAIT:
    max 10 bars

INVALIDATE:
    CLOSE < setup.low

TRIGGER:
    CLOSE crosses above setup.high

ACTION:
    BUY

STOP:
    setup.low

TARGET:
    setup.high + 2 * setup.range
```

This must be a mandatory end-to-end acceptance test.

## 6A.4 Anchor lifecycle

```text
NONE
 ↓
CREATED
 ↓
ARMED
 ├── TRIGGERED → CONSUMED
 ├── INVALIDATED → CLEAR
 └── EXPIRED → CLEAR
```

## 6A.5 Anchor replacement policy

Support:

```text
KEEP_FIRST
REPLACE_WITH_LATEST
IGNORE_WHILE_ARMED
QUEUE_MULTIPLE
```

Recommended initial behavior:

```text
IGNORE_WHILE_ARMED
```

This prevents accidental multiple overlapping setups.

## 6A.6 Dynamic order/risk references

Anchors may feed expressions for:

```text
ENTRY_TRIGGER_PRICE
STOP_LOSS
TARGET
STOP_DISTANCE
RISK_PER_SHARE
POSITION_SIZE
```

Examples:

```text
SL = anchor.setup.low

TARGET = anchor.setup.high + 2 * anchor.setup.range

STOP_DISTANCE = entry_price - anchor.setup.low

RISK_BASED_QUANTITY = risk_amount / STOP_DISTANCE
```

The rule/anchor engine resolves these values. The execution layer remains responsible for placing the resulting order.

## 6A.7 State isolation

Anchor state must be isolated by:

```text
strategy
instrument
sequence/anchor node
```

A setup for one stock must never leak into another stock.


# 7. Backward Compatibility Strategy

The legacy rule format must remain executable.

Implement:

```python
RuleExpressionEvaluator.evaluate_rule(rule)
```

with this behavior:

```text
if rule.expression exists:
    evaluate expression tree
else:
    evaluate legacy operand_a/comparison/operand_b
```

This allows all existing strategies to continue working without migration of stored JSON.

Do not delete the existing fields until the new expression system has been proven across backtest, paper, and live.

---

# 8. New Operand/Transform Registry

Create a central registry, for example:

`backend/rules_engine/registry.py`

Recommended structure:

```python
OPERAND_REGISTRY = {
    "CLOSE": {
        "category": "PRICE",
        "output_type": "FLOAT_SERIES",
        "evaluator": resolve_close,
        "supports_timeframe": True,
        "requires_state": False,
        "evaluation_mode": "VECTOR_STREAM"
    },
    "EMA": {
        "category": "INDICATOR",
        "output_type": "FLOAT_SERIES",
        "evaluator": resolve_ema,
        "supports_timeframe": True,
        "requires_state": False,
        "evaluation_mode": "VECTOR_STREAM"
    }
}

TRANSFORM_REGISTRY = {
    "ROLLING_MAX": {...},
    "ROLLING_MIN": {...},
    "ROLLING_MEAN": {...},
    "ROLLING_STD": {...},
    "PERCENT_CHANGE": {...},
    "Z_SCORE": {...},
    "PERCENTILE_RANK": {...}
}

PREDICATE_REGISTRY = {
    "RISING": {...},
    "FALLING": {...},
    "TRUE_COUNT": {...},
    "CONSECUTIVE": {...},
    "BARS_SINCE": {...},
    "WITHIN_BARS": {...},
    "AT_HIGHEST": {...},
    "AT_LOWEST": {...},
    "BREAKS_HIGH": {...},
    "BREAKS_LOW": {...}
}
```

The registry is the source of truth for frontend metadata as well as backend validation.

---

# 9. Operand Descriptor Contract

Every registered node should expose a descriptor:

```json
{
  "type": "RISING",
  "category": "PREDICATE",
  "label": "Rising",
  "output_type": "BOOLEAN_SERIES",
  "inputs": [
    {
      "name": "source",
      "kind": "EXPRESSION",
      "required": true
    }
  ],
  "params": [
    {
      "key": "bars",
      "type": "integer",
      "min": 1,
      "default": 3
    }
  ],
  "supports_timeframe": true,
  "requires_state": false,
  "evaluation_mode": "VECTOR_STREAM"
}
```

This should eventually replace frontend hard-coded `PARAM_CONFIG` entries.

---

# 10. First Implementation Set

Implement the following before advanced features.

## 10.1 Rolling transforms

### ROLLING_MAX

```python
source.rolling(window).max()
```

Parameters:

- window
- include_current

When `include_current=false`:

```python
source.shift(1).rolling(window).max()
```

### ROLLING_MIN

Equivalent using `.min()`.

### ROLLING_MEAN

Equivalent using `.mean()`.

### ROLLING_SUM

Equivalent using `.sum()`.

### ROLLING_STD

Use a defined `ddof` and keep it consistent between backtest/live.

Recommended default:

```text
ddof = 0
```

unless existing analytics conventions require otherwise.

---

# 11. Statistical transforms

## 11.1 PERCENT_CHANGE

```python
source.pct_change(periods=n) * 100
```

Parameters:

- periods

## 11.2 Z_SCORE

```python
mean = source.rolling(window).mean()
std = source.rolling(window).std(ddof=0)
z = (source - mean) / std
```

Rules:

- If standard deviation is zero, return NaN.
- Never substitute zero for undefined z-score.
- No future rows may contribute to a result.

## 11.3 PERCENTILE_RANK

Returns current observation's percentile position within the trailing window.

Suggested semantics:

```text
window = 100
current value included
rank = percent of trailing observations <= current value
```

Output:

```text
0..100
```

---

# 12. Volume transforms

## RELATIVE_VOLUME

Definition:

```python
current_volume / rolling_mean(volume, window)
```

Example:

```text
RELATIVE_VOLUME(20) > 2
```

Edge cases:

- rolling mean = 0 -> NaN
- insufficient bars -> NaN

This should live under transforms because it returns numeric series.

---

# 13. Trend predicates

## RISING

```python
source.diff() > 0
```

For `bars=3`, the condition is true when the source has increased on each of the last 3 transitions.

```python
increasing = source.diff() > 0
result = increasing.rolling(bars).sum() == bars
```

## FALLING

Mirror of RISING.

## CONSECUTIVE

Input:

```text
boolean expression
```

Parameters:

```text
bars
```

Returns true only when the input was true for all requested consecutive bars.

---

# 14. TRUE_COUNT

Input:

```text
boolean expression
```

Parameters:

```text
window
```

Output:

```python
source.astype(int).rolling(window).sum()
```

Then ordinary comparison can be used:

```text
TRUE_COUNT(CLOSE > EMA20, 5) >= 4
```

This is preferable to making a separate `AT_LEAST_N_TRUE` predicate for every variation.

---

# 15. Event predicates

## BARS_SINCE

Input:

```text
boolean event series
```

Output:

```text
number of bars since most recent true event
```

Semantics:

```text
Event bar -> 0
Next bar -> 1
Next bar -> 2
```

Before first event:

```text
NaN
```

Do not return an arbitrary large integer.

## WITHIN_BARS

Input:

```text
event expression
```

Parameter:

```text
window
```

Definition:

```text
BARS_SINCE(event) <= window
```

But ensure that an event has actually happened. `NaN <= window` must not accidentally become true.

---

# 16. Extremum predicates

## AT_HIGHEST

```text
source == rolling_max(source, window)
```

Parameters:

- window
- include_current

## AT_LOWEST

Mirror of AT_HIGHEST.

## BREAKS_HIGH

Meaning:

```text
current source > highest value of previous N bars
```

Recommended implementation:

```python
previous_high = source.shift(1).rolling(window).max()
result = source > previous_high
```

## BREAKS_LOW

Mirror using rolling minimum.

This explicit previous-window semantics prevents the current observation from trivially being its own breakout reference.

---

# 17. Price-action predicates

Add these after the first predicate release:

```text
BULLISH_BAR
BEARISH_BAR
CANDLE_RANGE
BODY_PERCENT
UPPER_WICK_PERCENT
LOWER_WICK_PERCENT
BODY_TO_RANGE_RATIO
GAP_PERCENT
```

Definitions must always state the exact denominator and zero-division behavior.

---

# 18. Session-level operands

Add these as numeric series/levels:

```text
DAY_HIGH
DAY_LOW
PREV_DAY_HIGH
PREV_DAY_LOW
PREV_DAY_CLOSE
WEEK_OPEN
WEEK_HIGH
WEEK_LOW
MONTH_OPEN
MONTH_HIGH
MONTH_LOW
```

Then add session-structure:

```text
OPENING_RANGE_HIGH
OPENING_RANGE_LOW
```

Parameters:

- session date basis
- duration
- timezone

Important: these must be calculated from only candles that occurred before the evaluation timestamp.

---

# 19. Sequence Engine

Sequence logic is not just another flat operand. It requires a runtime state model.

## 19.1 Data structure

Example:

```json
{
  "node_type": "SEQUENCE",
  "steps": [
    {
      "expression": { ... },
      "max_bars_after_previous": null
    },
    {
      "expression": { ... },
      "max_bars_after_previous": 5
    },
    {
      "expression": { ... },
      "max_bars_after_previous": 3
    }
  ],
  "restart_mode": "RESET_ON_COMPLETE_OR_TIMEOUT"
}
```

## 19.2 Runtime state

For each active strategy/instrument/sequence:

```python
{
    "sequence_step": 0,
    "step_started_bar": None,
    "last_event_timestamp": None,
    "active": False
}
```

The state must be isolated per:

```text
strategy
instrument
sequence node
```

## 19.3 Backtest behavior

Sequence evaluation must be deterministic from historical candles.

Recommended algorithm:

1. Evaluate step 1 event series.
2. When true, activate step 2 and store timestamp/index.
3. Evaluate step 2 only while within max window.
4. When step 2 fires, advance to step 3.
5. On completion, emit true on the completion bar and reset.
6. On timeout, reset according to `restart_mode`.

## 19.4 Live behavior

Maintain equivalent state in the strategy runtime cache.

Do not reconstruct sequence state differently from backtest.

---

# 20. Evaluation Context

Create an evaluation context abstraction:

```python
class EvaluationContext:
    dataframe
    mtf_data
    indicator_engines
    state
    timestamp
    instrument
    strategy_id
    mode
```

Where:

```text
mode = BACKTEST | PAPER | LIVE
```

The evaluator should not directly inspect Celery, Redis, broker objects, or HTTP clients.

It should receive state through the context.

---

# 21. Expression Compiler

Create:

`backend/rules_engine/expression_engine.py`

Recommended API:

```python
class ExpressionEngine:
    def __init__(self, context):
        self.context = context

    def evaluate(self, node):
        node_type = node.get("node_type")

        if node_type == "OPERAND":
            return self.evaluate_operand(node)
        if node_type == "TRANSFORM":
            return self.evaluate_transform(node)
        if node_type == "COMPARISON":
            return self.evaluate_comparison(node)
        if node_type == "LOGICAL":
            return self.evaluate_logical(node)
        if node_type == "PREDICATE":
            return self.evaluate_predicate(node)
        if node_type == "SEQUENCE":
            return self.evaluate_sequence(node)

        raise ExpressionValidationError(...)
```

This becomes the central composition layer.

---

# 22. Comparison implementation

Reuse the current comparison behavior for:

```text
GT
LT
GTE
LTE
EQ
NEQ
CROSSES_ABOVE
CROSSES_BELOW
```

Keep the current fast Numba cross helpers.

When both operands are Series:

1. Verify timeframe/index alignment.
2. Align the right operand to the left operand's evaluation timeframe.
3. Apply the comparison.
4. Normalize to boolean Series.

Do not forward-fill across a semantic gap where a higher-timeframe value is not yet known.

---

# 23. Timeframe semantics

Every node which consumes market data must have an explicit timeframe resolution rule.

Recommended:

```text
Node has timeframe
    -> evaluate source and nested transforms in that timeframe
    -> produce result in that timeframe
    -> align to parent timeframe
```

Example:

```text
RISING(EMA20, bars=3, timeframe=15m)
```

means:

```text
EMA20 calculated on 15m bars
RISING evaluated across 3 x 15m bars
boolean result aligned to base timeframe
```

Do NOT:

```text
15m EMA -> ffill to 1m -> RISING(3)
```

because that changes the meaning to 3 one-minute samples rather than three 15-minute observations.

---

# 24. Current/Completed Candle Policy

Preserve QuantNest's current completed-candle signal model.

For signal evaluation:

```text
current forming candle = not yet a signal candle
```

For backtesting, the decision is generated from the completed candle and existing architecture queues standard entries for the next candle open.

New transforms/predicates must therefore be defined relative to the evaluated completed bar.

For example:

```text
BREAKS_HIGH(HIGH, 20)
```

means the completed current bar's high exceeds the previous 20 completed bars' highs.

---

# 24A. Tick / Candle / Intrabar Evaluation Semantics

The rule system must distinguish **signal-generation frequency** from **price-protection monitoring**.

Every expression or executable trigger must declare an evaluation domain:

```text
CANDLE
TICK
INTRABAR
HYBRID
```

### CANDLE

Evaluate only when the relevant candle is completed.

Use for:

```text
CLOSE > EMA20
RSI > 70
CLOSE crosses above EMA20
CANDLE_PATTERN
BREAKS_HIGH(...)
```

The existing completed-candle policy remains the default for ordinary strategy conditions.

### TICK

Evaluate incrementally on incoming market ticks / LTP.

Use for true breakout and price-trigger semantics such as:

```text
LTP > setup.high
LTP crosses above setup.high
LTP <= setup.low
LTP >= target
```

A tick-level cross must use the transition:

```text
previous_ltp <= level
AND
current_ltp > level
```

and similarly for bearish crosses:

```text
previous_ltp >= level
AND
current_ltp < level
```

Do not implement a tick cross as only `current_ltp > level`, because that would remain true on every later tick above the level.

### INTRABAR

Evaluate against available intrabar OHLC information when the data source supports it.

This is useful for backtesting when exact tick data is unavailable, but the engine must make the intrabar assumption explicit.

Do not claim tick-exact behavior from ordinary 1-minute OHLCV data.

### HYBRID

Use candle evaluation to create setup/state and tick evaluation to trigger or protect the resulting order.

Canonical example:

```text
COMPLETED CANDLE
    -> evaluate setup
    -> capture setup.high / setup.low / setup.range
    -> ARM setup

LIVE TICKS
    -> LTP crosses above setup.high
    -> BUY

LIVE TICKS
    -> LTP <= setup.low
    -> STOP LOSS

LIVE TICKS
    -> LTP >= setup.high + 2 * setup.range
    -> TARGET
```

This is the required semantic model for a true breakout strategy.

---

## 24A.1 Static vs Dynamic Price Levels

Separate **level calculation** from **level monitoring**.

If a level is resolved once at entry:

```text
SL = setup.low
TARGET = setup.high + 2 * setup.range
```

calculate it when the order/position is created, store the resolved level in the execution state, and monitor that level on every tick.

Do not recompute the entire expression tree on every tick.

For a genuinely dynamic trailing level:

```text
SL = highest_price_since_entry - offset
```

the execution/risk state may update the level incrementally as new ticks arrive.

For candle-derived dynamic levels such as:

```text
SL = entry_price - 1.5 * ATR14
```

the default behavior should be:

```text
completed candle
    -> recalculate ATR
    -> update execution level
    -> tick monitor watches the updated level
```

unless the strategy explicitly declares a different intrabar/tick semantic.

---

## 24A.2 Tick Evaluation Is Separate from Indicator Recalculation

Tick-triggered execution does not mean every indicator must be recalculated on every tick.

For example:

```text
EMA20        -> candle series
RSI14        -> candle series
setup.high   -> captured state
LTP          -> tick stream
```

A strategy can therefore have:

```text
CANDLE:
    CLOSE crosses above EMA20
    AND EMA20 > EMA50

TICK:
    LTP crosses above setup.high
```

The tick engine consumes the latest resolved/captured strategy state; it does not rebuild the full Pandas indicator dataframe for each tick.

---

## 24A.3 Backtest Data Requirement for Tick Triggers

True tick-level trigger behavior cannot be reproduced exactly from ordinary 1-minute OHLCV candles.

Example:

```text
Open = 104
High = 106
Low = 103
Close = 104.50
setup.high = 105
```

The candle proves that 105 was reached, but does not prove the exact intrabar order of prices.

Therefore:

```text
TICK strategy + true tick historical data
    -> exact tick semantics

TICK strategy + only 1m OHLCV
    -> must use explicit approximation or be rejected

INTRABAR strategy + 1m OHLCV
    -> allowed only under documented OHLC assumptions
```

The deployment/backtest validator must never silently present an OHLC approximation as tick-exact execution.

---

# 25. Warm-up / Lookback Engine

Current `IndicatorRequirementAnalyzer` already calculates operand lookback and warm-up days.

Extend this to expression trees.

Create:

```python
ExpressionMetadataAnalyzer.analyze(node)
```

Return:

```python
{
    "lookback": 105,
    "timeframes": {
        "5m": 105,
        "15m": 35
    },
    "requires_state": False,
    "evaluation_mode": "VECTOR_STREAM",
    "output_type": "BOOLEAN_SERIES"
}
```

## 25.1 Lookback examples

### EMA 20

```text
base indicator lookback = existing EMA rule
```

### RISING(EMA20, 3)

```text
EMA lookback + 3
```

### TRUE_COUNT(condition, 5)

```text
condition lookback + 5
```

### Z_SCORE(CLOSE, 50)

```text
50
```

### BREAKS_HIGH(HIGH, 20)

```text
21
```

because the implementation uses `shift(1)` before rolling.

---

# 26. Output Type System

Every node must declare:

```text
FLOAT_SERIES
INTEGER_SERIES
BOOLEAN_SERIES
SCALAR
BOOLEAN
```

Examples:

```text
EMA -> FLOAT_SERIES
ROLLING_MAX -> FLOAT_SERIES
TRUE_COUNT -> INTEGER_SERIES
RISING -> BOOLEAN_SERIES
POSITION_PNL_PERCENTAGE -> SCALAR
```

Use output type validation before evaluation.

Reject invalid combinations instead of silently returning false.

---

# 27. Error Semantics

The current evaluator often turns errors into a false Series. Keep that behavior for legacy operation, but the new expression engine should distinguish:

```text
VALID_FALSE
VALID_TRUE
INVALID_EXPRESSION
INSUFFICIENT_DATA
RUNTIME_ERROR
UNSUPPORTED_IN_MODE
```

For strategy execution:

- INVALID_EXPRESSION -> strategy configuration error; should be surfaced to user.
- INSUFFICIENT_DATA -> valid no-signal state.
- UNSUPPORTED_IN_MODE -> configuration/deployment error.
- RUNTIME_ERROR -> log, alert, fail closed.

Do not silently convert a malformed expression into a legitimate false signal.

---

# 28. Frontend Architecture

The current `OperandSelector.jsx` contains a hard-coded `PARAM_CONFIG` and categories.

Replace this gradually with metadata-driven components.

Recommended components:

```text
ExpressionBuilder.jsx
ExpressionNodeEditor.jsx
OperandNodeEditor.jsx
TransformNodeEditor.jsx
PredicateNodeEditor.jsx
ComparisonNodeEditor.jsx
LogicalNodeEditor.jsx
SequenceBuilder.jsx
```

Legacy `OperandSelector` should remain for compatibility while the new builder is introduced.

---

# 29. Frontend UX

Top-level condition builder:

```text
Condition Type

[ Comparison ]
[ Predicate  ]
[ Logical    ]
[ Sequence   ]
```

## Comparison UI

```text
[Operand A] [GT ▼] [Operand B]
```

## Predicate UI

Example:

```text
Predicate: [Rising ▼]
Source:    [EMA ▼]
Period:    [20]
Bars:      [3]
Timeframe: [15m]
```

## Nested predicate

Example:

```text
True Count

Condition:
  [ CLOSE ] [ > ] [ EMA(20) ]

Window: 5
```

Then optionally:

```text
Compare Result [ >= ] [4]
```

## Sequence UI

```text
WHEN
  [condition builder]

WITHIN
  [5] bars

THEN
  [condition builder]

WITHIN
  [3] bars

THEN
  [condition builder]
```

---

# 30. Frontend Validation

Before save, validate:

- required node fields exist
- numeric parameters are within limits
- node output types are compatible
- sequence contains at least 2 steps
- timeframe values are valid
- windows are positive integers
- expressions are not empty
- unsupported combinations are blocked

The backend remains authoritative and must repeat validation.

---

# 31. Backend API Changes

Extend `RuleSerializer` to accept:

```text
expression
```

but preserve current fields.

Validation should support both modes.

Recommended validation methods:

```python
validate_expression()
validate_node()
validate_node_types()
validate_params()
validate_timeframe()
```

Potential API addition:

```text
GET /rules-engine/metadata/
```

Response:

```json
{
  "operands": [...],
  "transforms": [...],
  "predicates": [...],
  "comparisons": [...],
  "logical_operators": [...],
  "timeframes": [...]
}
```

Frontend should consume this rather than independently recreating the backend capability list.

---

# 32. Rule Model Migration

Add one JSONField:

```python
expression = models.JSONField(null=True, blank=True)
```

Recommended migration name:

```text
00XX_add_rule_expression
```

Do not change existing operand columns.

No data migration is required immediately.

Optional future migration can convert simple legacy rules into expression trees, but this should only be done after the new evaluator is proven.

---

# 33. Legacy Rule Adapter

Create:

```python
legacy_rule_to_expression(rule)
```

Example:

```python
{
  "operand_a_type": "EMA",
  "operand_a_params": {"period": 20},
  "comparison": "GT",
  "operand_b_type": "EMA",
  "operand_b_params": {"period": 50}
}
```

becomes:

```json
{
  "node_type": "COMPARISON",
  "operator": "GT",
  "left": {
    "node_type": "OPERAND",
    "type": "EMA",
    "params": {"period": 20}
  },
  "right": {
    "node_type": "OPERAND",
    "type": "EMA",
    "params": {"period": 50}
  }
}
```

This avoids duplicate comparison logic.

---

# 34. Integration with StrategyExecutor

Current `StrategyExecutor` calls `RuleEvaluator.evaluate_group()` for entry and exit groups.

Preserve this contract.

Change the internals so:

```python
RuleEvaluator.evaluate_rule(rule, state)
```

becomes:

```python
if expression exists:
    return expression_engine.evaluate(expression)
else:
    return legacy_evaluate_rule(rule, state)
```

The returned object remains:

```text
Boolean Series
```

Therefore the existing entry and exit group orchestration can continue using it.

---

# 35. Entry Evaluation

Current entry flow remains conceptually:

```text
Entry Groups
   -> evaluate each group
   -> group logical operator
   -> strategy entry signal
   -> can_enter()
   -> order processing
```

New predicates simply produce better boolean signals.

No new execution code is required for rule-only predicates.

---

# 36. Exit Evaluation

The current executor evaluates:

1. Stop loss groups.
2. Target groups.
3. Custom exit groups.

Keep this ordering.

Predicate expressions may consume position state when explicitly allowed.

Example:

```text
POSITION_PNL_PERCENTAGE > 2
AND
FALLING(RSI14, 2)
```

The position state must be supplied through `EvaluationContext.state`.

---

# 37. Stateful Exit Extensions

Add state-based expressions later:

```text
BARS_IN_POSITION
TIME_IN_POSITION
HIGH_SINCE_ENTRY
LOW_SINCE_ENTRY
MFE
MAE
DRAW_FROM_PEAK
```

These should be implemented as state operands, not as broker/execution code.

For backtest, the state comes from the backtest position context.

For paper/live, state comes from runtime session/position state.

---

# 38. Backtest Integration

Do not refactor the overall backtest loop.

Only replace the rule evaluation internals.

Existing flow remains:

```text
load data
 -> create evaluator
 -> calculate entry signals
 -> iterate timestamps
 -> intrabar SL/target checks
 -> evaluate exit rules
 -> evaluate entry rules
 -> execution service
```

The existing `entry_signals` dictionary can still be built from:

```python
executor.evaluate_entry_signals(df)
```

That function should internally use the new expression evaluator.

---

# 39. Backtest Vectorization Policy

Predicates should preferentially have a vectorized implementation.

Examples:

```text
ROLLING_MAX -> pandas rolling
Z_SCORE -> pandas rolling
RISING -> vectorized diff + rolling
TRUE_COUNT -> rolling sum
PERCENTILE_RANK -> vectorized/window implementation
```

Do not introduce a Python loop over every bar for predicates that can be vectorized.

Sequence predicates may require a controlled single pass because they are inherently stateful.

---

# 40. Live/Paper Evaluation Modes

Every registry entry should specify:

```text
evaluation_mode
```

Allowed values:

```text
VECTOR
STREAM
VECTOR_STREAM
STATEFUL
```

### VECTOR

Backtest/analytics only unless a full data window is already available.

### STREAM

Incremental evaluation suitable for live.

### VECTOR_STREAM

Must produce equivalent historical and incremental semantics.

### STATEFUL

Requires persistent state per strategy/instrument/node.

Do not allow a node marked VECTOR only to be deployed into a live strategy.

## 40.1 Evaluation Mode vs Evaluation Domain

`evaluation_mode` describes how a node is computationally evaluated:

```text
VECTOR
STREAM
VECTOR_STREAM
STATEFUL
```

It does **not** by itself define whether the node fires on candles or ticks.

Each executable expression/trigger must also declare:

```text
evaluation_domain:
    CANDLE
    TICK
    INTRABAR
    HYBRID
```

Recommended combinations:

```text
CANDLE   + VECTOR_STREAM
    -> candle-based conditions with equivalent historical/live semantics

TICK     + STREAM
    -> incremental LTP/tick conditions

HYBRID   + STATEFUL / VECTOR_STREAM + STREAM
    -> candle setup/anchor + tick trigger

INTRABAR + VECTOR
    -> OHLC-based historical approximation
```

Deployment validation must verify both dimensions.

A `STREAM` node is not automatically a tick trigger; the domain declaration is authoritative.

---

# 41. Live Runtime State

For stateful predicates, create a dedicated runtime state namespace, for example:

```text
strategy_rule_state:{strategy_id}:{instrument_id}
```

State should include only compact data required to continue evaluation.

Example:

```json
{
  "node_id": "seq_1",
  "sequence_step": 2,
  "last_event_timestamp": "2026-09-14T10:25:00+05:30"
}
```

Do not persist full dataframes in runtime state.

---

# 42. Execution Boundary

Rule predicates do not directly place orders.

The boundary must remain:

```text
Expression -> Signal -> StrategyExecutor -> Order Intent -> Execution Service -> Broker
```

Rule-only operands therefore require no execution-layer change.

---

# 43. Features That ARE Execution Features

These should not be implemented as predicates:

```text
LIMIT ENTRY
STOP ENTRY
STOP LIMIT ENTRY
TRAILING ENTRY
OCO
BRACKET
ICEBERG
TWAP
VWAP EXECUTION
```

These change order semantics and require changes to:

- order intent model
- backtest execution simulator
- paper execution simulator
- live execution service
- broker adapters
- order-state reconciliation

Treat them as a separate execution capability track.

---

# 44. New OrderIntent Abstraction for Future Execution Work

When non-market entry orders are implemented, introduce:

```python
@dataclass
class OrderIntent:
    side: str
    order_type: str
    quantity: int
    limit_price: float | None
    stop_price: float | None
    time_in_force: str | None
    reason: str
```

Then:

```text
Strategy Decision
   -> OrderIntent
   -> Backtest / Paper / Live execution adapter
```

Do not overload the predicate engine with this responsibility.

---

# 45. Session-Level Operand Implementation

For daily/week/month levels, use session boundaries derived from the configured strategy timezone.

Never use UTC date boundaries blindly for an Asia/Kolkata strategy.

For example:

```text
PREV_DAY_HIGH
```

must refer to the previous trading/session date in the strategy timezone, not merely the previous UTC calendar date.

The same principle applies to:

- opening range
- day high/low
- session statistics
- daily VWAP anchors

---

# 46. Data Availability Contract

Before exposing a new market-data operand in the UI, verify:

```text
BACKTEST DATA AVAILABLE?
PAPER DATA AVAILABLE?
LIVE DATA AVAILABLE?
HISTORICAL QUALITY?
TIMEZONE CORRECT?
TIMESTAMP GRANULARITY?
```

This is especially important for future options/microstructure operands such as:

```text
OPEN_INTEREST
CHANGE_IN_OI
IV
DELTA
GAMMA
THETA
VEGA
BID
ASK
SPREAD
DEPTH_IMBALANCE
```

Do not expose a rule that cannot be reproduced consistently across research and execution.

---

# 47. Option/Microstructure Extension

Future registry families:

```text
OPTIONS
MICROSTRUCTURE
FUNDAMENTAL
NEWS
MACRO
```

Examples:

```text
OPEN_INTEREST
OI_CHANGE
IV
DELTA
GAMMA
PUT_CALL_RATIO
BID
ASK
SPREAD_PERCENT
DEPTH_IMBALANCE
```

Each requires explicit data-source contracts and historical availability before enabling in backtests.

---

# 48. Security of Nested Expressions

Do not extend the existing `DataFrame.eval()` custom expression feature to expose arbitrary Python functions.

For expression nodes, use a whitelist registry.

Allowed:

```text
known operands
known transforms
known predicates
known comparisons
known logical operators
known parameters
```

Reject unknown node types.

Reject recursive structures that exceed a configurable maximum depth.

Recommended initial maximum expression depth:

```text
12
```

Recommended maximum children per logical node:

```text
32
```

These are configuration defaults, not hard requirements.

---

# 49. Validation Rules

Backend validation must reject:

```text
ROLLING_MAX(window <= 0)
RISING(bars <= 0)
TRUE_COUNT(window <= 0)
Z_SCORE(window <= 1)
UNKNOWN_NODE_TYPE
UNKNOWN_OPERAND
UNKNOWN_PREDICATE
BOOLEAN used as arithmetic without explicit conversion
SEQUENCE with zero steps
TIMEFRAME not supported by node
STATE operand in entry context unless explicitly supported
```

For stateful operands, the validation result should state why a mode is unsupported.

---

# 50. Test Strategy

Create tests at four levels.

## 50.1 Unit tests

For each predicate:

- normal values
- insufficient history
- NaN values
- flat values
- zero denominator
- first event
- missing event
- timeframe alignment

## 50.2 Expression tests

Examples:

```text
EMA20 > EMA50
CLOSE > ROLLING_MAX(HIGH, 20, previous_only)
TRUE_COUNT(CLOSE > EMA20, 5) >= 4
RISING(EMA20, 3)
Z_SCORE(CLOSE, 50) < -2
```

## 50.3 Regression tests

Every existing legacy rule type must return the same result as before.

## 50.4 Integration tests

Run the same strategy definition through:

```text
Backtest
Paper
Live-simulation/mock broker
```

and assert decision equivalence for identical candle streams.

---

# 51. Golden Test Fixtures

Create deterministic fixture data containing:

```text
- monotonically increasing prices
- monotonically decreasing prices
- alternating prices
- repeated equal values
- gaps
- volume spikes
- volatility shifts
- MTF timestamps
- missing candles
```

Expected outputs should be stored explicitly.

This is especially important for:

- cross
- rolling max/min
- bars since
- sequences
- multi-timeframe alignment

---

# 52. Look-Ahead Bias Tests

Every new temporal operator must have a specific no-lookahead test.

Example:

For:

```text
BREAKS_HIGH(HIGH, 20)
```

changing future candle values must not change the signal on the current candle.

For:

```text
Z_SCORE(CLOSE, 50)
```

future rows must not change current z-score.

For:

```text
OPENING_RANGE_HIGH(15m)
```

candles occurring after the opening range must not influence the level retrospectively for the earlier evaluation bars.

---

# 53. MTF Tests

Example:

```text
Base timeframe: 1m
Predicate timeframe: 15m
```

Test:

```text
RISING(EMA20@15m, 3)
```

must change only on new 15m source observations, then remain stable during their aligned 1m interval.

Test for:

- exact boundary
- first source bar
- source gaps
- timezone conversion
- incomplete current higher-timeframe bar

---

# 54. Sequence Tests

Example sequence:

```text
A
within 5 bars
B
within 3 bars
C
```

Test cases:

1. A/B/C all occur within limits -> true.
2. A occurs, B times out -> sequence resets.
3. A occurs twice before B -> verify restart policy.
4. B happens on boundary exactly N bars later -> define inclusive/exclusive semantics and test.
5. C occurs without A -> false.
6. Completed sequence must not retrigger on every later bar.

---

# 55. Performance Requirements

The new engine must not turn a 1-million-row backtest into a per-node/per-bar Python explosion.

Rules:

- Cache resolved operands.
- Cache identical transforms by normalized node hash.
- Reuse IndicatorEngine caches.
- Prefer vectorized NumPy/pandas operations.
- Use Numba only for genuinely hot loops.
- Avoid repeated DataFrame copies.
- Evaluate nested expressions once per unique node within a context.

Recommended cache key:

```python
hash(canonical_json(node))
```

combined with timeframe and instrument context.

---

# 56. Expression Canonicalization

Before caching, canonicalize JSON:

- sort dictionary keys
- remove non-semantic UI metadata
- normalize numeric types
- normalize timeframe aliases
- normalize parameter aliases

Equivalent expressions should generate the same cache key.

---

# 57. Explainability / Debug Output

QuantNest should eventually be able to show:

```text
Rule matched because:

CLOSE = 24850.20
EMA20 = 24810.31
RISING(EMA20, 3) = TRUE
RVOL20 = 2.14
TRUE_COUNT(CLOSE > EMA20, 5) = 4
```

For each expression node expose optional evaluation metadata:

```python
{
    "value": True,
    "node": "RISING",
    "inputs": {...},
    "timestamp": ...
}
```

Do not calculate expensive explainability details on every live bar by default.

Use debug mode or on-demand explanation.

---

# 58. Rule Preview Mode

Frontend should offer a preview for each condition:

```text
Last 20 bars

Condition result: TRUE

Current values:
CLOSE 24850.20
EMA20 24810.31
RVOL 2.14
```

This is valuable for catching configuration misunderstandings before deployment.

---

# 59. Recommended Current-Release Predicate Catalogue — Stock Only

## Release 1A — Core OHLCV transforms

Implement now:

```text
ROLLING_MAX
ROLLING_MIN
ROLLING_MEAN
ROLLING_SUM
ROLLING_STD

PERCENT_CHANGE
RELATIVE_VOLUME
Z_SCORE
PERCENTILE_RANK

TRUE_RANGE
CANDLE_RANGE
RANGE_PERCENT
ATR_PERCENT
```

## Release 1B — Core stock predicates

Implement now:

```text
RISING
FALLING
CONSECUTIVE
TRUE_COUNT

BARS_SINCE
WITHIN_BARS

AT_HIGHEST
AT_LOWEST
BREAKS_HIGH
BREAKS_LOW

NEW_HIGH
NEW_LOW
```

## Release 1C — Stock session levels

Implement now:

```text
DAY_HIGH
DAY_LOW
PREV_DAY_HIGH
PREV_DAY_LOW
PREV_DAY_CLOSE

WEEK_OPEN
WEEK_HIGH
WEEK_LOW

MONTH_OPEN
MONTH_HIGH
MONTH_LOW

OPENING_RANGE_HIGH
OPENING_RANGE_LOW
```

All are derived from stock OHLCV/session data.

## Release 1D — Stateful stock strategy logic

Implement now:

```text
EVENT
ANCHOR
STATE_REFERENCE
SEQUENCE
SETUP
TRIGGER
INVALIDATION
EXPIRY
```

This release specifically enables:

```text
signal-candle breakout
breakout retest
failed breakout
opening-range breakout
candle-pattern breakout
EMA crossover → pullback
dynamic SL/TP from setup candle
dynamic risk sizing from setup candle
multi-stage confirmation
```

## Deferred — advanced cross-asset statistics

Only add after the stock-first engine is stable and the required stock datasets are verified:

```text
SLOPE
ACCELERATION
CORRELATION
BETA
REGRESSION_SLOPE
CROSS_ASSET_SPREAD
```

These may be implemented using stock data but should remain secondary to the core stock rule language.

## Future F&O / microstructure release

Do not expose until the required data pipeline exists:

```text
OPEN_INTEREST
OI_CHANGE
IV
DELTA
GAMMA
THETA
VEGA
PUT_CALL_RATIO
BID
ASK
SPREAD
DEPTH_IMBALANCE
FUTURES_BASIS
```

# 60. Example Strategies Enabled by the New System

## Breakout

```text
CLOSE > ROLLING_MAX(HIGH, 20, previous_only)
AND
RISING(EMA20, 3)
AND
RELATIVE_VOLUME(20) > 1.5
```

## Momentum

```text
EMA20 > EMA50
AND
RISING(EMA20, 5)
AND
PERCENT_CHANGE(CLOSE, 10) > 2
```

## Mean reversion

```text
Z_SCORE(CLOSE, 50) < -2
AND
RSI14 < 30
AND
RISING(RSI14, 2)
```

## Volume confirmation

```text
BREAKS_HIGH(HIGH, 20)
AND
RELATIVE_VOLUME(20) > 2
```

## Persistent trend

```text
TRUE_COUNT(CLOSE > EMA20, 5) >= 4
```

## Event sequence

```text
RSI crosses below 30
-> within 5 bars
RSI crosses above 30
-> within 3 bars
CLOSE crosses above EMA20
```

---


## 60A. Required Stock Strategy Patterns

The implementation must be able to express these patterns without custom Python.

### 1. Signal candle breakout

```text
SETUP:
    CLOSE crosses above EMA20
    AND EMA20 > EMA50

CAPTURE:
    setup.high
    setup.low
    setup.range

TRIGGER:
    LTP crosses above setup.high

ACTION:
    BUY

SL:
    setup.low

TARGET:
    setup.high + 2 * setup.range
```

Semantics:

```text
SETUP / CAPTURE:
    completed-candle evaluation

TRIGGER:
    tick evaluation using LTP

SL / TARGET:
    price-level monitoring on every tick
```

A candle-close alternative remains valid:

```text
TRIGGER:
    CLOSE crosses above setup.high
```

but it is a different strategy semantic: it waits for candle confirmation rather than entering on the first live breakout tick.

### 2. Signal candle breakdown

```text
SETUP:
    CLOSE crosses below EMA20
    AND EMA20 < EMA50

CAPTURE:
    setup.high
    setup.low
    setup.range

TRIGGER:
    CLOSE crosses below setup.low

ACTION:
    SELL

SL:
    setup.high

TARGET:
    setup.low - 2 * setup.range
```

### 3. Breakout → retest

```text
SETUP:
    BREAKS_HIGH(HIGH, 20)

CAPTURE:
    breakout.level

TRIGGER:
    price retests breakout.level
    AND CLOSE > breakout.level

ACTION:
    BUY
```

### 4. Failed breakout

```text
SETUP:
    BREAKS_HIGH(HIGH, 20)

CAPTURE:
    breakout.level

TRIGGER:
    CLOSE < breakout.level

ACTION:
    SELL
```

### 5. Opening-range breakout

```text
CAPTURE:
    OPENING_RANGE_HIGH(15m)
    OPENING_RANGE_LOW(15m)

TRIGGER:
    CLOSE > opening_range_high

ACTION:
    BUY

SL:
    opening_range_low
```

### 6. EMA crossover → pullback

```text
SETUP:
    EMA20 crosses above EMA50

CAPTURE:
    setup.ema20

TRIGGER:
    price returns to setup.ema20
    AND RSI > 50

ACTION:
    BUY
```

### 7. Candle pattern → breakout

```text
SETUP:
    BULLISH_ENGULFING

CAPTURE:
    setup.high
    setup.low
    setup.range

TRIGGER:
    CLOSE > setup.high

ACTION:
    BUY

SL:
    setup.low

TARGET:
    setup.high + 2 * setup.range
```

### 8. Multi-stage RSI sequence

```text
RSI crosses below 30
    -> within 5 bars
RSI crosses above 30
    -> within 3 bars
CLOSE crosses above EMA20
    -> BUY
```

### 9. Dynamic ATR risk

```text
SETUP:
    EMA20 > EMA50

CAPTURE:
    setup.atr = ATR14

TRIGGER:
    CLOSE > previous 20-bar high

SL:
    entry_price - 1.5 * setup.atr

TARGET:
    entry_price + 3 * setup.atr
```

### 10. Time-limited setup

```text
SETUP:
    condition A

WAIT:
    maximum 10 bars

TRIGGER:
    condition B

EXPIRY:
    cancel if B does not occur in 10 bars
```


# 61. Profitability Research Rules

The purpose of the new builder is expressive strategy construction, not guaranteed profitability.

Every candidate strategy should be evaluated using:

```text
in-sample
out-of-sample
walk-forward
cost/slippage
parameter sensitivity
trade-count sufficiency
drawdown
expectancy
profit factor
Sharpe/Sortino
regime stability
```

Avoid adding dozens of predicates and optimizing them blindly. A more expressive builder increases the risk of overfitting as well as the ability to express useful ideas.

---

# 62. Deployment Validation

Before activation, compile the complete strategy expression graph and verify:

```text
All nodes valid
All operands supported
All timeframes available
Warmup computable
No stateful node unsupported in target mode
No missing market data dependencies
No execution capability mismatch
Expression depth within limit
Parameter ranges valid
```

Recommended API:

```text
POST /strategies/{id}/validate-runtime/
```

Response:

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "dependencies": {
    "timeframes": ["5m", "15m"],
    "lookback": {
      "5m": 250,
      "15m": 80
    },
    "stateful_nodes": []
  }
}
```

Activation should fail if there are hard validation errors.

---

# 63. File-by-File Implementation Plan

## Backend — new files

### `backend/rules_engine/registry.py`

Implement:

- operand descriptors
- transform descriptors
- predicate descriptors
- validation metadata
- mode support metadata

### `backend/rules_engine/expression_engine.py`

Implement:

- recursive node dispatch
- operand resolution
- transform evaluation
- predicate evaluation
- logical evaluation
- comparison evaluation
- sequence evaluation
- node caching

### `backend/rules_engine/expression_metadata.py`

Implement:

- output type analysis
- lookback analysis
- timeframe dependencies
- state requirements
- mode support

### `backend/rules_engine/predicates.py`

Implement first-release predicates.

### `backend/rules_engine/transforms.py`

Implement rolling/statistical transforms.

### `backend/rules_engine/sequence_engine.py`

Implement:

- ordered event evaluation
- setup/trigger/invalidation/expiry
- per-strategy/per-instrument sequence state
- restart policy
- exact boundary semantics

### `backend/rules_engine/anchor_store.py`

Implement:

- `create_anchor()`
- `get_anchor()`
- `replace_anchor()`
- `clear_anchor()`
- `invalidate_anchor()`
- `expire_anchor()`
- compact runtime serialization
- deterministic backtest state
- paper/live runtime adapters

### `backend/rules_engine/order_expression.py`

Implement resolution of:

- dynamic entry trigger levels
- dynamic stop loss
- dynamic target
- stop distance
- risk/share
- quantity expressions

This layer resolves values/intent inputs; it does not place broker orders.

### `backend/rules_engine/data_capabilities.py`

Implement:

- stock/OHLCV capability registry
- supported timeframes
- runtime-mode support
- deferred F&O capability flags
- data-quality requirements

### `backend/rules_engine/metadata_api.py

Optional DRF endpoint for frontend capability metadata.

## Backend — existing files

### `backend/rules_engine/models.py`

Add `Rule.expression` JSONField.

### `backend/rules_engine/serializers.py`

Add expression validation.

### `backend/rules_engine/evaluator.py`

Delegate expression rules to `ExpressionEngine` while preserving legacy path.

### `backend/rules_engine/metadata.py`

Delegate or extend warm-up calculation to expression metadata.

### `backend/rules_engine/views.py`

Add metadata/validation endpoints if used.

### `backend/strategy_engine/executor.py`

Minimal change only if additional context/state is required for the new evaluator.

Keep entry/exit orchestration unchanged.

### `backend/backtesting/engine.py`

Do not refactor the main simulation loop. Ensure the evaluator receives sufficient context for new expressions.

### `backend/strategy_engine/exit_actions.py`

No changes for rule-only predicates.

### `backend/risk_management/evaluator.py`

No changes for rule-only predicates.

## Frontend — new files

### `ExpressionBuilder.jsx`

Top-level recursive builder.

### `ExpressionNodeEditor.jsx`

Dispatches node-specific editors.

### `TransformNodeEditor.jsx`

Rolling/statistical configuration.

### `PredicateNodeEditor.jsx`

Temporal/trend/event predicates.

### `LogicalNodeEditor.jsx`

AND/OR/NOT composition.

### `SequenceBuilder.jsx`

Ordered event construction.

### `ExpressionPreview.jsx`

Readable rule text and optional evaluation preview.

## Frontend — existing files

### `EntryRulesBuilder.jsx`

Allow switching between legacy and expression rule mode.

### `ExitRulesBuilder.jsx`

Same integration for exit rules.

### `OperandSelector.jsx`

Keep for legacy and simple operand nodes; add support for metadata-driven operands.

### `MathExpressionBuilder.jsx`

Do not make this the new strategy language. Reuse it for arithmetic subexpressions where appropriate.

---

# 64. Implementation Order — Stock First, Then F&O

The implementation sequence is intentionally data-first.

## Step 1 — Protect existing strategy behavior

Add the optional `Rule.expression` field.

Do not remove or migrate the legacy operand fields yet.

## Step 2 — Create the capability registry

Create:

```text
OPERAND_REGISTRY
TRANSFORM_REGISTRY
PREDICATE_REGISTRY
DATA_CAPABILITY_REGISTRY
```

The registry must mark whether a feature is:

```text
CURRENT_STOCK
DEFERRED
FUTURE_FNO
```

Only `CURRENT_STOCK` appears in the production builder.

## Step 3 — Recursive expression engine

Implement:

```text
OPERAND
TRANSFORM
COMPARISON
LOGICAL
PREDICATE
```

with legacy-rule compatibility.

## Step 4 — Core stock transforms

Implement:

```text
ROLLING_MAX
ROLLING_MIN
ROLLING_MEAN
ROLLING_SUM
ROLLING_STD
PERCENT_CHANGE
RELATIVE_VOLUME
Z_SCORE
PERCENTILE_RANK
TRUE_RANGE
CANDLE_RANGE
RANGE_PERCENT
ATR_PERCENT
```

## Step 5 — Core stock predicates

Implement:

```text
RISING
FALLING
CONSECUTIVE
TRUE_COUNT
BARS_SINCE
WITHIN_BARS
AT_HIGHEST
AT_LOWEST
BREAKS_HIGH
BREAKS_LOW
NEW_HIGH
NEW_LOW
```

## Step 6 — Warm-up and data requirements

Make lookback analysis recursive.

Make sure every stock expression can report:

```text
required timeframe
required candles
minimum history
```

## Step 7 — Metadata-driven frontend

Replace duplicated hard-coded capability configuration gradually.

Build:

```text
ExpressionBuilder
ExpressionNodeEditor
OperandNodeEditor
TransformNodeEditor
PredicateNodeEditor
LogicalNodeEditor
ExpressionPreview
```

## Step 8 — Legacy regression

Confirm existing rule definitions produce the same:

```text
signals
entries
exits
backtest results
```

as before.

## Step 9 — Event/anchor engine

Implement:

```text
EVENT
ANCHOR
STATE_REFERENCE
```

with:

```text
capture values
setup lifecycle
expiry
invalidation
consumption
replacement policy
```

## Step 10 — Dynamic order expressions

Support:

```text
anchor.setup.high
anchor.setup.low
anchor.setup.range
anchor.setup.atr
```

for:

```text
entry trigger
stop loss
target
risk distance
position sizing
```

## Step 11 — Sequence engine

Implement:

```text
SETUP
→ WAIT
→ TRIGGER
→ ACTION
```

including:

```text
within N bars
expiry
invalidation
restart mode
```

## Step 12 — Mandatory signal-candle acceptance test

Implement and verify:

```text
CLOSE crosses above EMA20
AND EMA20 > EMA50

capture setup.high
capture setup.low
capture setup.range

wait up to N bars

LTP crosses above setup.high

BUY
SL = setup.low
TP = setup.high + 2 * setup.range
```

Required evaluation semantics:

```text
SETUP:
    completed candle

CAPTURE:
    completed candle

WAIT / EXPIRY:
    strategy state, counted in the selected strategy timeframe

TRIGGER:
    tick / LTP stream

SL:
    tick / intrabar price monitoring

TP:
    tick / intrabar price monitoring
```

Also verify the candle-close variant:

```text
TRIGGER:
    CLOSE crosses above setup.high
```

produces the intentionally different next-candle/close-confirmed behavior.

This becomes the canonical test of the new architecture for both candle-confirmed and true breakout semantics.

## Step 13 — Stock session levels

Implement:

```text
DAY_HIGH
DAY_LOW
PREV_DAY_HIGH
PREV_DAY_LOW
PREV_DAY_CLOSE
WEEK_OPEN
WEEK_HIGH
WEEK_LOW
MONTH_OPEN
MONTH_HIGH
MONTH_LOW
OPENING_RANGE_HIGH
OPENING_RANGE_LOW
```

## Step 14 — Paper/live equivalence

Use the same event/anchor semantics in:

```text
BACKTEST
PAPER
LIVE
```

and reject unsupported stateful/data capabilities at deployment.

## Step 15 — Deployment validation

Before activation:

```text
expression valid?
stock data available?
timeframe supported?
warm-up valid?
state supported?
execution capability supported?
```

## Step 16 — F&O only later

After a separate historical/live F&O pipeline exists, extend the same architecture with:

```text
FUTURES
OPTIONS
OPEN_INTEREST
IV
GREEKS
BID/ASK
DEPTH
```

Do not make the stock release depend on those capabilities.

# 64A. Tick/Candle Acceptance Matrix

The implementation must satisfy this matrix:

| Strategy component | Default evaluation |
|---|---|
| `CLOSE`, indicators, candle patterns | Completed candle |
| Candle-based setup/event | Completed candle |
| Anchor creation/capture | Event candle |
| `LTP crosses above/below level` | Every tick |
| Fixed price SL | Every tick / broker-native trigger |
| Fixed price target | Every tick / broker-native trigger |
| Trailing stop | Every tick for movement and hit detection |
| Candle-close exit predicate | Completed candle |
| Candle-derived dynamic level | Recalculate per completed candle unless explicitly configured otherwise |
| Tick trigger with only 1m OHLCV history | Approximation or reject; never silently tick-exact |

The same semantics must be preserved across:

```text
BACKTEST
PAPER
LIVE
```

subject to the available market-data resolution and the documented execution model.

---

# 65. Definition of Done — Release 1

Release 1 is complete only when all of the following are true:

### Builder

- User can create comparison expressions.
- User can create nested predicates.
- User can combine predicates with AND/OR.
- User can modify parameters without losing nested configuration.
- User can save and reload expressions exactly.

### Backend

- Expression JSON validated.
- Recursive evaluation works.
- Legacy rules still work.
- Warmup calculated correctly.
- MTF handled at source timeframe.
- No silent malformed-expression failures.

### Backtest

- Existing strategies remain unchanged.
- New predicates produce deterministic results.
- No look-ahead leakage.
- Entry/exit timing remains consistent.
- Tick-trigger strategies are never represented as tick-exact when only OHLCV history exists.
- Intrabar assumptions are explicit and testable.
- Static price SL/TP levels are monitored without waiting for candle close.

### Paper/live

- LTP/tick triggers can fire between candles.
- Candle-based conditions remain completed-candle driven.
- Tick-based SL/TP are monitored independently of candle-close rule evaluation.

- Vector/stream semantics match.
- Stateful nodes have runtime state.
- Unsupported nodes are rejected at deployment.

### Performance

- Indicator and node results are cached.
- No avoidable per-bar DataFrame copies.
- Large backtests remain practical.

---

# 66. Definition of Done — “Full Strategy Builder”

The stock-first builder can be considered complete when users can compose all of these classes without custom code:

```text
Stock OHLCV market data
Technical indicators derived from stock OHLCV
Rolling transforms
Statistical transforms
Price-action predicates
Trend predicates
Persistence predicates
Event predicates
Breakout/extremum predicates
Stock session levels
Position-state predicates
Event anchors
Dynamic setup-derived prices
Dynamic risk/SL/target expressions
Logical composition
Ordered event sequences
Multi-timeframe stock expressions
```

Execution order types remain a separate capability track.

---

# 67. Non-Goals

This implementation does not attempt to:

- guarantee profitable strategies
- redesign the finalized backtest engine
- replace the broker abstraction
- turn `MATH_EXPRESSION` into arbitrary Python
- expose unsupported data sources
- add every exotic indicator immediately
- implement execution algorithms as rule operands

---

# 68. Architectural Principle

The long-term QuantNest strategy language should follow:

```text
Small number of orthogonal primitives
        +
Recursive composition
        +
Strict type validation
        +
Explicit time/state semantics
        +
Shared historical/live evaluation
        =
Large strategy design space
```

The objective is not to create hundreds of one-off operands. The objective is to create enough composable primitives that a new strategy idea can usually be represented by composition rather than new backend code.

---

# 69. Recommended Final Capability Model

```text
                         QUANTNEST STRATEGY LANGUAGE

       ┌──────────────────────────────────────────────────┐
       │                 DATA OPERANDS                    │
       │ price • volume • indicators • position state     │
       └──────────────────────┬───────────────────────────┘
                              │
                              v
       ┌──────────────────────────────────────────────────┐
       │                TRANSFORMS                       │
       │ rolling • statistical • arithmetic • sessions    │
       └──────────────────────┬───────────────────────────┘
                              │
                              v
       ┌──────────────────────────────────────────────────┐
       │               PREDICATES                        │
       │ trend • breakout • persistence • events          │
       └──────────────────────┬───────────────────────────┘
                              │
                              v
       ┌──────────────────────────────────────────────────┐
       │             COMPARISON / LOGIC                  │
       │ GT • LT • CROSS • AND • OR • NOT                │
       └──────────────────────┬───────────────────────────┘
                              │
                              v
       ┌──────────────────────────────────────────────────┐
       │                 SEQUENCES                       │
       │ ordered events • time windows • state            │
       └──────────────────────┬───────────────────────────┘
                              │
                              v
                      STRATEGY SIGNAL
                              │
                              v
                     STRATEGY EXECUTOR
                              │
                 ┌────────────┼────────────┐
                 v            v            v
              BACKTEST      PAPER         LIVE
```

---

# 70. Final Implementation Recommendation

Implement the first release as a **recursive expression engine layered underneath the existing Rule/RuleGroup API**.

The most important engineering choices are:

1. Preserve the current binary rule model for backward compatibility.
2. Add an optional expression tree to `Rule`.
3. Create a central backend capability registry.
4. Return strongly typed Series from every expression node.
5. Evaluate MTF expressions at their native timeframe before alignment.
6. Attach explicit lookback/state/mode metadata to every node.
7. Keep rule evaluation separate from order execution.
8. Add sequence/state handling only where truly required.
9. Make malformed expressions fail validation instead of silently becoming false signals.
10. Build the frontend from backend metadata rather than maintaining a second hard-coded capability catalog.
11. Reuse the current StrategyExecutor, backtest loop, paper execution and live execution for rule-only predicate additions.
12. Treat LIMIT/STOP/OCO/etc. as a separate OrderIntent/execution project.

This architecture gives QuantNest a strategy builder that can express a very large class of systematic trading rules while remaining compatible with the current codebase and avoiding a growing collection of one-off operands.

---

## Repository-specific evidence used for this specification

Current repository evidence confirms that the candle model stores OHLCV fields and that canonical candle persistence is restricted to `1m` and `1D`, with higher supported timeframes derived from those data. This stock-data boundary is therefore intentional in this implementation plan.

The current branch was reviewed for the existing operand enum, rule model, serializer validation, frontend builder/operand selector, indicator engine, rule evaluator, warmup analyzer, strategy executor, and backtest decision/execution flow.

The current rule schema is two operands plus comparison; the evaluator resolves those operands and applies the comparison; the frontend hard-codes parameter metadata; the current warmup analyzer derives lookback from operands; and the backtest queues ordinary entry decisions for subsequent candle execution.


---

# Appendix D — Final Stock-First Capability Boundary

## Implement now

The current QuantNest rule builder should focus on rules derived from existing stock OHLCV data and existing strategy/position state:

```text
1. Price/candle conditions
2. Existing indicators
3. Rolling statistics
4. Volume statistics
5. Trend/persistence conditions
6. Breakout/extremum conditions
7. Statistical normalization
8. Session/day/week/month levels
9. Opening-range levels
10. Multi-timeframe stock logic
11. Event detection
12. Event anchors
13. Setup → wait → trigger sequences
14. Setup invalidation and expiry
15. Dynamic SL/target from captured stock values
16. Dynamic risk/position sizing from captured values
17. Position-state exits
```

## Do not implement now

```text
Options chain logic
Open interest logic
Options Greeks
Options IV
Futures-specific data
Futures basis
Bid/ask rules
Order-book rules
Depth imbalance
Tick microstructure
```

## Future scale-out principle

When QuantNest later adds reliable Futures/Options historical and live data, the same recursive expression/state architecture should be reused.

Only the capability/data layer needs to expand:

```text
STOCK
  ↓
FUTURES
  ↓
OPTIONS
  ↓
MICROSTRUCTURE
```

The rule-language core should not be redesigned for each asset class.
