# Authentication, browser sessions and administrator access

**Source review: 16 October 2026.** Customer sign-in, Django Admin sign-in, market
source authorization and customer broker authorization are separate flows.
Provider account registration is covered in [Third-party setup](third-party-setup.md).

## 1. Origins and ingress

React calls `/api/v1/` on the website's origin. Vite handles development proxying;
Cloudflare Pages handles Public ingress; Private Caddy serves/proxies the deployment.

FRONTEND_URL identifies the browser origin. BACKEND_URL identifies the external
callback origin. Production examples use the same HTTPS origin. Derived callback
URLs must exactly match provider registrations.

Public HTTP/WebSocket ingress requires the configured trusted gateway token.
A direct call to the Oracle origin can correctly return 403 even with a valid user
token. The private research-tools route uses its own internal authentication.
Do not expose the gateway secret in a VITE variable or browser request code.

Use one hostname consistently during local OAuth/Admin work. localhost and
127.0.0.1 have different cookies. A source-login start on the wrong hostname
redirects to its configured callback origin before creating the verification cookie.

## 2. Password login and page reload

1. The frontend calls `GET /api/v1/users/auth/csrf/` to initialize CSRF and learn
   whether a refresh cookie is available.
2. Password login calls `POST /api/v1/users/auth/login/`.
3. If local 2FA is enabled, the response contains a short-lived challenge instead
   of issuing authenticated tokens. Verification completes the same login service.
4. The server identifies a browser profile with the HttpOnly quantnest-device
   cookie and reuses/replaces that browser's owned active session.
5. The response contains the access token, user and CSRF token. The refresh token
   is written as an HttpOnly cookie and is not returned to JavaScript.
6. On reload, the frontend rotates the refresh session and loads the user before
   protected routes render. Signed-out visitors skip an unnecessary refresh.

| Credential | Current behavior |
| --- | --- |
| Access token | 15-minute lifetime; held in Redux memory for bearer requests |
| quantnest-auth cookie | HttpOnly access credential used by browser socket authentication |
| quantnest-refresh-session cookie | HttpOnly refresh credential scoped to /api/v1/users/ |
| quantnest-device cookie | Browser identity, not an authentication credential by itself |
| UserSession | Server-side owned session identity, expiry, refresh JTI and descriptive metadata |

A different browser profile/incognito window is a separate session. Tabs in one
browser share cookies. IP/user-agent metadata does not determine session identity.

ACCOUNT_EMAIL_VERIFICATION is currently optional. Mandatory verification would
require verification and a subsequent sign-in; do not assume creating a user
proves email ownership for records that explicitly require a verified address.

## 3. Refresh, concurrency and revocation

Refresh calls `POST /api/v1/users/auth/token/refresh/`. Under a database lock the
service validates the current refresh JTI, blacklists the old token, rotates
credentials and updates the existing session. Refresh does not create a new session.
Its seven-day expiry starts from the latest successful rotation.

The frontend shares concurrent refresh work, refreshes before expiry and on tab
resume, and uses Web Locks where available to serialize cookie-changing actions
across tabs. Authentication generation checks prevent a stale response from a
previous login restoring a signed-out user or another user's data.

Only non-secret login/logout signals use localStorage. Access/refresh credentials
must not be persisted there. Other tabs recover the shared cookie session on a
login signal and clear authentication on logout.

| Action | Session effect |
| --- | --- |
| Logout | Deletes the owned current session, blacklists refresh and clears cookies |
| Revoke selected session | Ends only the owned selected record |
| End other sessions | Preserves the authenticated current session |
| Change password | Requires current password; ends other sessions and rotates current credentials |
| Reset forgotten password | Revokes sessions; requires fresh sign-in |
| Deactivate/delete account | Revokes all sessions after account lifecycle validation |

Every REST authentication checks user/session validity and token/password
invalidation. last_activity updates are bounded rather than written on every call.
Expired records are hidden/pruned and the daily cleanup removes remaining token history.

Network/server failures during refresh permit retry; invalid authentication ends
the session. Failed logout stays visible as an error so it can be retried rather
than pretending the server session ended.

## 4. CSRF and stale administrator forms

Cookie-changing authentication requests use CSRF validation. The frontend obtains
the token and sends it with unsafe requests. Secure production cookies require
HTTPS; configure trusted origins from the actual deployment.

Django rotates CSRF state on authentication. A previously rendered Admin form can
contain an old token after another tab/login, Back navigation or a cached page.
Open the canonical Admin URL again and use the newly rendered form. Do not disable
CSRF or make login exempt to work around this.

If a new form still fails, inspect duplicate host/path cookies, blocked cookies,
canonical URL, gateway headers and the actual Origin. Do not paste cookies/tokens
into support messages.

## 5. Two-factor authentication

Customer Security settings provide setup, verification, backup-code regeneration
and disable actions. Setup creates a pending device and displays a QR/manual secret.
The user confirms a code before relying on it. Setup does not delete an existing
confirmed device.

Password/Google login for a protected account returns a five-minute, single-use
challenge bound to the current password state. Verification accepts an eligible
TOTP or backup code. TOTP replay and reused backup codes are rejected; sensitive
actions are throttled.

Store recovery codes privately. The login OTP comes from the authenticator to
which the device was enrolled, not an email or a broker authorization token.

## 6. Django Admin enrolment

Admin uses OTPAdminSite under `/admin/` and is titled **QuantNest Operations**.
An authenticated customer JWT is not a staff OTP-verified Django session.

For a new installation, from backend/ with the correct environment:

```sh
python manage.py createsuperuser
python manage.py enrol_staff_otp --username YOUR_ADMIN_USERNAME
```

The second command prints a secret provisioning URI. Import it privately into
your authenticator, then sign into Admin with username, password and the current
code. Do not retain the URI in shared logs, screenshots or tickets.

The command requires an existing staff user and refuses to replace a confirmed
device. Existing-device recovery requires an authorized operator procedure on the
host; creating another secret blindly is not the normal login flow.

Configure the Django Site through `configure_site` as described in the selected
mode's infrastructure guide. Business actions remain in Admin; routine records
are created by their services.

## 7. Google sign-in

1. `POST /api/v1/users/auth/google/start/` accepts an allowed local return path.
2. Django creates random state and a PKCE verifier in a signed five-minute
   HttpOnly cookie and returns Google's authorization URL.
3. Google redirects to `/api/v1/users/auth/google/callback/`.
4. The backend verifies/consumes state and exchanges the code with the verifier
   and server-side client secret.
5. It creates a one-use result cookie and redirects to /google-callback.
6. The frontend calls the CSRF-protected google/complete/ endpoint.
7. The shared login service either issues the browser session or asks for local 2FA.

Tokens are not put into the frontend URL. The provider callback does not itself
create an authenticated Django Admin session.

Configure a Google Social application in Admin with its web client credentials,
associated with the correct Django Site. Register the exact BACKEND_URL callback
with Google. There is no frontend Google secret or popup SDK.

Existing password accounts are not silently linked merely because a Google email
matches. Provider cancellation, invalid/expired state, inactive accounts and changed
passwords invalidate the pending result. Retrying starts a fresh flow.

## 8. WebSocket authentication

Sockets use an HttpOnly access cookie, allowed frontend Origin, active owned
session, expiry and revocation checks. No JWT appears in a socket query string.
Public sockets also require trusted gateway ingress.

On expiry/revocation, the browser refreshes when appropriate and reconnects its
streams. Resubscription is not guaranteed replay of all missed market/fill events;
REST reloads recover current records.

## 9. Market source and broker OAuth

| Flow | Who starts it | Callback and stored result |
| --- | --- | --- |
| Market source | Staff administrator at /api/v1/market/fyers/login/ | /api/v1/market/fyers/callback/; source access token |
| Broker account | Customer's broker connection workflow | /api/v1/brokers/credentials/fyers/callback/; owned broker session |
| Workspace refresh | Signed-in customer/browser | users/auth/token/refresh/; QuantNest session rotation |

The source flow checks signed state, same-browser cookie, current staff user and
one-time nonce within ten minutes. The start canonicalizes to the registered
callback host before setting its flow cookie. A used/expired callback must be
replaced by a fresh start, not replayed.

Source and broker access-token expiry require fresh provider sign-in. The removed
FYERS refresh-token feature is unrelated to required QuantNest account refresh.
Broker app credentials/callbacks are separate from operator data-source credentials.

Execution scope and applicable Private/data permissions still apply after a
successful broker authentication.

## 10. Profile images and account records

The profile API returns a signed API-relative avatar URL. It authorizes the current
active user's current stored image for up to 30 minutes without exposing a public
media directory. The image view buffers the small file into a regular response;
it does not use a synchronous streaming iterator under ASGI.

Uploads accept supported JPEG/PNG/WebP images up to 2 MiB. Replacing/removing the
file invalidates links to the old name. UserAvatar refreshes an expired/failed
capability with bounded retry. Sidebar and Profile share this behavior.

Verified-email association of guest support/consent records is routine login/
refresh work. It does not automatically confirm newsletter opt-in.

Account export, consent preferences, deactivation/deletion prerequisites, retained
financial records and operator recovery are detailed in
[Commercial operations](commercial-operations.md).

## 11. Source navigation

| Concern | Source |
| --- | --- |
| API routes | [users/urls.py](../backend/users/urls.py) |
| Login/refresh/security views | [auth_views.py](../backend/users/auth_views.py), [views.py](../backend/users/views.py) |
| Session issue/rotation | [sessions.py](../backend/users/sessions.py), [tokens.py](../backend/users/tokens.py) |
| REST / sockets | [authentication.py](../backend/users/authentication.py), [websocket.py](../backend/users/websocket.py) |
| Google state/PKCE | [google_auth.py](../backend/users/google_auth.py) |
| Admin and initial OTP | [admin.py](../backend/backend/admin.py), [enrol_staff_otp.py](../backend/users/management/commands/enrol_staff_otp.py) |
| Source OAuth | [marketdata/oauth.py](../backend/marketdata/oauth.py), [views.py](../backend/marketdata/views.py) |
| Trusted ingress | [ingress.py](../backend/backend/middleware/ingress.py) |
| Frontend request/session handling | [api.js](../frontend/src/shared/services/api.js), [useAuthSession.js](../frontend/src/shared/hooks/useAuthSession.js), [authSlice.jsx](../frontend/src/shared/store/authSlice.jsx) |
| Avatar | [avatar.py](../backend/users/avatar.py), [UserAvatar.jsx](../frontend/src/shared/components/UserAvatar.jsx) |

Follow the selected deployment guide for commands/environment. Review sign-in,
refresh, CSRF, revocation and recovery on the real gateway before accepting users.
