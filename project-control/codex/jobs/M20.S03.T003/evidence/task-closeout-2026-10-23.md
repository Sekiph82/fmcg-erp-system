# M20.S03.T003 task closeout

Date: 2026-10-23
Task: Validate changeover/CIP effects where data exists
Repository: `Sekiph82/fmcg-erp-system`, `main`

## Implemented

- Capacity scheduling now re-evaluates campaign transitions against the current active `changeover_matrix` rows instead of using a stale campaign grouping snapshot.
- A unique, non-negative configured transition is allocated once to the successor campaign's first scheduled day and included in finite-capacity slot and overload calculations.
- Missing transitions, ambiguous/negative setup rows, invalid campaign chains, and missing setup calendars remain explicit diagnostics; no default duration is applied.
- Work-center/member mismatches and inactive work centers cannot silently bridge a sequence or accrue setup load.
- CIP applicability and duration remain `NOT_CONFIGURED` because the repository has no authoritative MPS CIP duration source. No CIP value was invented.
- Campaign setup does not mutate the stored `total_changeover_hrs` snapshot or production required-hours value.

## Verification evidence

- `python -m py_compile backend/app/services/mps_capacity_service.py backend/tests/test_m20_v03_acceptance.py` — passed.
- `git diff --check` — passed.
- Focused disposable-PostgreSQL capacity acceptance case — `1 passed`.
- Full `backend/tests/test_m20_v03_acceptance.py` against a disposable PostgreSQL 16 database with `M20_DISPOSABLE_TEST_DATABASE=1` — `14 passed, 67 warnings`.
- The PostgreSQL database/container and credentials were disposable test resources; no owner or production data was used.
- Independent read-only review reported no remaining concrete findings in the T003 diff after mismatch and inactive-work-center regressions were added.

## Acceptance boundary

Configured changeover behavior is covered by local synthetic PostgreSQL tests. Real plant changeover/CIP policy and durations remain owner-data dependent; CIP is explicitly unknown. GitHub Actions and remote CI were not run due to the M20 quota restriction through 2026-10-30. This task closeout is implementation evidence, not milestone or external audit acceptance.
