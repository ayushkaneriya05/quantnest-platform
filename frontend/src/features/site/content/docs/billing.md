---
title: Billing and Usage
description: Understand allowances, actual AI credits, payment verification, renewal, invoices and refunds.
order: 11
---

## Check availability before paying

Open **Settings → Account → Billing and Usage**, or Pricing for the currently
published plans. Explore is free. Build and Pro add the amounts shown in the
current catalog; this guide does not fix future plan prices or quota numbers.

Public plans currently cover the supported NSE-stock workflow through simulation
and Paper. NSE futures/options remain listed as Coming soon where shown, without
an announced release date. A paid plan does not activate them early or enable
customer Live trading. QuantNest Private is not currently for sale.

## Three kinds of allowance

| Type | Examples | What reduces availability |
| --- | --- | --- |
| Per-period work | Backtest credits, AI credits, screen runs, Monte Carlo runs | Successful work and applicable in-progress reservations |
| Saved/active capacity | Strategies, named screens, active Paper deployments/instruments | Current saved records or active deployment capacity |
| Per-request maximum | Stocks, attached backtests, source workload, simulation count | The size of that request; it is not a spendable remaining balance |

Explore renews on calendar months in Asia/Kolkata. Paid allowances follow the
verified billing period. Work stays associated with the period in which it was
accepted. Unused allowances do not roll over, and no automatic paid overage is sold.

Archived but undeleted strategies still use saved capacity. Running, Paused,
Stopping and Error Paper sessions use active capacity; Stopped releases it.
Existing over-limit records are not silently deleted after a plan change.
New work and applicable restart/version-change actions must fit the current plan.

## Backtests, screening and failed work

A backtest preview shows workload and the accepted credit requirement, including
required warmup. Starting the accepted work reserves that amount. Completion
settles it; failure/cancellation releases the reservation. Deleting a completed
result does not refund successful work. A rerun is new admitted work.

Running a screen consumes the separate screen-run allowance. Saving its named
configuration uses saved-screen capacity. Monte Carlo has a separate run allowance
and per-request simulation maximum. These do not share the AI token-credit balance.

## AI credits are actual reported usage

One AI credit equals 1,000 reported provider tokens. Replies display fractional
credits to three decimal places; for example, 88,654 tokens equal 88.654 credits.
The amount includes the model calls needed for that saved answer rather than
one flat “message” charge.

Admission needs positive remaining balance and allows one active research request
per user. It does not impose a customer token budget inside each request. A
successful saved answer charges its actual reported usage once. Failed/cancelled
research is not charged to the customer.

An answer already accepted can exceed the remaining balance and finish. The next
request is blocked, the displayed spendable balance is zero, and the next period
starts fresh without carried debt. Provider usage can be marked incomplete when
not fully reported; inspect that label rather than treating missing usage as free.

## Review checkout

1. Sign in and verify your account email.
2. Select an offered plan and read its current price, allowance period, taxes and total.
3. Use manual payment when offered, or explicitly consent to automatic renewal.
4. Complete the provider checkout and return to Billing to check verification.

Checkout can be unavailable while payment collection is disabled. A browser
success callback is not itself proof that the payment was captured and applied.
If processing is delayed, inspect the existing attempt before paying again.
Keep its reference and contact Support if the status remains unresolved.

## Paid periods, invoices and renewal

Billing shows the confirmed plan, paid-through dates, payment status and recent
invoices. Download the owned invoice when available. Its invoice number and the
provider's payment reference are different identifiers.

Cancel automatic renewal to stop future renewals while keeping the current paid
period. Cancellation is not an immediate refund or deletion of your saved work.
Choosing free Explore does not create a paid prorated conversion.

For an active automatic subscription, an offered plan change is scheduled for
the verified future renewal. A manual-payment account uses another reviewed
manual checkout rather than the automatic-subscription change flow. Read the
displayed effective dates and totals; do not assume immediate proration.

If a provider operation is still being reconciled, a conflicting new change can
be blocked. Wait for its final state instead of submitting repeated changes.
Renewal never automatically restarts a paused/stopped Paper session.

## Refund requests

The published policy provides a seven-day request window for the first paid
Workspace purchase, alongside applicable remedies. Open the captured payment's
refund request, provide its payment reference and reason, and follow the status.
Other requests can require individual review.

Eligible is not Approved, and Approved/provider pending is not money returned.
Confirmed processing updates the record and relevant credit note. A full processed
refund can change paid access; a partial refund does not necessarily remove the
whole period. Do not submit a second payment merely to work around an unresolved
refund or disputed payment.

Recent billing history is not an unlimited historical export. Use [account export](/docs/controls/)
or [Support](/docs/support/) for broader record questions. Custom Development
agreements/payments remain outside this application. Read the [refund policy](/refunds/).
