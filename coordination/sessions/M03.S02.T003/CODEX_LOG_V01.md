# M03.S02.T003 — Implementation Log V01

## Scope

The root task had no linked M03-specific acceptance file. Repository inspection found `Recipe` to be the M03 master model that carries both a version identifier and an effective-date window. This implementation preserves the existing product-scoped `(product_id, version)` identity and the established M20 recipe-selection rule; it does not add a numeric version format, auto-numbering, or a new approval lifecycle.

The accepted recipe-selection behavior is: only active `APPROVED` recipes are eligible; date boundaries are inclusive; null endpoints are unbounded; overlapping eligible versions resolve by latest `valid_from`, then latest `created_at`. The shared UUID tie-break only resolves records tied on those existing precedence fields. The M20 S01 T001 V06 audit is the latest applicable MPS audit; its V02 criteria/log establish the recipe-selection contract used here.

## Changes

- Added one inclusive date-window validator used by Recipe create, partial update, and duplicate flows. A supplied `valid_to` before `valid_from` returns request validation errors; the resulting partial-update window is validated against persisted values.
- Kept version identifiers opaque and case-sensitive as before, while rejecting blank/whitespace-only and over-20-character values at recipe API and CSV import boundaries.
- Added matching database check constraints and Alembic revision `20261028_0016`. The migration checks the full constraint identity before adding either constraint and reverses both on downgrade. No existing records were edited.
- Added `recipe_governance` helpers and aligned both MPS release and advanced feasibility on the accepted eligibility, precedence, and required-date fallback. With no planned start, both now use the MPS line's `period_start`.
- Added unit and task-owned PostgreSQL coverage for version/date validation, inclusive boundaries, deterministic precedence, shared date fallback, and DB enforcement of tab/newline-only versions and reversed windows.

## Verification

- Fresh PostgreSQL 18 `alembic upgrade head` — passed at `20261028_0016`.
- `alembic downgrade 20261027_0015` followed by `alembic upgrade head` — both passed.
- `python -m pytest -q tests/test_m03_recipe_version_effective_dates.py` against the task-owned loopback PostgreSQL database — **10 passed**.
- `python -m pytest -q tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py -k 'select_release_recipe'` — **2 passed, 20 deselected**.
- Python compile check for all changed Python source/test/migration files — passed.
- `git diff --check` — passed.
- Independent read-only review initially identified the mismatched MPS date fallback and incomplete CSV/database whitespace handling. Both were corrected, then independently re-reviewed with no remaining finding reported. The reviewer did not run tests.
- An initial PostgreSQL attempt used a process that had loaded the earlier whitespace constraint before the correction and correctly failed the new tab/newline assertion. A fresh disposable database initialized from the final source passed the complete migration and focused verification above.
- The disposable PostgreSQL 18 container/database was removed after verification. Its generated password remained local and was not recorded in this log or sent to the owner.

## Limits

No production or owner database was accessed. No owner data was fabricated or changed. No GitHub Actions, external audit, deployment, production-readiness claim, or owner acceptance was performed.
