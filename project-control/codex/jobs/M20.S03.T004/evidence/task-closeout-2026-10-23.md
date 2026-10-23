# M20.S03.T004 task closeout

Date: 2026-10-23
Task: Persist capacity overload diagnostics
Repository: `Sekiph82/fmcg-erp-system`, `main`

## Implemented

- Finite-capacity evaluations persist per-line diagnostics with run/source version, evaluation kind, mode, recalculation state, and explicit base-plan scenario provenance.
- Capacity issue snapshots include stable slot identity, work center/date, per-line and aggregate required hours, available/net available hours, downtime, line-attributed overload, and the complete affected-line list.
- Recalculation marks prior current diagnostics as `SUPERSEDED` and links them to the replacing run. Empty-plan and finite/infinite transitions also keep persisted state consistent; infinite mode marks capacity diagnostics `NOT_APPLICABLE`.
- The API schemas and TypeScript types expose the persisted diagnostic fields. The MPS constraints page can trigger recalculation and displays run/state/slot/affected-line context.
- Acceptance coverage verifies persistence, API schema compatibility, idempotent slot values after recomputation, supersession linkage, and finite→infinite→finite state transitions using synthetic data.

## Verification evidence

- `python -m py_compile backend/app/services/mps_advanced_service.py backend/app/services/mps_capacity_service.py backend/app/schemas/mps.py backend/tests/test_m20_v03_acceptance.py` — passed.
- `pnpm --dir frontend type-check` — passed.
- `git diff --check` — passed.
- Full `backend/tests/test_m20_v03_acceptance.py` against a disposable PostgreSQL 16 database with `M20_DISPOSABLE_TEST_DATABASE=1` — `14 passed, 69 warnings`.
- The database/container and credentials were disposable local test resources; no owner or production data was used. The test process exited successfully and cleanup completed.
- Independent read-only review reported no remaining concrete findings in the T004 diff.

## Acceptance boundary

Synthetic local PostgreSQL acceptance, Python compilation, and frontend type-check passed. Existing Pydantic/FastAPI deprecation and namespace warnings remain in the suite output. GitHub Actions and remote CI were not run due to the M20 quota restriction through 2026-10-30. This closeout records implementation evidence; it does not claim milestone approval or external audit acceptance.
