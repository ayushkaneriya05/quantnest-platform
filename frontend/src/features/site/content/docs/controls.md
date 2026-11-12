---
title: Account, Security and Records
description: Manage sign-in, 2FA, sessions, notifications, export and account access safely.
order: 10
---

## Profile and sign-in

Open Settings from your workspace profile menu. Profile lets you update the
offered personal fields and avatar. Your registered email is read-only in the
current profile form; contact Support if you need help with the account identity.

Use your password or configured Google sign-in. Google still follows your account's
2FA requirement. An existing password account is not silently linked to Google
just because the email text matches; follow the offered sign-in flow or ask Support.

Verify your email for checkout and to associate eligible earlier contact requests.
Verification is different from signing in and does not place a trade or buy a plan.

## Password recovery and changes

Use Forgot password on the sign-in page when needed. Follow the emailed reset
link without sharing it. After a successful reset, sign in again; earlier sessions
are revoked. If mail does not arrive, check spam and the address you registered,
then contact Support without sending your password.

When already signed in, use Security's password-change form and enter the current
password. A successful change refreshes the current browser's access and revokes
other sessions. Keep the new password private and unique.

## Enable two-factor authentication

1. Open **Settings → Security** and start authenticator setup.
2. Scan the provided QR code privately in an authenticator app.
3. Enter the current code to confirm setup. Starting setup alone does not enable it.
4. Store the generated backup codes securely. The plaintext codes are shown once.

When 2FA is enabled, sign-in requires a current authenticator code or one unused
backup code. A used backup code cannot be reused. Regenerating codes invalidates
the previous set. Disabling 2FA and regenerating codes require the verification
offered by Security; do not send those credentials through Support.

Authenticator setup QR codes and recovery links contain secrets. Do not attach
them to AI Research, tickets or screenshots.

## Review browser sessions

Security lists your active browser sessions. Check the current device/browser,
sign-in/activity information and any unfamiliar access. End an individual session
or use the offered control to sign out other sessions while keeping the current one.

Logging out ends access for the selected browser session. It does not stop an
automated strategy on the server or close a position. Use execution-session
controls for trading actions.

Reload normally restores sign-in when the session is still valid. If access was
revoked or expired, sign in again. Use one consistent site address; switching
between different hostnames is not the same browser origin/session.

## Notifications and Activity

Notifications preferences control supported account notifications. The notification
center stores owned messages and offers its read controls. A transient success/error
toast is different from a saved notification.

Activity shows recorded account/configuration actions and available filters.
It is not the order book, proof of an exchange fill or a replacement for Journal.
Check the actual order/session record when an action is pending.

Account/security, billing and support email also serve the workflows you use.
Keep your registered address accessible for recovery links and request updates.

## Export account records

Open **Settings → Account → Export records**. The JSON export includes supported
owned account, strategy, research, execution, review, billing and support records.
Passwords, broker secrets and backup codes are excluded. Keep the downloaded file
private: it can contain your questions, rules and financial activity.

Exports are limited by frequency and total file size. If your complete export is
too large, it fails rather than silently dropping old records; ask Support about
the records you need. Do not rely on this as a full broker statement or an export
of every internal operator record.

## Deactivate or erase your identity

The Account tab offers two different actions:

| Action | Effect |
| --- | --- |
| Deactivate account | Disable sign-in and new work while retaining records; request reactivation through Support |
| Delete account | Permanently disable sign-in and anonymize the identity; required financial/execution records are retained |

First close positions, settle pending/unknown orders across enabled execution
sources, and cancel automatic renewal in [Billing](/docs/billing/). The confirmation
checks remaining activity again. **It does not close or cancel trades for you.**

Eligible shutdown stops sessions, disables broker connections, cancels analysis
and revokes sign-in sessions. Identity erasure is not an immediate promise to
delete every transaction, backup or retained support record. Export what you need
before proceeding and contact [Support](/docs/support/) with retention questions.

## Configuration privacy and execution controls

Public strategy visibility shares the saved configuration, not your private
positions, payment records or journal notes. Choose the visibility deliberately.

Strategy status, a session's Pause/Stop, enabled execution scope and plan allowance
are separate controls. Renewing a plan does not resume a stopped session.
An application-monitored stop depends on running services; do not assume it is
an exchange-hosted protective order. Follow [Paper controls](/docs/paper/).
