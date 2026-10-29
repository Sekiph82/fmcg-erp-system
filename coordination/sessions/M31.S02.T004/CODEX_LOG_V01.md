# M31.S02.T004 — Transactional event creation/outbox strategy

Date: 2026-10-30
Workspace: `C:\Users\sekip\Desktop\fmcg-erp-system`
Task authority: root `TASKS.md`, M31.S02.T004

## Scope and strategy

- Reviewed the T004 tracker row, the webhook/event-engine production risks in `docs/planning/GAP-006_REAL_INTEGRATIONS_AUDIT.md`, and the canonical contract in `docs/planning/M31_DOMAIN_EVENT_ENVELOPE.md`. The tracker has no separate T004 acceptance document.
- The existing `webhook_event_logs` row and matching `webhook_delivery_attempts` rows are the durable outbox record; no duplicate outbox table is introduced.
- Added `stage_event()`, which validates, idempotently inserts the event and queues matching pending deliveries in the caller's current database transaction, flushes, and does not commit. Domain services can call it alongside their business writes and commit once. A rollback removes all writes together.
- Preserved `publish_event()` as a standalone wrapper that stages the event/outbox and commits them together. The inbound webhook endpoint now stages the event, updates its receive counter, and commits once, so the event, pending deliveries, and endpoint state are atomic.
- Outbox persistence does not claim exactly-once external delivery. Dispatch and retry behavior remain governed by the separate M31 delivery-engine tasks. A business service that uses request idempotency must check a replay result before applying a duplicate business mutation.

## Verification

- Focused T001/T002/T003 regression and T004 unit suite: **22 passed**.
- T004 disposable PostgreSQL/API suite: **2 passed**. It verified inbound event/counter/outbox commit, same-key replay without a second delivery, mismatched-key conflict without counter mutation, and explicit transaction rollback removing business-state, event, and delivery writes. The runner used a uniquely named loopback-only PostgreSQL database (`postgres:16-alpine`, image `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`) and removed its task-owned container.
- Python byte-compilation passed. The single Alembic head remains `20261030_0002`; T004 requires no schema migration. `git diff --check` passed.
- Independent read-only review found no remaining blockers. The reviewer did not run tests.
- Test output included 69 existing Pydantic/FastAPI deprecation warnings from the application; they are unrelated to this task.
