# Local integration harness and provider adapter boundary (M43.S00.T004)

**Purpose:** develop and accept provider integrations before POVU has any real accounts (owner directive 2026-11-25). The harness tests the real adapter code against documented public contracts served locally. A simulator is a testing tool; it never counts as a live connection.

## Pieces

| Piece | Where | What it does |
|---|---|---|
| Egress guard | `backend/app/core/provider_http.py` | Every provider client is built by `provider_client()`. `PROVIDER_EGRESS` takes three values: `live` (default in production; https only), `local` (default elsewhere; only loopback, `*.localhost` and `*.test` hosts) and `off`. A blocked request raises `EgressBlocked` before anything is sent. |
| Test transport | `provider_http.set_test_transport()` | Routes provider clients through an in-process transport (for example `httpx.ASGITransport` over the simulator). The adapter code path stays unchanged. |
| Deterministic clock | `backend/app/core/clock.py` | `utcnow()` can be pinned in tests (token expiry, DST, sync windows). |
| Delegated OAuth | `backend/app/services/oauth_service.py`, `backend/app/models/oauth_connection.py`, migration `20261125_0072`, API `/api/v1/integrations/oauth/*` | Authorization code + PKCE S256, single-use 10-minute state bound to the user, exact redirect URI, granted-scope check, encrypted tokens, refresh under a row lock (handles rotating refresh tokens), Google revoke plus local wipe, audit log. Status is NOT_CONFIGURED without a client id/secret. |
| Provider keys | `backend/app/services/provider_credentials.py` | Integrations → Provider keys now also holds the Google OAuth and Microsoft Entra app credentials (encrypted). |
| Provider simulator | `backend/tests/provider_sim/` | Google and Microsoft OAuth (consent page, token, refresh, revoke, userinfo, Graph `/me`) with fault injection through `/_control`: 429 with Retry-After, 500, invalid_grant, consent refusal, dropped scopes, short expiry. Run it with `python -m tests.provider_sim --port 8765` (binds to 127.0.0.1 only). Point the ERP at it with `sim_settings()`. |
| Signed webhooks | `backend/tests/provider_sim/signing.py` | Meta `X-Hub-Signature-256` and generic HMAC-SHA256 bodies, built exactly as the ERP verifies them. |
| Mail sink | Mailpit (existing opt-in `SMTP_TEST_SERVER=127.0.0.1:<port>`) | Real SMTP delivery to a local sink, never to the internet. |
| Databases | Disposable PostgreSQL per DB test file (existing `*_DB=1` convention). Local Redis is isolated by the conftest. | Never the dev database. |

## Synthetic data rules

- Every identity the simulator issues ends in `@povu-demo.test` (a reserved TLD, so it can never deliver).
- Tokens start with `sim-`.
- Seeds must be clearly marked as synthetic and are never loaded into production.
- A simulated success must never appear as LIVE_CONNECTED, LIVE_SENT, LIVE_PAID or LIVE_PUBLISHED.

## Public contracts covered (checked 2026-11-25)

| Provider | Contract | Scopes / endpoints |
|---|---|---|
| Google OAuth 2.0 (web server flow + PKCE) | `accounts.google.com/o/oauth2/v2/auth`; `oauth2.googleapis.com/token` and `/revoke`; OpenID userinfo | Mail: `gmail.readonly` + `gmail.send` (least privilege; not `mail.google.com`). Calendar: `calendar.events`. |
| Microsoft identity platform v2.0 | `login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize` and `/token`; Graph `/me` | Mail: `Mail.ReadWrite` + `Mail.Send`. Calendar: `Calendars.ReadWrite`. Plus `offline_access` and `User.Read`. Delegated tokens have no revoke endpoint, so disconnect wipes the tokens locally and the user can also remove consent in their account. |

M43.S01 adds the Gmail API (history/messages/send), Graph mail delta, Google Calendar sync tokens and Graph events delta, and a voice-provider callback contract to the same simulator.

## Not possible without accounts (recorded in M47.S02.T002)

These cannot be done before POVU has real accounts:
- Google OAuth app verification (restricted Gmail scopes need a security assessment).
- Microsoft publisher verification and tenant admin consent.
- Production redirect URIs on a public HTTPS domain.
- Real mailbox and calendar smoke tests.

Until then, the connectors stay NOT_CONFIGURED in any real environment.

## Tests

- `backend/tests/test_m43_s00_t004_harness.py` covers:
  - the egress policy;
  - the full OAuth round trip for both providers;
  - state replay;
  - consent refusal;
  - a missing scope;
  - 429 and invalid_grant;
  - the not-configured case.
- The tests are prepared now and run at the M43 milestone gate.
