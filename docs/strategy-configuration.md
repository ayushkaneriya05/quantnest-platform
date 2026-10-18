# Strategy configuration and version lifecycle

**Source review: 16 October 2026.** This guide describes the implemented builder.
For execution scheduling and fill behavior, use the [technical reference](execution-technical-reference.md).
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
| SpecialEventFilter | Configured event restrictions and custom avoided dates |
| RuleGroup / Rule | Ordered active groups and typed operand comparisons |
| PositionSizingRule | Fixed quantity or percentage of available capital |
| StrategyAutoDisable | Performance-triggered entry pause and optional cooldown recovery |
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
4. Configure exit, stop-loss and target groups/actions.
5. Set sizing, schedule, event restrictions and optional auto-disable rules.
6. Save a version with useful notes; inspect its complete snapshot/differences.
7. Run a backtest with a saved/effective configuration.
8. Activate a deployable strategy and select a version for Paper or qualified Live.
9. Change a deployment through its supported version/allocation action.
10. Review the recorded order's version when investigating a result.

Editing a builder configuration does not silently rewrite the version already
deployed to an allocation. Historical results retain their effective configuration.

## 3. Rules and operands

A Rule compares **Operand A → comparison → Operand B**. Each operand has a type,
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

The arithmetic validator permits numeric constants, declared names, parentheses,
unary signs and +, -, *, /, %. Function calls, attributes, indexing and arbitrary
Python execution are outside this contract. Variables resolve through typed
operands; this is not an expression-node graph or a general scripting language.

See [RuleEvaluator](../backend/rules_engine/evaluator.py),
[math validation](../backend/rules_engine/math_expressions.py) and
[operand metadata](../backend/common/enums.py) for exact supported parameters.

## 4. Timeframes, warmup and event context

Supported frames are 1m, 3m, 5m, 15m, 30m, 1H, 4H, 1D and 1W.
A rule operand can override the base TimeRule frame.

The requirement analyzer walks the configuration to determine required history
and indicator lookback. Runtime preparation builds completed frames; higher-frame
values must not become visible before their close. Intraday alignment uses the
exchange session; weekly aggregation has its own calendar boundary.

Schedule checks use configured weekdays, allowed time window, excluded windows and
timezone together with market/calendar state. Event filters depend on the event
data actually available; a selected flag does not establish complete news coverage.

An indicator strategy waits for completed analytical bars. Static protection may
use current observed prices. The browser's forming chart candle is not the
authoritative analytical frame.

## 5. Instruments, routes and sizing

Current strategy execution supports NSE stocks and DIRECT routes. Other contract
enums or catalog Coming soon labels do not activate futures/options/crypto.

A route uses the strategy sizing rule unless its explicit override is enabled.

| Method | Calculation |
| --- | --- |
| Fixed Quantity | Positive configured units, rounded down to valid whole lots |
| Capital Based | Available capital × configured percentage / reference price, rounded down to whole units/lots |

A zero quantity rejects an entry. Capital reservations are checked again during
financial admission, so an earlier calculated quantity is not permission to exceed
the account/allocation's current funds.

Risk Based sizing and its field are removed. Stop-loss/target configuration remains.
The shared quantity evaluator is [RiskEvaluator](../backend/risk_management/evaluator.py),
called through [compute_position_size](../backend/strategy_engine/sizing.py).
Its use of lot rounding is a foundation, not proof of derivatives support.

## 6. Exit actions and parity boundaries

Exit groups can request a full exit, a partial percentage exit or moving protection
to breakeven. Shared action handling orders full exits before partial/breakeven
actions and records markers for applicable one-position actions.

Paper and Live request opposite-side MARKET execution; an exit cannot create extra
exposure beyond owned quantity. Backtesting models next-open orders plus OHLC
protection, including its stop-first convention when both levels are touched.

Fast price-based protection and complete group evaluation are different paths.
Complex stop/target groups and protection during unresolved partial Live fills
remain explicit verification areas in the technical reference. Do not promise
identical fill outcomes across all three drivers.

## 7. Versions, notes, differences and rollback

Snapshot serialization includes strategy details/tags, all configuration records,
ordered rule groups/rules, instruments/routes, sizing and auto-disable definitions.
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

## 8. Deployment and lifecycle validation

Deployment validates ownership, runtime scope, feature/plan admission, selected
version, instruments/routes, allocation and financial requirements.

A deployable strategy must be ACTIVE, have the relevant Paper/Live flag enabled,
contain instruments and nonempty active entry rules, and have sizing configured.
Live also requires an active stop-loss rule. The scope, licence, broker and data
requirements are additional gates.

Changing strategy status is restricted while Paper/Live sessions are RUNNING,
PAUSED, STOPPING or ERROR. Use halt/archive and stop workflows deliberately.
Strategies with execution/backtest history cannot be deleted as unused drafts;
archive them to retain related records.

Changing a deployed version uses the allocation/session APIs, updates runtime
assignments and publishes lifecycle work. A queued decision carries its original
version; financial admission rejects a stale version. Broker fills retain the
order's saved strategy/session/allocation/version.

## 9. Auto-disable configuration

The execution configuration contains `auto_disable_rules`. Backtests use their
effective saved configuration; Paper/Live use the allocation's deployed version.
Tick evaluation does not query StrategyAutoDisable rows.

| Trigger | Compared metric |
| --- | --- |
| Consecutive losses / wins | Closed-trade streak against a positive count |
| Daily / weekly / monthly loss | Negative realized period P&L as a percentage of supplied capital |
| Win-rate drop | Closed-trade win percentage at/below the threshold; requires completed trades |
| Drawdown | Realized-equity drawdown at/above the threshold |

Inactive rules do not match. Any matching rule can block entries. All matching
rules must allow automatic reenabling for automatic recovery; the longest matched
cooldown applies.

The shared metrics normalize daily/weekly/monthly periods using the deployed
timezone. Drawdown follows peak realized equity, excluding open-position unrealized
P&L. Recovery replays recorded closes in timestamp/ID order.

Paper/Live close outcomes record deduplicated risk publication work. Background
projection updates restore incomplete/out-of-order metrics and persist a matched
risk pause. Entries wait when required inputs are not ready.

The pause stores matched rules, version and cooldown state. The five-minute
reenable job resumes only eligible recorded risk pauses. Manual and data-gap pauses
are distinct. Resume records a close-count acknowledgement so unchanged old
results do not immediately retrigger the same pause. Version changes invalidate
the acknowledgement/projection as required.

Auto-disable restricts entries. Existing position protection, reductions and
reconciliation continue through their own execution paths.

## 10. Sharing

The owner sets visibility Public and copies `/strategy/view/<id>`.
The anonymous backend route is `/api/v1/strategies/shared/<id>/`.

The share view exposes current configuration, not account balances, private
execution history, P&L, editing, cloning or backtest actions. Visibility Private
makes subsequent public reads unavailable. Previously viewed/copied content
cannot be recalled. Responses are not cached.

Sharing is not version-pinned unless the API explicitly adds that feature later.
There are no marketplace cloning/backtesting permissions or user invitation flow.
Owners can still clone/backtest their own strategies.

## 11. Developer navigation and change procedure

| Concern | Source |
| --- | --- |
| API ownership/actions | [strategies/views.py](../backend/strategies/views.py), [serializers.py](../backend/strategies/serializers.py) |
| Defaults and checkpoints | [signals.py](../backend/strategies/signals.py) |
| Snapshot/restore/deployment | [services.py](../backend/strategies/services.py) |
| Anonymous projection | [public_views.py](../backend/strategies/public_views.py) |
| Timeframe requirements | [configuration.py](../backend/trading_domain/configuration.py), [metadata.py](../backend/rules_engine/metadata.py) |
| Shared rule/action program | [strategy.py](../backend/trading_domain/strategy.py), [exit_actions.py](../backend/trading_domain/exit_actions.py) |
| Auto-disable | [policy.py](../backend/risk_management/policy.py), [auto_disable.py](../backend/risk_management/auto_disable.py), [tasks.py](../backend/risk_management/tasks.py) |
| Builder/version UI | [strategy feature](../frontend/src/features/strategies), [configuration viewer](../frontend/src/shared/components/StrategyConfiguration.jsx) |

When adding an operand or field, update validation, backend metadata, serialization,
restore, requirement analysis, evaluation, research draft schema and presentation
together. Restart long-running processes after deploying changed Python definitions.
Use normal migrations for schema changes; follow the mode upgrade guide.
