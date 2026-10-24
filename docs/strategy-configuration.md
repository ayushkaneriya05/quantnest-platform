# Strategy configuration and version lifecycle

**Source review: 23 October 2026.** This guide describes the implemented builder.
Execution and operation are documented separately in [Backtesting](backtesting.md),
[Paper trading](paper-trading.md), [Live trading](live-trading.md) and [Terminal](trading-terminal.md).
For plan limits and feature availability, use [Commercial operations](commercial-operations.md).

For the future expression/setup/sequence builder, use the separate
[Strategy builder plan](strategy-builder-plan.md). It is a deferred design, not
the current rule schema described here.

## 1. Configuration ownership

A Strategy belongs to one user. Its editable relational configuration becomes a
complete JSON snapshot when a StrategyVersion is saved.

| Record | Responsibility |
| --- | --- |
| Strategy | Name, classification, owner, status, visibility, tags and execution flags |
| EntryOrderConfig | Direction, entry-group combination and entry restrictions |
| ExitOrderConfig | Exit configuration |
| TimeRule | Weekdays, session/time window, excluded windows, base timeframe and timezone |
| RuleGroup / Rule | Ordered active groups and typed operand comparisons |
| PositionSizingRule | Fixed quantity or percentage of available capital |
| WatchlistInstrument / ExecutionRoute | Signal instruments, execution routing and optional sizing override |
| StrategyVersion | Version number, full configuration, author, timestamp and notes |

Creating a strategy creates its one-to-one configuration records through signals
and schedules an initial checkpoint. Users do not create these defaults in Admin.
Version numbers are unique within the strategy.

The builder uses backend enums and operand metadata from
`GET /api/v1/common/enums/`. Frontend labels/default choices should reuse that
contract rather than a second JSON definition.

## 2. Customer workflow

1. Create a strategy and select its supported market/instrument classification.
2. Add the stocks used for signals and their execution routes.
3. Configure entry rules and the entry direction.
4. Configure exit, stop-loss and target groups. Each matched exit closes the full position.
5. Set position sizing, trading days, session hours and no-trade windows.
6. Save a version with useful notes; inspect its complete snapshot/differences.
7. Run a backtest with a saved/effective configuration.
8. Activate a deployable strategy and select a version for Paper or qualified Live.
9. Change a deployment through its supported version/allocation action.
10. Review the recorded order's version when investigating a result.

Editing a builder configuration does not silently rewrite the version already
deployed to an allocation. Historical results retain their effective configuration.

## 3. Rules and operands

A Rule compares **Operand A â†’ comparison â†’ Operand B**. Each operand has a type,
parameter object and optional timeframe override.

Groups are ENTRY, EXIT, STOP_LOSS or TARGET. Active rules combine with the group's
AND/OR operator. Entry groups use the entry configuration's group operator.
Priority determines group ordering; inactive groups/rules do not participate.

| Operand family | Examples | Configuration implications |
| --- | --- | --- |
| Prices/volume | OPEN, HIGH, LOW, CLOSE, VOLUME, LTP, HL2, HLC3, OHLC4 | Frame, source and shift affect the observed series |
| Session/history values | Current day open, previous week high/low | Depend on available calendar-aligned history |
| Indicators | SMA/EMA, RSI, MACD, ATR, bands, SuperTrend and others in metadata | Period/source/component requirements determine warmup |
| Candle analysis | Pattern, candle body size | Numeric or pattern parameters must follow metadata |
| Position state | Entry price, P&L points/percent, trailing offset, reward/risk | Meaningful only with the appropriate position context |
| Constant | Numeric value | Does not itself require historical bars |
| Arithmetic | MATH_EXPRESSION with configured variables | Restricted arithmetic; not arbitrary Python |

Candle body percentage is `abs(close - open) / (high - low) * 100`; a zero-range
candle resolves to zero. It is not a percentage of the opening price.

A positive shift selects previous bars in that operand's frame. Crosses compare
the previous/current values and are distinct from an ordinary greater/less check.
Missing warmup values are not valid signal evidence.

`LTP` reads a live provider observation; `CLOSE` reads a completed candle. LTP has no candle shift. Candle backtests approximate tick operands using their disclosed OHLC replay path. Existing saved LTP rules now use live ticks.

Position operands are rejected in entry rules, including Entry Price and Trailing
Peak Offset. They have no candle-history shift: the runtime stores current
position state rather than a historical position series. P&L points/percent use
the position side, and reward/risk divides those points by its configured stop
distance. Trailing offset measures distance from the favorable peak for that side.

Indicator sources support one configured source indicator. Its displayed
parameters are validated; recursively nested sources and source shifts are not
part of the editor contract. SMA and EMA tolerate the source indicator's initial
missing values and become valid after their own warmup.

Current Day Open groups candles by exchange trading session. Previous Week
High/Low use the previous Monday-to-Sunday calendar week, never a partially
completed current week. VWAP resets by the configured exchange session, week or
month. Overnight sessions retain their opening trading date.

Ichimoku Tenkan/Kijun use trailing ranges. Senkou A/B include their positive Kijun
displacement. The historical-close option uses `close.shift(kijun)`; the original
backward chart-plotting shift would read future prices in a historical rule and
is not used. This option is explicitly labelled as a historical close in the UI.

The arithmetic validator permits numeric constants, declared names, parentheses,
unary signs and +, -, *, /, %. Function calls, attributes, indexing and arbitrary
Python execution are outside this contract. Variables resolve through typed
operands; this is not an expression-node graph or a general scripting language.

See [shared evaluator](../backend/execution/engine.py),
[math validation](../backend/rules_engine/serializers.py) and
[operand metadata](../backend/common/enums.py) for exact supported parameters.

## 4. Timeframes, warmup and trading schedules

Supported frames are 1m, 3m, 5m, 15m, 30m, 1H, 4H, 1D and 1W.
A rule operand can override the base TimeRule frame.

The requirement analyzer walks the configuration to determine required history
and indicator lookback. Runtime preparation builds completed frames; higher-frame
values must not become visible before their close. Intraday alignment uses the
exchange session; weekly aggregation has its own calendar boundary.

The same requirements feed live preparation, workload pricing, backtests and
research. They include active groups/rules, operand shifts, a preceding crossing
value, both source and outer-indicator warmup, and math variables' timeframes.
Session Open, previous-week and VWAP operands also retain complete anchor windows
using the instrument's calendar session length. Inactive groups do not enlarge
the window. A math variable without its own timeframe inherits the containing
operand's timeframe.

Minute-derived frames use one shared `1m` source; daily/weekly frames use a separate
`1D` source. The largest requirement wins when several sessions need the same
symbol. The feed acquires missing provider history, reads confirmed rows, and
publishes OHLCV/time arrays before marking that requirement ready. An existing
buffer is not automatically resized: follow the [Paper runtime operations guide](paper-trading.md#runtime-operations-and-scaling) if a larger rule
window exceeds its capacity. History preparation does not manufacture observed ticks.
Insufficient actual source rows leave the symbol unready and report the available
and required counts; an acquisition-coverage record alone cannot mark it ready.

Schedule checks use configured weekdays, allowed time window, excluded windows and
timezone together with the instrument's exchange/segment calendar and holidays.

Weekdays use the backend `TradingDay` values (`Monday` through `Sunday`). The time
rule serializer writes that spelling, and runtime prepares the same values once
when loading a saved version. Indicator source parameters are normalized to their
uppercase enum values before validation and caching, including sources in saved
versions such as `close`. These conversions do not change saved version contents.

Invalid rule calculations raise an error. Paper/Live execution pauses new entries,
records the actual reason in the session's `error_message`, and sends a notification.
Local tick protection continues for open positions. Review the configuration and
resume the session after correcting the cause. A valid rule that evaluates to
false remains an ordinary no-signal result.

For every strategy type, **end time is an entry-window boundary only**. Entry
checks reject times later than the configured end; the exact end timestamp remains
inside the window, matching the original schedule logic. Open positions continue
through their configured stop-loss, target and exit rules. Reaching end time or
observing a position on a later day does not create a close request. Explicit
session-stop actions can still request position closure.

New builder settings default to **15:30 Asia/Kolkata**. End time is optional,
including for Intraday Live deployment; normal start/end ordering validation still
applies when both values are provided. The forward migration restores the default
and field description without rewriting saved settings or version snapshots.
NSE cash-stock short entries are admitted only for Intraday strategies; delivery
stock borrowing is not part of the implemented execution path.

An indicator strategy waits for completed analytical bars. Static protection may
use current observed prices. The browser's forming chart candle is not the
authoritative analytical frame.

## 5. Instruments, routes and sizing

Current snapshot validation supports DIRECT routes to selected active, tradable
catalogue instruments. It rejects indices, mutual funds and underlying references.
Contract metadata, history, live observations and broker support remain required;
a catalogue enum or Coming soon label does not establish end-to-end market support.

A route uses the strategy sizing rule unless its explicit override is enabled.
Each selected instrument has at most one Direct sizing override. The editor does
not offer Manual, Futures or Options routes while those paths are unsupported.
Strategy entry orders are MARKET orders; Terminal retains its separate order types.

| Method | Calculation |
| --- | --- |
| Fixed Quantity | Positive configured units, rounded down to valid whole lots |
| Capital Based | Available capital Ã— configured percentage / (reference price Ã— quantity multiplier), rounded down to whole units/lots |

A zero quantity rejects an entry. Capital reservations are checked again during
financial admission, so an earlier calculated quantity is not permission to exceed
the account/allocation's current funds.

Risk Based sizing and its field are removed. Stop-loss/target configuration remains.
The shared quantity function is [`calculate_quantity`](../backend/rules_engine/utils.py),
used by shared ledger sizing with the same flat sizing block,
reference price, available capital, lot size and quantity multiplier.
Its use of lot rounding is a foundation, not proof of derivatives support.

For the numerical sizing, contract validation and financial admission paths, see
[Backtesting](backtesting.md#sizing-capital-and-charges),
[Paper](paper-trading.md#from-a-tick-to-a-completed-trade) and
[Live](live-trading.md#admission-allocations-and-funds).

## 6. Exit configuration

Automated strategy exits request the full current position. There are no
fractional exit actions, trade-cooldown timer or performance auto-disable settings.
Configure active STOP_LOSS, TARGET and EXIT groups in the builder; Live snapshot
validation requires an active stop-loss group with a usable rule.

End time restricts new entries. It does not force an intraday square-off.
Simulation fill timing and end-of-test closure are described in [Backtesting](backtesting.md#replay-orders-and-fills).
Session stopping and position management belong to the [Paper](paper-trading.md#managing-a-running-session)
and [Live](live-trading.md#session-management) guides.

## 7. Versions, notes, differences and rollback

Paper allocations and Live sessions use one
[version-change dialog](../frontend/src/features/strategies/components/ChangeStrategyVersionDialog.jsx).
Each caller supplies its strategy/version fields and its own allocation update
action. The dialog submits an integer version ID. The shared version selector
loads searchable options and selected metadata; the dialog does not fetch the
entire version list separately. Backend ownership, allowance and open-exposure
validation still runs on the version-change action.

Snapshot serialization includes strategy details/tags, all configuration records,
ordered rule groups/rules, instruments/routes, sizing and schedules.
Database IDs/timestamps of nested configuration records are excluded where they
would create meaningless version differences.

Automatic versioning schedules a checkpoint after commit. It compares the final
serialized state with the latest snapshot and skips identical state; there is no
time debounce. Multiple changes in one transaction can therefore produce one
distinct final checkpoint. Snapshot creation locks the strategy before allocating
the next number.

Version history compares a selected version with the preceding saved version.
The UI groups readable before/after changes by section and keeps raw snapshot
inspection optional. A comparison is between saved configurations, not a record
of unsaved field edits.

The strategy-specific `StrategyVersionSelect` presents version number, timestamp
and notes consistently across consumers. Long notes use the common tooltip behavior;
the generic Select contains no strategy-specific formatting.

Rollback restores the chosen configuration in a transaction, recreates nested rules
and routes as needed, and records a new version noting the rollback. It replaces
the current builder configuration; it does not erase previous versions, rewrite
past fills or automatically switch a running allocation.

## 8. From configuration to execution

The builder owns editable rules, settings and saved versions. Execution uses the
selected immutable snapshot. Editing a draft does not change a deployed version.

Use the mode guide for validation, deployment, worker application and management:

- [Backtesting](backtesting.md): historical admission, replay and reports.
- [Paper trading](paper-trading.md): wallet, distinct-version deployments and simulated fills.
- [Live trading](live-trading.md): broker-account deployments, order submission and reconciliation.
- [Trading Terminal](trading-terminal.md): manual orders without a strategy.

Changing strategy status is restricted while Paper/Live deployments are RUNNING,
PAUSED, STOPPING or ERROR. Stop/manage them before changing lifecycle status.
Strategies with retained execution/backtest history should be archived rather than
treated as disposable drafts. `StrategyDeploymentService.validate_strategy_lifecycle()`
implements this boundary.

## 9. Sharing

The owner sets visibility Public and copies `/strategy/view/<id>`.
The anonymous backend route is `/api/v1/strategies/shared/<id>/`.

The share view exposes current configuration, not account balances, private
execution history, P&L, editing, cloning or backtest actions. Visibility Private
makes subsequent public reads unavailable. Previously viewed/copied content
cannot be recalled. Responses are not cached.

Sharing is not version-pinned unless the API explicitly adds that feature later.
There are no marketplace cloning/backtesting permissions or user invitation flow.
Owners can still clone/backtest their own strategies.

## 10. Developer navigation and change procedure

| Concern | Source |
| --- | --- |
| API ownership/actions | [strategies/views.py](../backend/strategies/views.py), [serializers.py](../backend/strategies/serializers.py) |
| Defaults and checkpoints | [signals.py](../backend/strategies/signals.py) |
| Snapshot/restore/deployment | [services.py](../backend/strategies/services.py) |
| Anonymous projection | [public_views.py](../backend/strategies/public_views.py) |
| Timeframe requirements | [compiler.py](../backend/execution/compiler.py) |
| Shared rule program | [engine.py](../backend/execution/engine.py) |
| Position sizing | [models.py](../backend/rules_engine/models.py), [serializers.py](../backend/rules_engine/serializers.py), [utils.py](../backend/rules_engine/utils.py) |
| Builder/version UI | [strategy feature](../frontend/src/features/strategies), [configuration viewer](../frontend/src/shared/components/StrategyConfiguration.jsx) |

When adding an operand or field, update validation, backend metadata, serialization,
restore, requirement analysis, evaluation, research draft schema and presentation
together. Restart long-running processes after deploying changed Python definitions.
Use normal migrations for schema changes; follow the mode upgrade guide.
