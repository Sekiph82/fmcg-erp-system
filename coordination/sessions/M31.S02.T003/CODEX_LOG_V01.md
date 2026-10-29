# M31.S02.T003 — Idempotency/correlation/causation IDs

Date: 2026-10-30
Workspace: `C:\Users\sekip\Desktop\fmcg-erp-system`
Task authority: root `TASKS.md`, M31.S02.T003

## Scope and policy

- Reviewed the T003 tracker row, the webhook/event-engine risks in `docs/planning/GAP-006_REAL_INTEGRATIONS_AUDIT.md`, and the canonical contract at `docs/planning/M31_DOMAIN_EVENT_ENVELOPE.md`. The tracker has no separate T003 acceptance document.
- Event publishers may supply an optional idempotency key. The key is trimmed, limited to 255 characters, and unique per event type. A SHA-256 fingerprint of the canonical request fields distinguishes a retry from reuse of the same key for different request content.
- Repeating the same event type, key, and request returns the original event and queues no additional delivery. Reusing the key for changed content returns HTTP 409. PostgreSQL `ON CONFLICT DO NOTHING` arbitrates concurrent first uses without rolling back unrelated state in the caller's session.
- Optional correlation and causation identifiers are trimmed, limited to 200 characters, and stored in the canonical event envelope. Historic event reads normalize missing values to JSON `null`. Inbound webhook requests may carry these values through `X-Correlation-ID` and `X-Causation-ID`, and may deduplicate through `Idempotency-Key`.
- The key scope is event type within the current event engine; no tenant/client scope or exactly-once external-delivery guarantee is introduced. Outbox atomicity remains M31.S02.T004.

## Implementation

- Added nullable idempotency key/fingerprint fields, a per-event-type unique constraint, and a paired-nullability check, with an upgrade/downgrade migration that adopts the current squashed baseline and also adds missing fields on older databases.
- Extended request validation, service publication, canonical envelope normalization, public publish API status/header behavior, and inbound header propagation.
- Added unit and isolated PostgreSQL coverage for identifier bounds, deterministic fingerprints, schema constraints, duplicate returns, payload conflicts, API replay response, delivery deduplication, concurrent same-key publication, and migration downgrade/re-upgrade.
- Updated `docs/planning/M31_DOMAIN_EVENT_ENVELOPE.md` and preserved the prior T001 contract test for the expanded nullable envelope fields.

## Verification

- Focused T001/T002 regression plus T003 unit suite: **21 passed**.
- T003 disposable PostgreSQL suite: **3 passed**, including API replay/conflict checks and concurrent publication. It used `postgres:16-alpine` image `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`, a uniquely named loopback-only database, and a migration downgrade to `20261030_0001` followed by upgrade to `20261030_0002`. The task-owned container was removed by the runner.
- Python byte-compilation passed for changed backend, migration, and test files. Alembic reports one head, `20261030_0002`. `git diff --check` passed.
- Independent read-only review found and helped identify a race-path session rollback hazard. The implementation now uses a targeted PostgreSQL conflict insert; the reviewer rechecked it and reported no remaining blockers. The reviewer did not run tests.
- Test output included 69 existing Pydantic/FastAPI deprecation warnings from the application; they are unrelated to this task.
