# M31.S01.T004 — Partner audit/usage analytics

## Implementation

- API application create/update, API-key create/rotate/revoke, and OAuth client-secret create/rotate/revoke now append a scoped event to the existing audit log in the same database transaction as the credential change.
- Audit event detail contains only identifiers and policy metadata; it excludes raw keys, raw OAuth secrets, hashes, and request IP addresses. The developer audit endpoint requires `integrations.view`, filters to the current actor and allowlisted partner event types, and caps results at 200.
- Usage analytics summarize existing usage-log records for the authenticated user's keys over a requested 1–90 day window (30-day default), with UTC day counts, success/error/unclassified counts, and average response time. Future-dated rows are excluded. IP addresses are not returned.
- Developer Portal shows the recent partner credential audit and usage summary. Both API and UI state that automatic request capture is disabled while API-key authentication is not enabled; synthetic test rows are not presented as real traffic.
- No database migration was needed; the existing `audit_logs` and `dev_api_key_usage_logs` tables are used.

## Verification

- Task-owned disposable PostgreSQL runner: `run_partner_analytics_tests.ps1`.
- PostgreSQL image: `postgres:16-alpine`, image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`.
- Database/container suffix: `b2fdd64a4b634ea58d58`; task-prefixed random database, loopback-only port, no volume, no password, synthetic fixtures only. Migration head `20261029_0043` was verified and the task-labeled container was removed.
- Integration result: 2 passed, 72 existing project/dependency warnings. A first run caught a missing `UUID` import in the new test; after correction and future-date coverage, the disposable run passed.
- M31.S01.T003 scope/rate regression suite rerun against its own disposable PostgreSQL database after lifecycle audit integration: 2 passed, 75 existing project/dependency warnings.
- Backend Python syntax compilation passed.
- Frontend TypeScript `--noEmit` and targeted ESLint passed.
- `git diff --check` passed.
- Independent read-only reviewer confirmed the future-date guard is applied to daily, aggregate, and per-key usage queries; no blockers remain.

## Scope boundary

The analytics report stored rows only. This task does not enable API-key authentication, collect external requests, enforce per-key quotas, or fabricate traffic.
