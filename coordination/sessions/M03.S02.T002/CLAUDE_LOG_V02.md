# M03.S02.T002 Implementation Log V02

Status: `AWAITING_AUDIT`

Date: 2026-10-28

## Revision basis

- Follow-up to implementation commit `45358929663f3f4e93fb37299768479032dbd577` and evidence in `CLAUDE_LOG_V01.md`.
- Independent read-only review found two defects: default warehouse listing referenced an ORM relationship that does not exist; and the database's named inactive-master constraint surfaced as an HTTP 500.
- Both findings were corrected in commit `8b4df655ff7ab7aa8330df97856b0d8ae883d50b`.

## Corrections

- Replaced the invalid `Warehouse.company` relationship lookup with a correlated active-company query. Added a PostgreSQL-backed regression test that executes the default warehouse list, verifies a branch-scoped warehouse disappears after branch deactivation, verifies a company-scoped warehouse disappears after company deactivation, and verifies both remain available with `include_inactive=True`.
- Added an exception handler for the exact database constraint `ck_active_master_reference`. That specific violation now returns HTTP 409 with `inactive_master_reference`; unrelated integrity errors continue through the generic HTTP 500 handler. A test invokes an API route with the named constraint and checks the 409 payload, while a separate test confirms unrelated constraints still return 500. The PostgreSQL integration test also confirms the actual driver error exposes the expected constraint name.
- Added an autouse test fixture to dispose the async SQLAlchemy engine after each test, avoiding connection-pool reuse across pytest's per-test event loops.

## Checks and results

- Disposable PostgreSQL 18 on loopback, database `fmcg_m03_t002_20261028abcdef0123456789`, created specifically for this revision; no password was configured or exposed.
- Fresh `venv\Scripts\python.exe -m alembic upgrade head` — PASS through `20261027_0015`.
- With `M03_DISPOSABLE_TEST_DATABASE=1` and the exact matching disposable database name: `venv\Scripts\python.exe -m pytest -q tests/test_m03_master_lifecycle.py tests/test_gap025_multi_company_branch.py` — PASS, 27 passed.
- `venv\Scripts\python.exe -m compileall -q app/core/exception_handlers.py app/crud/master.py tests/test_m03_master_lifecycle.py` — PASS.
- `git diff --check` — PASS; `node scripts/codex/validate-task-state.mjs` and `node scripts/codex/task-queue.mjs --check` — PASS. Task remains `IN_PROGRESS` and current; no successor selected.
- A first run of the newly added warehouse test exposed a test-only async connection-pool/event-loop reuse issue. The fixture now disposes the engine after every test; the full targeted rerun passed.

## Handoff

- Results are implementer-run evidence only; this log assigns no independent audit verdict.
- Re-review the original changes plus this correction commit. Do not close the task or start a successor until the correction is independently reviewed. No GitHub Actions were run; both commits use `[skip ci]`.
