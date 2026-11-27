# Intraday stock, futures and options strategies for QuantNest

**Prepared: 23 November 2026.** This is a practical strategy-building playbook for
the current QuantNest implementation. It contains four strategy families and six
separately deployable long/short variants. It does not create deployments or place
orders in your account.

**Start with S-PULLBACK in Paper.** Add futures only when one lot fits your risk
budget. Treat options as a separately tested strategy, not as a cheaper substitute
for the same futures trade.

The recipes below are explicit research candidates. Their settings are proposed
starting parameters, **not strategies with a verified QuantNest win rate**. I
checked that all six numerical configurations compile with the current engine,
use supported operands and have correctly directed 2R target calculations. I did
not backtest their performance, inspect current trade opportunities or establish
that they are profitable in India. A high reward/risk setting cannot establish
an edge by itself.

## 1. What to build

Here, `reward:risk = 2:1` means a planned 2R target against a 1R stop.

| ID / suggested strategy name | Trade | Signal market | Intended situation | Planned reward:risk | Measured win rate |
| --- | --- | --- | --- | --- | --- |
| **S-PULLBACK — Stock Trend Pullback** | Buy a liquid NSE stock | The same stock | Established upward trend resumes after a controlled pullback | 2:1 | Not yet measured |
| **S-BREAKOUT — Stock Volume Breakout** | Buy a liquid NSE stock | The same stock | A completed bar breaks an established range with increased activity | 2:1 | Not yet measured |
| **F-LONG — Index Future Trend Reclaim** | Buy the selected index future | Its cash index | Upward trend resumes after a short pullback | 2:1 | Not yet measured |
| **F-SHORT — Index Future Trend Rejection** | Sell the selected index future | Its cash index | Downward trend resumes after a short bounce | 2:1 | Not yet measured |
| **O-CALL — Index Breakout, Long Call** | Buy the selected call | Its cash index | Bullish index breakout with a sufficiently strong option premium | 2:1 in premium points | Not yet measured |
| **O-PUT — Index Breakdown, Long Put** | Buy the selected put | Its cash index | Bearish index breakdown with a sufficiently strong option premium | 2:1 in premium points | Not yet measured |

These families overlap economically. Buying a stock, buying its index future and
buying a call during the same rally are correlated exposures, not three independent
edges. Initially run one family per underlying, and test the long and short
variants separately.

### Why these families, and what the evidence actually supports

Published research on US-stock opening-range breakouts found that selecting
unusually active stocks materially affected results. That supports investigating
liquidity/activity selection alongside a breakout; it does not establish these
specific rules, a transferable NSE win rate or a guaranteed return. S-BREAKOUT
below is a rolling-range design, **not a replication of that opening-range paper**.
[Zarattini, Barbon and Aziz: original research paper](https://concretumgroup.com/wp-content/uploads/2026/02/A-Profitable-Day-Trading-Strategy-For-The-U.S.-Equity-Market.pdf).

Trend pullbacks are included as a transparent hypothesis: require an existing
trend, avoid entering an extended impulse, and require renewed movement before
entry. EMA lengths, ATR multiples and target levels here are design choices to
test; they are not published estimates of an Indian-market edge.

Options need separate validation because premium also depends on volatility and
time to expiry. A correct directional index signal can still produce a losing
option trade. The OIC explains these sensitivities through Delta, Gamma, Theta
and Vega. [OIC: option pricing and market mechanics](https://prd-web.optionseducation.org/news/february-office-hours-faqs-option-pricing-strategies-and-market-mechanics).

## 2. Current QuantNest capabilities that change the design

Read this before entering the recipes into Studio.

| Current behavior | Consequence for these strategies |
| --- | --- |
| `CLOSE`, `HIGH`, `LOW`, `OPEN` and indicators use completed candles | A 5m condition uses the last completed 5m bar, not the forming bar |
| LTP is the last received price for its selected market | It can confirm a breakout between candle closes |
| An entry capture setup is the only active Entry group | Put all arming filters inside that one group's ALL tree |
| Arming freezes captures; confirmation must occur on a later observation | The candle signal and the later price breakout are distinct events |
| Stop loss and Target act on the traded position | Index signal points must never be used as option-premium risk points |
| Studio emits market orders | A breakout condition requests an order; it does not install a resting broker stop-entry order |
| Paper fills on an eligible later observation; Live uses broker fills | The observed signal price is not a guaranteed fill price |
| Backtests use synthetic OHLC observations and signal-quote fills | Fine intrabar sequences and realized live slippage are not proved by a good candle backtest |
| Cash stocks use CNC; derivatives use Margin | Do not assume the Intraday strategy label changes the broker product |
| Schedule End time stops new entries | **It does not square off positions** |
| Daily square-off is an optional schedule setting | Configure 15:15 IST for these examples. Shortened sessions can move the cutoff earlier. |
| No built-in daily loss cutoff, per-day trade cap, spread or Greeks operand | The corresponding controls below are explicitly manual |
| Strategy protection is evaluated by the running engine | It is not an exchange-hosted resting protective stop |

**These examples use supervised intraday deployments.** Verify scheduled
closures in Paper and check broker fills and remaining exposure in Live.
An unavailable runtime or broker can delay the close.

FYERS distinguishes Delivery/CNC from Intraday, and states that delivery positions
are not subject to intraday auto square-off. FYERS cash short selling is an
intraday-only activity. Therefore the stock recipes here are long-only; a cash
short recipe is not recommended with QuantNest's present CNC mapping.
[FYERS: product behavior](https://support.fyers.in/portal/en/kb/articles/how-to-place-an-overnight-delivery-order-in-fyers),
[FYERS: cash short selling](https://support.fyers.in/portal/en/kb/articles/what-is-short-selling).

Local implementation references:
[Studio guide](strategy-configuration.md),
[capture and confirmation](strategy-configuration.md#10-capture-and-confirmation),
[contract/product mapping](../backend/execution/types.py),
[entry windows](../backend/execution/compiler.py),
[signal evaluation](../backend/execution/engine.py),
[backtest fill behavior](backtesting.md#current-fill-policy-signal-quote).

## 3. Notation: translate every line into Studio

The blocks below are readable specifications, not importable code. Studio does
not have a playbook-import button.

| Notation | What to select |
| --- | --- |
| `S` | Market source: **Signal instrument** |
| `T` | Market source: **Traded contract** |
| `C5`, `H5`, `L5`, `O5`, `V5` | Signal Close, High, Low, Open, Volume; timeframe **5 Minutes**, Shift **0** |
| `C15` | Signal Close; timeframe **15 Minutes**, Shift **0** |
| `EMA20_5`, `EMA20_15`, `EMA50_15` | Signal EMA with that period/timeframe and price source Close |
| `A5` | Signal ATR, Period **14**, timeframe **5 Minutes** |
| `T.ATR14_5` | ATR14 on the traded contract; timeframe **5 Minutes** |
| `VWAP5` | Signal VWAP, Anchor **Daily**, timeframe **5 Minutes** |
| `T.VWAP5` | Same VWAP calculation on the traded contract |
| `Lag1(X)` | Wrap X in **Lag by bars**, Bars **1**, or use Shift 1 for a single supported candle input |
| `Highest20(H5)` | **Highest over bars**, Bars **20**, input Signal High, 5m |
| `Mean20(V5)` | **Rolling average**, Bars **20**, input Signal Volume, 5m |
| `H`, `L`, `A` | Remembered values from the Entry setup; not live-changing formulas |
| `RR` | **Position Risk:Reward Ratio**; this route's traded position |
| `AND` | Inside the group choose **All conditions** |
| `+`, `−`, `×`, `max` | Use the common expression/ƒx operations and Constant Value inputs |

All unspecified candle shifts are zero: the newest completed bar. Set timeframes
explicitly, including leaves inside formulas. All EMA price sources are Close.

For a preceding window, use:

```text
Previous20High = Lag1(Highest20(H5))
Previous20Volume = Lag1(Mean20(V5))
```

This excludes the signal bar. `C5 > Highest20(H5)` including the same bar's high
cannot express a valid close-above-prior-range breakout. A 20-bar rolling-volume
comparison also is **not** same-time-of-day relative volume across 20 sessions.

Do not put captured values, LTP or position state inside a rolling window.
See [rolling semantics](strategy-configuration.md#83-rolling-and-lag-operations).

## 4. Shared settings and operating routine

### Details and Schedule

| Setting | Baseline |
| --- | --- |
| Strategy type | Intraday |
| Visibility | Private |
| Paper trading | Enabled |
| Live trading | Enable only for a separately verified Live deployment |
| Default candle timeframe | 5 Minutes |
| Schedule timezone | Asia/Kolkata (IST) |
| Weekdays | Monday–Friday, subject to the exchange calendar |
| Entry start | **09:45:00** |
| Entry end | **14:30:00** |
| Excluded entry window | **11:45:00–13:15:00** for the initial baseline |
| Daily square-off | **15:15 IST**, subject to the exchange calendar and broker cutoff |
| Entry order type | Market, as currently supported by Studio |
| Stop-loss stage combination | OR, with one active stop group |
| Target stage combination | OR, with one active target group |
| Other Exit groups | None in the baseline |

These time choices are research parameters, not a claim that the midday window
is unprofitable. Keep the same schedule during the first comparison. A setup can
remain in memory across an excluded interval if no event resets it; do not rely
on the exclusion itself to clear captures. The short setup expiries below limit
that problem, and ordinary trading-session guards still apply.

Read current segment sessions, holidays and special-session notices from the
platform calendar and official exchange information. Do not hardcode an expiry
weekday or assume cash and derivatives always have identical closing schedules.
[NSE: contract specifications and trading information](https://www.nseindia.in/static/products-services/equity-derivatives-contract-specifications).

### Before the session — manual controls

1. Use liquid instruments and check the broker's actual spread/depth. LTP and
   historical volume alone do not prove you can transact your chosen size.
2. Avoid a stock's scheduled results/corporate-event session initially. Avoid
   initiating index trades around a known major policy announcement. Event
   avoidance is not an automatic QuantNest feature.
3. Choose either S-PULLBACK or S-BREAKOUT for a stock, not both initially.
4. Start with one traded instrument per deployment so fixed sizing is unambiguous.
5. Require a round-trip cost/slippage estimate small relative to the proposed R.
   As an initial research filter, reject a trade if estimated friction exceeds
   **0.15R**. This is a chosen cost budget, not an exchange rule or Studio guard.
6. Verify feed authorization, broker connection, history readiness, saved version,
   charge profile, quantity, available funds and absence of an unintended position.

### During and after the session — manual controls

- Initial planned risk per trade: at most **0.25% of total trading equity**.
- Initial total simultaneous planned risk: at most **0.75%** across all related
  deployments. Correlated variants should share a tighter combined budget.
- Stop opening new work after **1% realized daily loss** or **three consecutive
  losses**, whichever occurs first; explicitly pause the affected deployments.
- Initial operational cap: **two completed entry cycles per instrument per day**;
  pause afterward. Capture logic does not enforce this cap.
- At the square-off cutoff, check working orders and closing fills until flat.
  **Stop & close** is available when you need to intervene in Live. Handle
  rejected or unresolved exits promptly.
- Review trades, charges, missed signals, latency and unexpected re-entry in the
  Journal. Do not modify a running strategy to repair a losing trade.

The numerical percentages are conservative starting research limits, not
personalized sizing advice or guarantees of maximum loss. Slippage, gaps and a
failed exit can exceed the planned loss.

## 5. S-PULLBACK — stock trend pullback

### Idea and market setup

Buy a controlled pullback in an established upward trend, after price takes out
the signal bar's high. This avoids treating a continuously true `LTP > EMA20`
condition as permission for immediate repeated entries.

In Markets & size:

- Add a **fixed NSE cash stock** that passes your liquidity check.
- Signal instrument = that same stock; Entry direction = **Buy**.
- Sizing = **Fixed Quantity → Units**, calculated using section 9.
- Use the shared schedule from section 4.

This is intended for orderly trending sessions. It can repeatedly lose in
sideways trade or after a trend has already exhausted.

### Entry group: Capture & confirmation

Create one Entry group, name it `Trend pullback`, and select Configure.
**Arm when ALL nine conditions are true:**

```text
1. C15 > EMA20_15
2. EMA20_15 > EMA50_15
3. EMA20_15 > Lag1(EMA20_15)
4. L5 <= EMA20_5 + 0.10 × A5
5. L5 > EMA50_5
6. C5 > EMA20_5
7. C5 > O5
8. C5 > VWAP5
9. H5 - L5 <= 1.50 × A5
```

Rules 4–7 define a touch/reclaim while avoiding a deeper break of the slower
5m average. The 15m conditions provide direction; they do not predict a trend.

**Remember values:** `H = H5`, `L = L5`, `A = A5`.

**Intermediate confirmations:** none.

**Enter on a later observation when ALL:**

```text
S.LTP Crosses Above H + 0.05 × A
S.LTP <= H + 0.30 × A
C15 > EMA20_15
```

**Invalidate:** `S.LTP < L`.

**Expire:** completion of **2 new 5-minute bars** after arming. A confirmation at
the expiry boundary loses to expiry. This is a bar count, not a guaranteed ten
wall-clock minutes across breaks or session boundaries.

### Risk and exits

In Markets & size → Reward/risk basis → Define initial risk distance:

```text
RiskDistance = 1.20 × T.ATR14_5
```

Use traded-source inputs in this formula even though signal and trade happen to
be the same stock. The engine freezes the resulting distance when generating the
entry intent and retains it for the owned position; it does not keep moving the
denominator as ATR changes. Actual position average determines the later R value.

```text
Stop loss group: RR <= -1
Target group:    RR >= 2
Other Exit:     none
Daily square-off: 15:15 IST
```

This is an **ATR-distance stop**, not a stop guaranteed to lie below the captured
pullback low. The low invalidates an unfilled setup only. If you want a structural
low-based stop instead, research that as a separate version rather than silently
changing this definition.

### Worked example — hypothetical prices

At 10:20 the completed 5m signal has H=₹500.00, L=₹497.00 and A=₹2.00.
All arming filters hold. Confirmation threshold is ₹500.10 and the anti-chase
ceiling is ₹500.60. A later observed cross to ₹500.15 can request entry; a jump
straight to ₹501.00 fails the ceiling and must not be chased.

If traded ATR is ₹2.00 when the intent is generated, R distance is ₹2.40.
For an actual average fill of ₹500.20, the R stop corresponds to ₹497.80 and the
target to ₹505.00, before costs/slippage. Stop/target conditions request market
exits; those exact exit prices are not guaranteed.

## 6. S-BREAKOUT — stock volume-supported rolling breakout

### Idea and market setup

Buy continuation after a completed 5m close clears the previous twenty 5m highs,
then require a later break of the signal bar's high. Use the same fixed-stock,
same-signal, Buy, fixed-Units setup as S-PULLBACK.

This is intended for directional expansion, not range-bound sessions. It may
enter later than an intrabar breakout; that is the deliberate cost of requiring
a completed-bar signal.

### Reusable formulas and arming

Define:

```text
Previous20High   = Lag1(Highest over 20 bars(S.High, 5m))
Previous20Volume = Lag1(Rolling average over 20 bars(S.Volume, 5m))
```

Create one Entry capture group. **Arm when ALL seven conditions hold:**

```text
1. C15 > EMA20_15
2. EMA20_15 > EMA50_15
3. EMA20_15 > Lag1(EMA20_15)
4. C5 > Previous20High
5. C5 > VWAP5
6. V5 > 1.50 × Previous20Volume
7. H5 - L5 <= 1.80 × A5
```

Remember `H = H5`, `L = L5`, `A = A5`. No intermediate confirmations.

**Enter later when ALL:**

```text
S.LTP Crosses Above H + 0.05 × A
S.LTP <= H + 0.30 × A
C5 > VWAP5
```

Invalidate at `S.LTP < L`. Expire after **1 new 5m bar**.
Initial risk distance = `1.20 × T.ATR14_5`; stop = `RR <= -1`;
target = `RR >= 2`; no other baseline Exit. Use the shared schedule/closure.

### What this does not mean

- Twenty 5m bars are a rolling lookback and may cross a session boundary. They
  are not the first twenty bars of the current day.
- This is not a 09:15–09:30 opening-range breakout. The current vocabulary does
  not provide a dedicated time-bounded opening-range capture or same-clock
  multi-session relative-volume series.
- The 1.50× rule compares with the preceding twenty bars, not the same opening
  interval on earlier days. It can be affected by intraday volume seasonality.
- A breakout above yesterday's high is also a different strategy; this does not
  implement that merely because its window occasionally includes yesterday.

### Example

Previous20High=₹1,000.00. A completed signal bar has C=₹1,001.00,
H=₹1,002.00, L=₹998.50, A=₹3.00 and volume 1.8 times its preceding-window
mean. If the other filters hold, it arms.

The later confirmation threshold is ₹1,002.15, with a ₹1,002.90 ceiling.
With unchanged traded ATR, R=₹3.60. An average fill of ₹1,002.20 gives an
indicative ₹998.60 stop and ₹1,009.40 target. The captured low and actual R stop
are separate values; do not assume they are identical.

## 7. F-LONG / F-SHORT — index futures trend reclaim/rejection

### Contract and sizing configuration

Use **one cash-index underlying**, such as the NIFTY 50 index from your catalog,
and create two separate strategies for long and short testing.

| Field | Setting |
| --- | --- |
| Add instrument | Automatic F&O selection |
| Underlying / Signal | The selected cash index |
| Contract family | Future |
| Expiry | Nearest eligible listed expiry |
| Include contracts expiring today | No |
| Option right / strike fields | Not used for futures |
| Quantity | Custom Fixed Quantity → Lots; start with 1 only if section 9 allows it |
| F-LONG direction | Buy |
| F-SHORT direction | Sell |
| Schedule | Shared section 4 settings |

Read actual lot size and multiplier from the selected contract. Do not type an
old NIFTY/BANKNIFTY lot quantity from an online example. Check actual broker margin;
the platform's simulated collateral percentage is not an exchange margin quote.
[NSE: current contract specifications](https://www.nseindia.in/static/products-services/equity-derivatives-contract-specifications).

If you do not want automatic expiry selection, add the exact future instead,
then change its Signal instrument to the cash index. You must manually change
that fixed contract when appropriate; neither version rolls an open position.

### F-LONG: arm ALL eight conditions

Signal inputs below refer to the cash index; the VWAP input explicitly refers
to the **future**:

```text
1. C15 > EMA20_15
2. EMA20_15 > EMA50_15
3. EMA20_15 > Lag1(EMA20_15)
4. EMA9_5 > EMA21_5
5. C5 > EMA9_5
6. Lag1(C5) <= Lag1(EMA9_5)
7. T.Close(5m) > T.VWAP(5m, Daily)
8. H5 - L5 <= 1.80 × A5
```

Rules 5–6 mean the completed signal bar reclaimed its fast average after the
previous completed bar was at/below its corresponding fast average. This is
different from comparing an old close with today's newest EMA value.

Remember `H = H5`, `L = L5`, `A = A5`. No intermediate steps.

```text
Confirm ALL:
  S.LTP Crosses Above H + 0.05 × A
  S.LTP <= H + 0.30 × A
  C15 > EMA20_15
Invalidate: S.LTP < L
Expire: 2 new 5m bars
```

### F-SHORT: arm ALL eight inverse conditions

```text
1. C15 < EMA20_15
2. EMA20_15 < EMA50_15
3. EMA20_15 < Lag1(EMA20_15)
4. EMA9_5 < EMA21_5
5. C5 < EMA9_5
6. Lag1(C5) >= Lag1(EMA9_5)
7. T.Close(5m) < T.VWAP(5m, Daily)
8. H5 - L5 <= 1.80 × A5
```

Remember the same H/L/A values. No intermediate steps.

```text
Confirm ALL:
  S.LTP Crosses Below L - 0.05 × A
  S.LTP >= L - 0.30 × A
  C15 < EMA20_15
Invalidate: S.LTP > H
Expire: 2 new 5m bars
```

### Shared futures risk and exits

```text
Initial risk distance: 1.20 × T.ATR(14, 5m)
Stop loss:            RR <= -1
Target:               RR >= 2
Other Exit:           none
Daily square-off:      15:15 IST
```

Do not calculate VWAP or a volume filter on a cash index: it is not a traded
contract with stock-like transaction volume. The future supplies the VWAP and risk
basis; the index supplies the directional/capture logic.

If a short future fills at 25,000 and R distance is 40 future-price points,
the indicative stop is 25,040 and target 24,920. Profit is `80 × quantity ×
multiplier` before charges. This example intentionally does not specify a current
exchange lot size. There can be index/future basis changes; the two prices are
not interchangeable.

Initially avoid the contract's expiry session. This is an intraday future strategy,
not a rollover, spread, physical-delivery or settlement-arbitrage system.

## 8. O-CALL / O-PUT — index breakout expressed through a long option

### Contract configuration

Build call and put variants separately. **Both Entry directions are Buy.** A
bearish index view is implemented by buying a put, not by setting its direction
to Sell.

| Field | Initial candidate |
| --- | --- |
| Add instrument | Automatic F&O selection |
| Signal underlying | One liquid NSE cash index from the catalog |
| Contract family | Option Contract |
| Right | Call for O-CALL; Put for O-PUT |
| Expiry policy | **Next eligible listed expiry**, not the nearest |
| Include contracts expiring today | No |
| Strike selection | **ITM** |
| Listed strikes from ATM | **1** |
| Direction | **Buy** for both |
| Size | Custom Fixed Quantity → Lots; 1 only if affordable within the loss budget |
| Schedule | Shared section 4 settings |

Next means the listed expiry immediately after Nearest, not a fixed number of
days. Check the chosen date each session. ITM 1 moves one actual listed strike
below ATM for calls and above ATM for puts. It is not a promised Delta value.
If its spread/liquidity is unsuitable, skip the trade; ATM should be a separately
evaluated variant, not an ad hoc substitution for a failed signal.

The selected premium needs its own history. Do not replace unavailable option
ATR/EMA values with index values. After a sufficiently large underlying move,
the flat route can require history for another strike and must wait until ready.

### O-CALL: arm ALL five conditions

```text
1. C15 > EMA20_15
2. EMA20_15 > EMA50_15
3. C5 > Lag1(Highest over 10 bars(S.High, 5m))
4. C5 > O5
5. H5 - L5 <= 1.80 × A5
```

Remember index `H = H5`, `L = L5`, `A = A5`. No intermediate steps.

### O-PUT: arm ALL five conditions

```text
1. C15 < EMA20_15
2. EMA20_15 < EMA50_15
3. C5 < Lag1(Lowest over 10 bars(S.Low, 5m))
4. C5 < O5
5. H5 - L5 <= 1.80 × A5
```

Remember the same index H/L/A values. No intermediate steps.

### Premium risk formula and final confirmations

Define one reusable formula with **Traded contract** leaves:

```text
RiskDistance = max(1.20 × T.ATR(14, 5m), 0.10 × T.LTP)
```

Select this formula as the explicit initial risk distance. It is in **option
premium points** and is frozen for the entry intent, not recomputed every tick
for the owned position.

For **O-CALL**, final confirmation is ALL:

```text
S.LTP Crosses Above H + 0.05 × A
S.LTP <= H + 0.30 × A
C15 > EMA20_15
T.LTP > T.EMA(20, Close, 5m)
RiskDistance <= 0.20 × T.LTP
```

For **O-PUT**, final confirmation is ALL:

```text
S.LTP Crosses Below L - 0.05 × A
S.LTP >= L - 0.30 × A
C15 < EMA20_15
T.LTP > T.EMA(20, Close, 5m)
RiskDistance <= 0.20 × T.LTP
```

The premium-strength comparison is **greater than for both**: you want the option
you are buying to strengthen, whether it is a call or a put.

```text
O-CALL invalidation: S.LTP < L
O-PUT invalidation:  S.LTP > H
Both setup expiries: 1 new 5m bar
Both Stop loss:      RR <= -1
Both Target:         RR >= 2
Other Exit:          none
Daily square-off:     15:15 IST
```

This produces a proposed initial risk distance between 10% and 20% of the
observed premium when accepted by the filter. It does not cap a market-exit loss
at 20%, nor define risk as 10% of your account. The 10% floor and 20% filter are
candidate parameters to validate against costs and actual option behavior.

Only index-derived quantities are captured. Keeping the arm/captures free of a
specific premium helps an underlying-only setup survive an eligible flat strike
selection change. Final traded inputs must still be ready. Once an order is
pending or exposure is owned, its contract is pinned until the cycle finishes.

### Worked premium example

At entry intent time, option LTP=₹240.00 and option ATR14=₹15.00:

```text
1.20 × ATR = 18.00
10% of premium = 24.00
RiskDistance = max(18.00, 24.00) = 24.00
20% premium filter = 48.00 → passes
```

If actual average entry is ₹240.50, the indicative stop is ₹216.50 and target
₹288.50. If the underlying rises 100 points, that does **not** imply the option
gains 100 points, reaches 2R or fills at that target. Use actual contract prices.

Check bid/ask in the broker terminal. As an initial manual filter, require spread
no wider than **0.50% of midpoint**, and also require its rupee cost to fit the
0.15R round-trip friction budget. A percentage spread alone can be misleading
relative to a tight stop. This is not an implemented Studio spread filter.

Avoid expiry-day buying, illiquid strikes and known volatility-event sessions in
the initial experiment. Time decay and volatility changes can offset the benefit
of the index moving in the anticipated direction.
[OIC: buying options, time decay and volatility](https://www.optionseducation.org/news/september-2026-webinar-key-takeaways).

No naked option selling, averaging down or coordinated multi-leg strategy is
included. An index put and call in separate deployments are not an atomic spread.

## 9. Position sizing: calculate loss risk, not just capital allocation

The present size methods are fixed quantity and percentage of available capital.
**Capital percentage is not percentage loss-at-stop sizing.** Use fixed quantities
for this playbook and calculate them before deployment.

Let:

```text
E = total trading equity being risk-budgeted
B = 0.0025 × E                    # 0.25% planned risk budget
D = estimated initial price-point R distance
L = contract lot size             # 1 for ordinary cash shares
M = contract financial multiplier
F = estimated costs + adverse slippage allowance for the proposed quantity

Planned price loss per lot = D × L × M
Choose the largest whole lot count n satisfying:
    n × D × L × M + F(n) <= B
and satisfying available cash / actual broker margin and portfolio limits.

Order units = n × L
```

If fees are approximated as a fixed buffer F, an initial bound is
`floor((B - F) / (D × L × M))`. Recalculate fees for that quantity and reduce it
if necessary. If one lot does not fit, **skip the trade**. Do not round up, widen
the account risk budget to force an entry or enter 1 Unit on a multi-unit lot.

Because ATR/premium can change before a later signal, the pre-session quantity is
only a risk estimate. The current engine does not resize a fixed order from the
eventual frozen R. Use the widest plausible stop for the admitted session or
recalculate while flat and deploy deliberately; the 0.25% cap is not automatically
enforced by this fixed-size configuration.

### Examples — all numbers and lot sizes are hypothetical

| Case | Calculation | Decision |
| --- | --- | --- |
| Stock | E=₹100,000; B=₹250; D=₹2; reserve F=₹10; M=L=1 | At most 120 shares from risk; reduce further if cash/cost estimates require it |
| Future | E=₹500,000; B=₹1,250; D=40 points; L=25; M=1; estimated F=₹150 | One lot has ₹1,150 planned loss including buffer; requires separate broker-margin headroom |
| Option too large | E=₹100,000; B=₹250; D=₹24; L=25; M=1 | One lot's ₹600 price risk already exceeds B: no trade |
| Same option, larger budget | E=₹300,000; B=₹750; price risk per lot ₹600 and estimated F=₹50 | One lot fits the estimated risk budget, subject to liquidity/cash/portfolio gates |

For long options, premium cash outlay is `entry premium × L × n × M`. That is a
different figure from stop risk. The whole premium can be lost in an adverse
scenario even when the intended stop risks much less. Futures margin is also
different from maximum potential loss.

In QuantNest, enter the computed share quantity as Units or the computed whole
lot count as Lots. **Do not enter lot count as derivative Units.**

## 10. What win rate would make the payoff worthwhile?

For ideal full-target winners, full-stop losers and an average cost `c` in R:

```text
Net expectancy per trade = p × W - (1 - p) × L - c
Break-even p = (L + c) / (W + L)
```

Here p is win probability, W average gross winning R and L average gross losing R.
With W=2 and L=1:

| Planned payoff | Before-cost break-even win rate | Break-even with 0.10R average cost |
| --- | --- | --- |
| 1.5R win / 1R loss | 40.00% | 44.00% |
| 2R win / 1R loss | 33.33% | 36.67% |
| 2.5R win / 1R loss | 28.57% | 31.43% |

At a **hypothetical** 40% win rate, 2R wins, 1R losses and 0.10R cost,
expectancy is `0.40×2 - 0.60×1 - 0.10 = +0.10R`. This is arithmetic, not an
estimate for these strategies. A higher target may reduce the hit rate; you
cannot increase reward without changing the distribution of results.

Time closures, gaps, partial fills, slippage and rejected exits mean realized W
and L will differ from the nominal 2 and 1. For actual reporting, use **net** R
after all charges; do not subtract costs twice if they are already included in
the winning/losing averages.

Do not advertise 60–80% win rates, 2R per day or a fixed monthly return without
relevant independent results. Measure expectancy, drawdown and execution quality
alongside win rate. A high win rate can hide rare large losses.

## 11. Re-entry, missed crosses and what to expect on the screen

Every recipe uses capture & confirmation instead of a bare level-only entry:

1. Flat + running + eligible schedule/data: a new known true arming occurrence
   freezes H/L/A.
2. That same observation cannot open its trade. It seeds later-cross comparisons.
3. A later observed crossing must satisfy the anti-chase and other final filters.
4. Expiry/invalidation wins before entry; unavailable inputs do not become true.
5. Pending/owned exposure preserves its actual contract and captures.
6. After full closure, the setup needs a new false → true arming edge. A still-true
   arm is not immediate permission to re-enter. A later valid occurrence may
   re-enter; there is no automatic two-trades-per-day cap.

An initial quote already beyond the trigger is not a newly observed cross. A jump
past the anti-chase ceiling consumes that crossing without permission to enter;
simply drifting back inside the ceiling while remaining above the threshold is
not a new crossing. Do not replace the cross with Greater Than just to force a
missed trade without testing the resulting re-entry/chase behavior.

Pausing, feed resets and history corrections can abandon an unfilled sequence.
Do not infer a missed trade merely because a later completed chart appears to
contain the setup: the live evaluator needs the observations, ready selected
contract history and an eligible arming/confirmation sequence at the time.

## 12. Build, test and deploy in QuantNest

### Create the first strategy

1. Strategies → New Strategy → enter the suggested name and Intraday details.
2. In Studio → Markets & size, select the exact stock or automatic derivative
   policy, signal source, direction and correctly calculated size.
3. Add the traded-source RiskDistance expression and choose it as the initial
   reward/risk basis. Constants and formulas are price distances, not currency
   account P&L values.
4. Conditions → Entry: create one group, open Configure, and enter the recipe's
   **Arm**, remembered values, final confirmation, invalidation and expiry.
   There are no intermediate steps in these baseline recipes.
5. Add a Stop loss group with `Position Risk:Reward Ratio <= -1` and a Target
   group with `Position Risk:Reward Ratio >= 2`. Leave other exits disabled.
6. Enter Schedule exactly, including the excluded window. The chosen schedule
   controls entries and arming, not an automatic end-of-day liquidation.
7. Validate, review the dependency/history requirements, and Save version.
8. Reopen that version and check the source/timeframe on every input; a label
   that looks similar can still refer to the wrong market.

### Backtest and Paper acceptance

1. Begin with fixed stocks/futures and inspect actual entries/exits before
   introducing dynamic option selection. Include a realistic charge profile.
2. Use a chronological development period, validation period and untouched
   out-of-sample period. Include trending, sideways, gap and stressed sessions.
   Do not select only currently successful stocks for a historical universe.
3. Use earlier history to warm features; do not allow indicators or contract
   selection to borrow future prices. Review expired-contract catalog and
   current-lot-size fallback assumptions in derivative backtests.
4. Set Daily square-off to 15:15 IST before backtesting these rules over
   multiple days. Check the exit reason and time in the trade ledger. Review any
   coverage warnings for positions carried beyond the cutoff.
5. Test higher friction: for example 0.05%, 0.10% and 0.20% per-fill modeled
   slippage, then compare with actual observed spreads/fills. These are stress
   scenarios, not forecasts and not a replacement for bid/ask modeling.
6. Manually audit a sample of signals against source candles, captured levels,
   initial risk, selected contract, actual quantity and costs. Inspect stop and
   target touched within the same 1m bar: synthetic OHLC ordering can determine
   the result. Keep such ambiguity visible.
7. Deploy the pinned saved version in Paper. Record signals that failed entry,
   fills, R, fees and end-of-day operator closure. Do not compare a changing draft
   to a session running an older saved version.

An initial research acceptance screen could require at least 200–300 untouched
out-of-sample trades across several market conditions, positive net expectancy,
net profit factor above 1.20 and tolerable drawdown under higher-cost assumptions.
Those thresholds are proposed screening rules, **not sufficient statistical proof
or guaranteed production readiness**. Calendar clustering reduces the effective
number of independent observations. Paper exposure over only a few days also
does not establish an edge.

Try only a small predeclared parameter neighborhood, such as ATR multiplier
1.0/1.2/1.5 or target 1.5/2.0/2.5, without treating every combination as an
independent discovery. Repeatedly choosing the best backtest can overfit noise.
[Bailey et al.: The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

### Live acceptance and operation

Only progress when the research evidence and operational checks support it:

1. Use a deployment with Live scope, a verified authorized broker connection and
   current market data; confirm the intended product and sufficient broker funds.
2. Check minimum-lot loss risk. If it is too large, continue Paper; do not force
   an oversized real-market experiment.
3. Supervise an appropriately sized first deployment. Confirm both entry and exit
   broker fills, actual contract IDs, average prices and duplicate-report handling.
4. Keep the data, execution, broker-event and reconciliation services available.
   An engine-monitored stop cannot trigger while its required services/data are
   unavailable. Follow the account's established broker-side emergency procedure
   and reconcile before resuming; an external manual exit does not automatically
   rewrite QuantNest's session ownership.
5. Perform the manual loss/trade-count gates and verify the scheduled 15:15
   closes in the broker's order and position records.
6. Compare Live gross results with actual broker charges. Current Live reporting
   excludes actual broker fee accounting; Paper/backtest estimated net is not
   directly comparable to a Live before-fees figure.

See [Live operations and boundaries](live-trading.md),
[Paper session controls](paper-trading.md) and
[deployment acceptance](../infra/START-HERE.md#7-acceptance-and-release-checklist).

## 13. What was checked for this playbook

All six recipe expression configurations compiled against the current
`execution.compiler` with database access explicitly forbidden. Checks covered:

- One entry capture setup plus one stop and one target group per variant.
- Supported price, EMA, ATR, VWAP, volume, rolling, lag, arithmetic, capture and
  position-R inputs; correct traded-source risk leaves.
- A short future's profitable downward move evaluates as positive R.
- A long put's profitable premium increase evaluates as positive R; its entry
  direction stays Buy.
- No cash-index VWAP used by the option signal configuration.

Compiled historical dependencies were:

| Variant | Signal 5m bars | Signal 15m bars | Traded 5m bars |
| --- | --- | --- | --- |
| S-PULLBACK | 251 | 251 | 71 |
| S-BREAKOUT | 78 | 251 | 71 |
| F-LONG / F-SHORT | 106 | 251 | 78 |
| O-CALL / O-PUT | 71 | 251 | 101 |

These are compiler requirements for these exact expression trees, including
indicator stabilization and shifts. They are not separate provider calls per
rule: shared data/features are reused, and stock signal/trade roles reference
the same actual instrument. A newly selected option still needs its own premium
history. Roughly 251 regular 15m bars span about ten ordinary cash sessions, so
do not expect one morning's history alone to warm EMA50-based filters.

Compilation is a compatibility check. **No performance backtest, live trade or
empirical win-rate claim was produced for these recipes.**

## 14. Suggested order of work

1. Build **S-PULLBACK** on one liquid stock and validate every trade's logic.
2. Compare **S-BREAKOUT** on the same development/holdout methodology; retain the
   better supported candidate, not whichever just won the last session.
3. Test **F-LONG** and **F-SHORT** independently using actual future prices and
   costs. Add real exposure only if one lot meets the budget.
4. Test **O-CALL** and **O-PUT** on their actual historical premiums, expiries and
   selected strikes. Do not transfer the futures win rate to options.
5. Verify scheduled exits and broker-side emergency procedures before relying on
   the live strategy.

The useful outcome is a small, explainable and validated trading process—not the
largest indicator list or a claimed high win rate without evidence.
