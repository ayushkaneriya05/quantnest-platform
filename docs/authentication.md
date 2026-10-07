# Authentication and browser sessions

## Login and reload

1. The frontend requests a CSRF token from `GET /api/v1/users/auth/csrf/`.
2. Password login, Google login and registration use a common session service. If two-factor authentication is enabled, login returns a signed, single-use challenge instead of JWTs.
3. The server identifies the browser profile using the HttpOnly `quantnest-device` cookie. A repeat login from that browser replaces its refresh token and reuses its active session; another browser profile or incognito window has a separate session.
4. Access tokens last 15 minutes and stay in Redux memory. Refresh tokens stay in the secure HttpOnly `quantnest-refresh-session` cookie, scoped to `/api/v1/users/`. The distinct name prevents older root-scoped cookies from overriding the current token. The response contains the access token, user and CSRF token, never the refresh token. Profile image URLs are absolute in login and profile responses.
5. On reload the frontend rotates the refresh cookie and loads the profile before rendering protected pages. CSRF bootstrap reports whether that cookie is present, so signed-out visits skip an unnecessary refresh request. It refreshes access before expiry and when a tab resumes. Concurrent requests share a refresh operation; Web Locks serialize authentication cookie changes across browser tabs.

Only non-secret login/logout events are written to localStorage. Browser tabs recover the current cookie session when they receive a login event; a logout event clears authentication in the other tabs. Responses started under previous authentication cannot restore it or replace the current user's data.

## Google sign-in redirect

1. The button calls `POST /api/v1/users/auth/google/start/` with a local return path. Django generates a random state and PKCE verifier, stores them in a signed HttpOnly cookie for five minutes, and returns the Google authorization URL. The browser opens that URL in the same tab.
2. Google redirects to `GET /api/v1/users/auth/google/callback/`. Django verifies the browser's state cookie, consumes the state once, and exchanges the code using the PKCE verifier and the backend client secret. Existing Google accounts are looked up through allauth; new accounts receive an unusable password and Google's verified email. Existing password accounts are not automatically linked by email.
3. The callback creates a signed, five-minute, one-use result cookie and redirects to the frontend's `/google-callback` page. No Google or QuantNest tokens are put in the frontend URL. The callback does not create a Django authentication session or issue JWTs.
4. The frontend calls the CSRF-protected `POST /api/v1/users/auth/google/complete/`. The result cookie is consumed and the shared login service issues session cookies and an access token, or requires local two-factor verification. Inactive accounts and password changes invalidate the pending login. Cancellation, expired state and provider failures show a useful error on the callback page.

Configure the Google **Social application** in Django admin with the web client's ID and secret, and associate it with the configured Django Site. Frontend Google credentials and the Google popup SDK are no longer used.

Using browser Back before selecting an account returns to an enabled sign-in button and leaves the user signed out. The shared button resets its loading state on a cached `pageshow` restoration. Retrying starts a fresh OAuth flow; the previous state cookie is replaced.

In Google Cloud Console, add this development URI under **Authorized redirect URIs**:

```text
http://localhost:8000/api/v1/users/auth/google/callback/
```

For deployment, use `BACKEND_URL` plus `/api/v1/users/auth/google/callback/`; it must exactly match Google's registered URI. `FRONTEND_URL` specifies the QuantNest page to return to. Both must use HTTPS in production. The state and result cookies use `SameSite=Lax`, allowing Google's top-level callback navigation; frontend and API domains must support the application's existing cookie authentication configuration.

See [Google's authorization-code flow](https://developers.google.com/identity/protocols/oauth2/web-server).

## Rotation, revocation and security settings

- Every REST request validates token signature, expiry, active user, password hash and ownership of a nonexpired session. Refresh also validates the exact current refresh JTI under a database lock, blacklists the old token and updates the existing record. It never creates a session.
- Refresh expiry is seven days from the latest rotation. Browser metadata is descriptive; IP address or user agent is not used as device identity. `last_activity` updates on login, refresh, WebSocket connection and authenticated API activity, with API writes limited to once per minute.
- Logout deletes the owned session, blacklists its current refresh token and clears JWT cookies. Ending other sessions uses the authenticated access token's session ID to preserve the current session.
- Changing a password requires the current password, revokes other sessions, rotates the current credentials and reconnects its streams. Password reset revokes all sessions and requires fresh login. Account deactivation/deletion also revokes all sessions.
- Two-factor challenges expire after five minutes, are single use and are bound to the user's password. TOTP and backup codes cannot be reused. Setting up two-factor authentication never deletes an already confirmed device. Security actions are throttled.
- Authentication cookie actions require CSRF validation. Production cookies require HTTPS. WebSockets use HttpOnly access cookies and an allowed frontend Origin, enforce the same authentication checks as REST, close on expiry and receive revocations after database commit. JWTs are not included in WebSocket URLs.
- Expired sessions are hidden and pruned on session listing/login. The daily `users.cleanup_expired_sessions` Celery task removes remaining expired records and SimpleJWT token history.
- Network/server failures during refresh retain the current authentication for retry. Invalid authentication ends it. Failed logout keeps the user signed in and shows an error so the server session can be ended on retry.

Email verification follows `ACCOUNT_EMAIL_VERIFICATION` (currently optional). Optional verification preserves the registration session; mandatory verification requires verification and subsequent login.

## Migration and checks

`users.0006_browser_sessions` expires old session records because they have neither a browser identity nor refresh-token ownership. All users must sign in once after this migration. It does not modify account, strategy, broker or trading data.

Run backend verification in the isolated SQLite settings:

```powershell
rtk proxy .venv\Scripts\python.exe backend/manage.py test users research --settings=users.test_settings --noinput
rtk proxy .venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run --settings=users.test_settings
```

Run frontend authentication checks from `frontend/`:

```powershell
rtk proxy node --test tests/auth-session.test.mjs
rtk proxy node --test tests/ui-regressions.test.mjs
rtk proxy npm run build
```

The UI checks use an isolated headless Chrome profile. Set `CHROME_PATH` if the browser is installed outside the standard locations; these checks skip if no supported browser is installed.

References: [OWASP token storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html), [SimpleJWT settings](https://django-rest-framework-simplejwt.readthedocs.io/en/stable/settings.html), [dj-rest-auth settings](https://dj-rest-auth.readthedocs.io/en/latest/configuration.html).
