# M23.S02.T001 — Actual quantity/time capture

## Implementation status

Implemented locally; milestone acceptance and consolidated test/review batch remain pending.

## Scope and acceptance basis

- Root `TASKS.md` task: `M23.S02.T001 — Actual quantity/time capture`.
- Shop Floor manual: `docs/user-manual/module-manuals/manufacturing/08-shop-floor.md`.
- Existing execution model stores actual setup/run/cleanup duration in minutes. This implementation captures optional actual run time in minutes and preserves unknown values as unset; it does not invent runtime data.
- Existing M23.S01.T002 evidence defines completion quantity validation and the shop-floor finish workflow. The M22 boundary remains separate `exec_*` execution records without inferred crosswalks.

## Changes

- Added an optional actual run-time input to the Shop Floor terminal finish action; only the finish request sends it, and the value is cleared after a successful finish.
- The finish service validates supplied quantities and runtime as finite, nonnegative values, persists actual good/scrap/rework quantities and optional runtime, captures completion time, and writes runtime minutes to the FINISH activity record.
- Updated the shop-floor manual to state that timestamps are system captured and unknown runtime remains unset.
- Added `backend/tests/test_m23_s02_t001_actual_quantity_time.py` to cover service persistence and activity logging. It is intentionally deferred to the M23.S04 consolidated test batch.

## Verification performed

- `python -m py_compile backend/app/services/shop_floor_service.py backend/tests/test_m23_s02_t001_actual_quantity_time.py` — PASS.
- `frontend/node_modules/.bin/eslint.cmd src/app/dashboard/shop-floor/terminal/page.tsx` — PASS.
- `git diff --check` — PASS (Git printed existing LF-to-CRLF working-copy notices for multiple files).
- No pytest, full suite, database migration, frontend typecheck, independent review, or live-site/factory acceptance is claimed here; tests and consolidated review are scheduled for M23.S04.

## Review notes

A static inspection caught the runtime activity argument initially attached to the quantity-update path. It was moved to the FINISH activity call before this status was recorded; the final static checks above passed after correction.
