# M31.S04.T003 — Failure/replay/idempotency tests

## Scope and implementation

Added a guarded PostgreSQL integration regression that exercises one synthetic event end to end:

- repeated publish with the same event-scoped idempotency key returns the original event and does not queue a second initial delivery;
- changed payload with the same key is rejected as an idempotency conflict;
- a failed loopback-only delivery moves to retry, retry exhaustion records a dead-letter child without rewriting its parent, and replay creates one linked pending child;
- repeating the replay while that child is pending creates no duplicate attempt.

The test is opt-in only for a task-named loopback PostgreSQL database. Its endpoint is `127.0.0.1:1`; no external service is contacted. The PowerShell runner starts a uniquely named `postgres:16-alpine` container on a random loopback port, migrates only its task-owned database, verifies Alembic head `20261030_0004`, restores the process environment, validates task labels, then stops/removes that container.

## Verification

- Focused M31.S03/S04 unit regression run, including the new database-guard test: **57 passed, 1 disposable-database test skipped, 68 existing deprecation warnings**.
- Task-owned disposable PostgreSQL runner: **2 passed** (database isolation guard and end-to-end publish/failure/retry/dead-letter/replay); Alembic `20261030_0004 (head)`; runner reported `RESULT=PASS` and removed the task container.
- Python byte-compilation and `git diff --check`: passed.

The first disposable run exposed a too-specific assertion: the OS surfaced the expected closed-loopback-port failure as `ConnectTimeout` instead of `ConnectError`. The test now accepts either transport-level connection failure class while requiring the delivery state and safe persisted error behavior. The rerun passed.

## Independent review

Read-only reviewer confirmed the exact database-name/loopback/driver guard, task-labeled loopback-only container and scoped cleanup, no external request target, migration-head verification, synthetic record cleanup, and assertions for idempotent publication, payload conflict, retry/dead-letter lineage, and duplicate replay prevention. No remaining gap was reported. Reviewer made no edits and ran no tests.
