---
title: Strategy Builder and Versions
description: Rules, sizing, safeguards, version changes and sharing.
order: 4
---
## Make your idea explicit

- Select instruments and a default timeframe.
- Define entry and exit groups with supported indicators, prices, operators and parameters.
- Use AND/OR groups to describe how conditions combine. Set a separate condition timeframe when needed.

## Configure sizing and safeguards

- Choose fixed quantity or capital-based sizing.
- Configure stop-loss, target and exit conditions separately. Each matched exit closes the full position.
- Set trading days, session hours and no-trade windows relevant to your idea.
- End time controls when new entries stop for every strategy type. Existing positions continue to follow stop-loss, target and exit rules. The default entry window ends at 15:30 in Asia/Kolkata.
- NSE stock short entries use Intraday execution. Delivery/Swing stock borrowing is not supported.

## Save a version

- Add a note explaining the change.
- Version lists show number, date and notes; long notes have a tooltip.
- Open version details to inspect readable before/after changes, including nested parameters and added/removed rules.
- Each test and deployment uses its own selected configuration; an edit does not silently replace a running version.

## Restore carefully

- Review the target version before restoring it.
- Use an explicit deployment/version-change operation to update running work.
- Stop or settle incompatible execution before changing its configuration.

## Share only when you choose

- Public visibility enables a read-only configuration link.
- It shares rules, not your account, notes or execution records, and does not grant editing, cloning or another user's backtesting.
- Return visibility to Private to stop new public access.
