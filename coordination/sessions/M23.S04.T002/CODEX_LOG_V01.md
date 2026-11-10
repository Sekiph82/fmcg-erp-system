# M23.S04.T002 — Operator UI/E2E tests

## Scope and acceptance basis

- Canonical task authority: root `TASKS.md`, task `M23.S04.T002`.
- M23.S03.T002 sets the Shop Floor to online-only authoritative operation; after connectivity returns, current server state must be refreshed before writes resume.
- M23.S03.T003 requires unchanged retries to reuse the same idempotency key. M23.S04 is the consolidated acceptance checkpoint.

## Implemented

- Added mocked Playwright scenarios for offline write blocking and explicit refresh after reconnecting.
- Added a temporary-server-error scenario that refreshes state and verifies an unchanged retry reuses the original request key.
- Added a lost-response scenario in which the mocked server persists the downtime record before the response is interrupted; the UI must refresh and reveal the saved record before another submission is enabled.
- Scenarios use synthetic identities/data and a loopback-only test cookie. They do not call a live ERP service.

## Verification and limits

- Targeted ESLint passed for the new Playwright spec and changed Shop Floor frontend files.
- `git diff --check` passed for the task files.
- The Playwright scenarios were authored but not run yet; M23.S04 comprehensive UI/E2E validation is intentionally batched after the remaining milestone test work is assembled.
- No physical-device, live-network, live-factory, or production acceptance is claimed.
