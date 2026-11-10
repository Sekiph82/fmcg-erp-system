# M24.S04.T003 — Reversal/correction controls

## Scope and starting state

- Canonical workspace and acceptance authority: `C:\Users\sekip\Desktop\fmcg-erp-system`, root `TASKS.md`.
- Acceptance material: `coordination/milestones/M24/EXECUTION_PLAN_V01.md`, T003 section added during this task.
- Applicable audit: `docs/planning/GAP-002_POSTING_INTEGRATION_AUDIT.md`; review policy: `coordination/AUDIT_POLICY.md`.
- Starting `HEAD`: `0db8dc68c971661dbda55f6992f3b4e70e4da84d`.
- Starting `origin/main`: `0db8dc68c971661dbda55f6992f3b4e70e4da84d` (0 ahead / 0 behind).
- The checkout already contained extensive unrelated local changes and task/evidence files. They were preserved; no reset, clean, stash, commit, push, or force-push was performed.

## Implementation

- Generic `REVERSAL` drafts are rejected by the transaction API and service. Generic reversal drafts also cannot be confirmed through the API or service.
- The generic reverse endpoint checks transaction warehouse scope and then returns HTTP 409. The service refuses posted reversals without creating an inverse-looking transaction or changing the source status.
- Existing exact issue-line return and scrap flows retain their own rules. Unsupported WIP and finished-goods corrections remain blocked; no quantity, financial value, inventory event, genealogy edge, physical activity, or approval was invented.
- Added a guarded disposable-PostgreSQL test for exact loopback, passwordless database identity and for the service-level fail-closed behavior, source status preservation, and absence of a reversal row.
- No schema or migration change was needed.

## Changed files for this task

- `backend/app/api/v1/endpoints/material_flow.py`
- `backend/app/services/material_flow_service.py`
- `backend/tests/test_m24_s04_t003_reversal_guards_db.py` (new; not run)
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`
- `coordination/sessions/M24.S04.T003/CODEX_LOG_V01.md` (this file)

## Checks and review

- `python -m py_compile backend/app/api/v1/endpoints/material_flow.py backend/app/services/material_flow_service.py backend/tests/test_m24_s04_t003_reversal_guards_db.py` — passed.
- `python -m ruff check backend/app/api/v1/endpoints/material_flow.py backend/app/services/material_flow_service.py backend/tests/test_m24_s04_t003_reversal_guards_db.py` — passed.
- `git diff --check` — passed; Git printed existing LF/CRLF notices for other dirty files.
- Disposable PostgreSQL, API, frontend, migration, and full M24 regression tests — not run; consolidated acceptance is deferred to M24.S04.T004.
- Independent read-only review — no remaining generic reversal create/confirm/reverse bypass found; source preservation and reverse-route warehouse-scope ordering were verified.
- No owner decision is required to refuse unsupported corrections safely. Full M24 milestone acceptance and consolidated security review remain pending.

## Publication and tracker

- No commit or push was made. Local task and owner changes remain preserved.
- Root `TASKS.md` was read and updated only through `scripts/codex/task-queue.mjs`; it was not edited directly.
