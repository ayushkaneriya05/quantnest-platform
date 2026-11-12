---
title: Strategy Studio and Versions
description: Build conditions, formulas and captured setups; size trades, schedule entries and manage versions.
order: 4
---

## Start with one explicit idea

A strategy says what to trade, when to enter, how much to use and what closes its
position. It does not start running when you save it.

Public subscriptions currently cover the published NSE-stock workflow. The
contract-selection sections below explain controls available where derivative
functionality is enabled; they are not a promise that futures/options or customer
Live trading are included in a public plan. Check [current availability](/docs/billing/).

## Create and navigate a strategy

Open **My Strategies → New Strategy**. Enter a name and useful description, review
its classification and enable Paper trading when you intend to deploy it.
Strategy status and execution-session status are different: setting a strategy to
Active makes it eligible for deployment; it does not create a session.

| Main tab | Purpose |
| --- | --- |
| Details | Name, description, classification, tags and execution enablement |
| Studio | Markets & size, Conditions, Schedule and Review |
| Sharing | Private/Public visibility and the current configuration link |
| Versions | Saved snapshots, notes, changes and restore |

Studio's four steps edit one draft. Previous/Next changes the visible step, not
what is saved. **Validate** and **Save version** stay in the main header.

## Markets & size: fixed instruments

1. Choose **Add instrument → Fixed instrument / contract**.
2. Search by name or ticker. Use exchange, instrument-type or expiry filters when
   useful. Read the full displayed name, particularly for options.
3. Add the instrument and expand its row to change the signal instrument or size.
4. Use the same instrument for signals and trading unless your idea explicitly
   needs a different signal source.

A fixed contract retains its exact strike and expiry; it does not turn into the
next month's contract. Expired/archived instruments are for historical work and
cannot receive current normal orders. Indices may supply signals or chart data,
but cannot be traded directly.

### Signal source, traded source and position values

| Input | What it reads | Example |
| --- | --- | --- |
| Signal instrument | The row's chosen signal market | BANKNIFTY index Close |
| Traded contract | The instrument actually receiving the order | The selected call option's LTP |
| Position state | That row's owned traded position | The option's Entry Price |

Each market input has its own source selector. A selector on one side of a
comparison or inside one arithmetic child does not apply to the other children.
Constants need no instrument. Position values are labelled as the traded position
and need no market selector.

An indicator's **Source** parameter is a different choice: Close, Volume or a
supported indicator series. Its outer market selector chooses which instrument
provides that series.

## Automatic futures and options, where enabled

Choose **Add instrument → Automatic F&O selection**, select the underlying and
expand the row. Choose Future or Option; for options choose Call/Put, expiry and
strike selection. A preview shows the currently resolved contract, not a permanent
order instruction. Saving retains the selection policy.

| Expiry choice | Meaning |
| --- | --- |
| Nearest | First eligible listed expiry |
| Next | Listed eligible expiry immediately after Nearest |
| Specific expiry | Require the selected date rather than a nearby replacement |

**Include contracts expiring today** controls whether today's expiry participates.
Dates come from available contracts; the selector does not assume a fixed expiry
weekday.

ATM is the listed strike nearest the underlying price. An exact tie chooses the
lower strike. ITM/OTM distance counts listed strike steps, not rupees or points.

| Strike policy | Call | Put |
| --- | --- | --- |
| ATM | Nearest listed strike | Nearest listed strike |
| ITM N | N strikes below ATM | N strikes above ATM |
| OTM N | N strikes above ATM | N strikes below ATM |
| Specific | Require that exact strike | Require that exact strike |

Example only: with strikes 57,000, 57,100, 57,200, 57,300, 57,400, 57,500 and
57,600, an underlying at 57,320 has ATM 57,300. Call ITM 3 is 57,000; Put ITM 3 is
57,600. Read your actual available strike grid before using a distance.

An open position or pending order pins its contract. Underlying movement does
not move an exit to a different strike. After becoming fully flat, the next valid
entry can select another contract. An unavailable exact strike or missing required
data makes selection wait; it does not silently substitute another contract.
Rows trade independently; they are not an atomic multi-leg spread or automatic
rollover instruction.

## Direction and default size

Choose Buy for a long entry or Sell for a supported short entry. Exit rules use
the opposite side automatically. Stock shorts require the supported Intraday
strategy classification; selecting Sell does not add stock-borrowing capability.

| Method | Meaning |
| --- | --- |
| Fixed Units | Exact order units; derivatives still require whole lots |
| Fixed Lots | Number of lots multiplied once by the selected contract's lot size |
| Percentage of available capital | A budget calculated from currently usable funds, rounded down to an affordable whole-lot size |

For a lot size of 30, 1 Lot and 30 Units both mean 30 order units. **1 Unit is not
converted to 1 Lot.** Give different instruments a custom size when a shared
default is unsuitable. Automatic fixed contract sizing uses Lots.

Capital-based sizing uses currently available funds after commitments, rather
than the original deposit. If no whole lot fits, no entry is admitted. Its
percentage sizes an order; Paper deployment allocation remains a fixed rupee amount.

### Reward/risk basis

When using position R-multiples, **Reward/risk basis** defines a positive initial
distance in traded-contract price points. For example, entry 100.00 with distance
2.00 makes a favorable move of 4.00 equal to +2R. The distance is frozen for that
trade; later ATR changes do not rewrite it.

Use an explicit traded-contract basis for separate signal/traded markets or
complex stop rules. Defining the basis does not place a stop; configure a Stop
loss condition too. An unavailable or non-positive basis prevents entry.

## Conditions: actions and combinations

| Stage | Evaluated when | Action |
| --- | --- | --- |
| Entry | Flat, Running, ready and inside the entry window | Request an entry |
| Stop loss | A position is owned | Request a full exit, before other exit stages |
| Target | A position is owned and no Stop loss wins | Request a full exit |
| Exit | A position is owned and neither earlier exit stage wins | Request a full exit |

Inside a group choose **All conditions**, **Any condition**, **Not** or
**At least K**; use Nested group for mixed logic. Separately, choose AND/OR across
the enabled groups of that stage. A disabled group is kept in the editor but
does not participate. A stage with no active groups does not trigger by default.

Use the value selector for an input, its parameter control for periods/components,
and Default/Override for the candle timeframe. **Close Price** reads the latest
completed candle; **LTP** reads received live prices during running execution.
The forming chart candle is not the completed Close used by a rule.

Position state belongs only to an owned traded position and is unavailable in
Entry. It can support exits using entry price, P&L, R-multiples and other inputs
shown by the [live builder reference](/docs/reference/).

Missing history or a calculation that cannot be evaluated is unavailable, not a
numeric zero. NOT of an unavailable result stays unavailable.
Crosses Above/Below need consecutive known observations on opposite sides of
the boundary; remaining above is not a new cross.

### Choose an input for the question you are testing

| Question | Useful input family | What to check |
| --- | --- | --- |
| Where is the market relative to its recent trend? | Moving averages and trend indicators | Period, source, output component and completed timeframe |
| Has momentum changed? | RSI, MACD, ROC or other momentum inputs | Threshold/crossover meaning; each indicator has its own scale |
| How large are recent movements? | ATR, ranges, bands or rolling deviation | Price-point versus percentage units and window length |
| Is activity unusually high? | Volume and volume-based indicators | Selected session/timeframe and whether data is available |
| What is happening to my owned trade? | Entry price, position P&L and R-multiples | Traded-position scope, quantity/multiplier and initial risk basis |

An indicator name is not a complete rule: choose its parameters, output and a
comparison that expresses your idea. The reference lists the currently accepted
inputs and parameters; it is not a catalog of recommended trading signals.

## Arithmetic, rolling windows and formulas

Use **ƒx** to combine numeric children with Add, Subtract, Multiply, Divide,
Minimum, Maximum, Absolute value or Negate. Each child retains its own market
and timeframe. A comparison then evaluates the resulting number.

Rolling operations read a completed-candle series: Lag, highest, lowest, average,
sum, standard deviation, z-score and return over bars. A rolling window uses one
market and one timeframe. Live prices, current position state and captured values
cannot be placed inside it. Combine separate rolling results outside their windows
when comparing markets or timeframes.

- A 20-bar Rolling sum of Volume adds those 20 candle volumes.
- A 20-bar sum of EMA values adds historical EMA outputs; it does not set the EMA's period.
- The newest completed candle participates. To exclude it, wrap the result in
  **Lag by bars (1)**.
- Example: `Close > Lag 1(Rolling highest 20(High))` compares the newest completed
  Close with the preceding 20 completed highs.

Named formulas let you reuse a readable numeric calculation. References must
resolve and cannot form a cycle. For **Math Expression**, add variables in its
parameter editor, configure their operands/timeframes and use the displayed IDs.
For example, set `VAR_1 = EMA(9)` and `VAR_2 = EMA(21)`, then enter
`(VAR_1 - VAR_2) / VAR_2 * 100` for their percentage gap. `%` means modulo, not
percentage conversion; multiply/divide by 100 explicitly when that is your intent.

Text-expression variables inherit their parent's market source. Use ordinary
arithmetic-tree children for separately chosen Signal/Traded markets. The text
expression does not execute Python or arbitrary functions. Current names,
parameters and operators are in the [builder reference](/docs/reference/).

## Capture and confirmation

Use a simple Entry condition when it should allow entry whenever it is true.
Use **Capture & confirmation → Configure** when an occurrence must remember values
and wait for a later event.

1. **Arm when:** define the initial condition.
2. **Remember values:** name values to freeze, such as the arming candle's High and Low.
3. **Intermediate confirmations:** optionally require ordered later observations.
4. **Enter on a later observation:** define the final confirmation.
5. **Invalidate:** optionally abandon the occurrence when a condition is met.
6. **Expire:** choose the number and timeframe of new completed bars.

Arming and entry cannot happen on the same observation. At most one ordered step
advances on an observation. Invalidation/expiry take priority over confirmation;
a confirmation at the exact expiry boundary does not rescue the setup.

Example: a completed bar arms a setup and captures High 101.00 and Low 99.00.
A later LTP cross above 101.00 may confirm entry. Captures stay at 101.00/99.00
while the position is open; they do not follow each new candle.

### Re-entry after closing

| Entry design | What permits another entry once flat |
| --- | --- |
| Simple level, such as LTP > EMA | Another eligible advancing observation while still true can enter |
| Crosses Above/Below | A new qualifying cross is required |
| Capture & confirmation | A new observed false → true Arm occurrence, followed by its later confirmations |

The first eligible known true Arm can arm an initially idle setup. After a filled
occurrence, an Arm that stayed true throughout the trade does not re-arm merely
because the position closed. An unknown value does not count as an observed false.
Pausing or losing the required observation sequence resets unfilled setup state;
captured values protecting an existing position are retained.

## Schedule

Set the default candle timeframe, schedule timezone, trading weekdays, optional
Entry start/end and excluded entry windows. Candle inputs can override Default;
LTP and position state do not become candle inputs by choosing a timeframe.

- All exchange trading days adds no custom weekday filter. Selected weekdays
  requires a non-empty selection and cannot open a closed exchange session.
- Times are interpreted in the selected timezone. Changing timezone keeps the
  entered clock text; it does not convert it to the same instant automatically.
- Entry bounds and exclusion boundaries include their exact times. Windows
  cannot wrap midnight, and the exchange/segment calendar must also be open.
- **Entry end stops new entries. It does not square off a position.** Stop loss,
  Target and Exit remain responsible for it. Intraday classification does not
  change this rule, and there is no general timed-exit operand in current Studio.

For example, an entry window ending at 15:10:00 does not close an existing position
at 15:10:01. Use the deployment's explicit stop/close controls when needed.

## Validate, save and review versions

Review the selected instruments, signal bindings, conditions, schedule and sizing.
Validation checks the definition and its history requirements; it does not place
orders or guarantee data availability, sufficient capital or a profitable result.

Save version stores the whole Studio document and an immutable snapshot. Moving
between steps or validating alone does not save. A saved version does not silently
replace a running deployment. Use its explicit **Version** action and wait for
the applied version, as described in [Paper](/docs/paper/).

In Versions, read the date, note and changes before restoring. Restore changes
the saved configuration; it is not an instruction to switch running sessions.
Snapshots and optional version auto-save do not preserve unsaved browser edits.

Leaving an unsaved Studio shows a confirmation. In-app navigation uses QuantNest's
dialog; reload/tab-close uses the browser's own warning. Neither saves automatically.
If another tab saved a newer revision, preserve the edits you need and reload
before reapplying them; a conflict protects the newer save from being overwritten.

## Clone, share, archive and delete

Use Clone on an owned strategy to start a separate editable strategy. It copies
the configuration rather than the original account's positions, orders or results.
The copy starts as a Private Draft with its own initial snapshot and uses
saved-strategy capacity. It does not copy the complete old version timeline.
Review its identity and rules before testing or deploying it. Restore changes
the original saved strategy instead.

Private visibility keeps the strategy accessible only to you. Public visibility
enables a read-only link to the current saved configuration. It does not share
private account/execution records, grant editing or authorize someone else's trading.
Return to Private to stop new access; material already viewed cannot be recalled.

Manage active sessions before disabling, archiving or deleting their strategy.
Related execution/backtest records can prevent deletion. Archive retains a
strategy; unarchive returns it to Draft. Archived but undeleted strategies still
count towards saved-strategy capacity.

## A first stock example

For learning the editor, use one supported stock, Buy direction and a small fixed
Units size. On one timeframe, define Entry as `Close > EMA(20)` AND `RSI(14) > 50`.
Define Stop loss as `Traded LTP < Entry Price - 2` and Target as
`Traded LTP > Entry Price + 4`. The example numbers are arbitrary price points,
not a recommendation or a promise that they suit that stock.

This is a level-entry example: it may re-enter after a full exit if Entry remains
true on another eligible observation. Use a crossover or captured setup if that
is not your intended behavior. Backtest it with [costs](/docs/charges/) before
[Paper practice](/docs/paper/).
