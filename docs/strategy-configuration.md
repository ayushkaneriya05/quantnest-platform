# Strategy configuration

## Position sizing

Strategies and execution routes support two methods:

- **Fixed Quantity:** enter a positive number of units. Execution applies the instrument's lot size.
- **Capital Based:** allocate a percentage of available capital to an entry.

An execution route uses the strategy's sizing settings unless its sizing override is enabled. Risk Based sizing and its percentage field have been removed from the UI, API, models, execution calculations, and research draft contract. The one-time development data migration replaces that removed method with Capital Based at 10% and cleans saved configurations. Stop-loss and target rules remain available.

## Saved versions

Versions include strategy details, tags, trading rules and operand parameters, instruments and execution routes, sizing, schedule, event restrictions, entry/exit settings, and auto-disable rules. Changes are compared with the preceding saved version and grouped by section. The details dialog displays readable before/after values and the complete configuration; raw JSON is optional.

Automatic versioning captures configuration changes without a time-based debounce. Related edits in one transaction produce one distinct final snapshot. Snapshot creation locks the strategy while assigning its version number. Restoring a version recreates its configuration and records a new rollback version.

## Public share links

Save **Public** visibility to enable `/strategy/view/<id>`. Anyone with the link can read the current saved configuration without signing in. The public endpoint exposes configuration only, with no account data, execution results, editing, cloning, or backtest actions. Save **Private** to make new requests to the link unavailable. The page offers refresh and retry actions and does not cache the API response.

Strategy sharing no longer includes per-user invitations or marketplace cloning/backtesting permissions. Owners can still clone and backtest their own strategies.

## Auto-disable rules

Backtests use their saved configuration. Paper and live execution use the allocation's deployed version. Rule evaluation reads `auto_disable_rules` from that configuration and cached/in-memory execution metrics; it does not query the rule table.

Paper/live sessions persist the matched rules, deployed version, pause time, and cooldown deadline. Automatic resumption applies only to recorded risk pauses whose matched rules permit it. Manual pauses stay paused. A resumed session records a close-count marker to prevent the same historical result from immediately pausing it again. Redeployment clears that resume marker.

Auto-disable prevents new entries. Exit and position protection processing continues. Database writes for session state and background recovery are separate from evaluating rule definitions.

Live, paper, and backtest calculations share the same closed-trade metrics. Daily, weekly, and monthly loss periods use the deployed strategy timezone. Drawdown is measured from peak realized equity, excluding unrealized open-position P&L. Recovery replays recorded closes in timestamp/ID order to restore period totals, streaks, win rate, and the equity peak.

Paper/live close callbacks update the latest projection under the existing shared-state lock after the database commit. Recent trade IDs prevent duplicate updates; missing metrics or closes arriving out of order trigger recovery from recorded trades. Background context refresh restores incomplete projections, and entries wait until metrics are ready. Version changes clear resume acknowledgements and invalidate the projection so timezone changes are reflected in recovery.

## Applying changes

Run Django migrations, then restart Django, Celery, the research service, and execution workers through the normal process management workflow so they load the updated code. Existing workers retain Python definitions until restarted.

Implementation checks include Django system checks, migration consistency, focused ESLint, and the frontend production build. Real broker execution and visual browser checks require a separate verification pass.
