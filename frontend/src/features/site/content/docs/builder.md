---
title: Strategy Studio and Versions
description: Markets, composable conditions, sizing, saved versions and sharing.
order: 4
---
## Make your idea explicit

- Open Studio and choose the exact instruments or contracts to trade in **Markets & size**.
- Use **Add instrument** to choose a fixed contract or an automatic F&O policy. Expand a selected row to edit its signal mapping, contract settings or custom size.
- Each traded contract can use a separate signal instrument. For example, NIFTY 50 can generate a signal for a selected call option. An index generates signals; it cannot receive orders.
- In **Conditions**, define entry, stop-loss, target and exit groups. Combine comparisons with All, Any, Not or At least K conditions, including nested groups.
- Select the signal or traded-contract source and timeframe for each market input. CLOSE uses completed candles; LTP uses received ticks. Position values always belong to the traded contract.

## Reuse calculations and remember a setup

- Reusable formulas can combine supported indicators, prices and arithmetic, and reference other formulas. Use a name that explains the calculation.
- Candle windows include lag, highest, lowest, average, sum, standard deviation, z-score and percentage return. A window uses one source and timeframe; compare separate windows to combine markets or timeframes.
- **Rolling sum** adds the input value across the chosen number of completed candles. For example, a 20-bar sum of 15-minute Volume is the total volume for those 20 candles. A sum of EMA outputs adds historical EMA values; it does not change the EMA period.
- Entry price, position P&L, LTP and captured values cannot be used inside a rolling window. Combine current position values with the completed rolling result outside that window instead.
- For a breakout above the preceding 20 highs, compare CLOSE with `Lag 1(Rolling highest 20(HIGH))`. Without the lag, the newest completed high participates in the maximum.
- Enable **capture & confirmation** to arm a setup, remember values such as a signal candle's high/low, wait for ordered confirmations, and define invalidation or expiry in completed bars.
- A setup cannot arm and enter on the same observation. Remembered values remain available to exit conditions while its position is open.

## Configure sizing and safeguards

- Choose fixed Units, fixed Lots or capital-based sizing. Lots convert using each contract's lot size; fixed units that are not whole lots are rejected.
- Expand the instrument's settings and enable **Use custom size** to override the default for one traded contract. Capital sizing uses the same collateral estimate as order reservation.
- Configure stop-loss, target and exit conditions separately. Each matched exit closes the full position.
- Reward/risk rules need a valid initial risk distance. For separate signal/traded markets or complex stops, configure **Reward/risk basis** in traded-contract price points. This freezes the meaning of 1R at entry; it does not place a stop by itself.
- Set trading days, session hours and no-trade windows relevant to your idea.
- Schedule explicitly offers all exchange trading days or selected weekdays. An empty custom selection must be completed before saving. Times use the chosen schedule timezone; exchange holidays still apply.
- End time controls when new entries stop for every strategy type. Existing positions continue to follow stop-loss, target and exit rules. The default entry window ends at 15:30 in Asia/Kolkata.
- NSE stock short entries use Intraday execution. Delivery/Swing stock borrowing is not supported.

## Save a version

- Use **Review** to inspect the configuration and validate it before saving. Compilation checks the rules; deployment and testing also check actual instruments, history, funds and allowances.
- **Validate** and **Save version** stay in the workspace header. Review's Edit links return to the relevant step. Removing configured conditions or instruments asks for confirmation.
- Saving Studio creates a version. Unsaved edits prompt before navigation and are not automatically applied to running sessions.
- Add a note explaining the change.
- Version lists show number, date and notes; long notes have a tooltip.
- Open version details to inspect readable before/after changes, including nested parameters and added/removed rules.
- Each test and deployment uses its own selected configuration; an edit does not silently replace a running version.

## Restore carefully

- Review the target version before restoring it.
- Use an explicit deployment/version-change operation to update running work.
- Stop or settle incompatible execution before changing its configuration.

## Current contract boundaries

- Choose exact futures/options contracts. Automatic expiry/strike selection and coordinated multi-leg strategies are not available yet.
- Expired contracts can be selected for historical testing when their catalog identity and dated specifications exist. This does not make them eligible for live orders.
- Historical ranges cannot cross expiry, contract-term changes or overnight futures settlement until those lifecycles are supported. A successful compilation is not a guarantee that every provider or broker supports the selected contract.

## Share only when you choose

- Public visibility enables a read-only configuration link.
- It shares rules, not your account, notes or execution records, and does not grant editing, cloning or another user's backtesting.
- Return visibility to Private to stop new public access.
