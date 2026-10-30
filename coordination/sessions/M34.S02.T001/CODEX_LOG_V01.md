# M34.S02.T001 — Blanket agreement governance

## Scope and decisions

- Hardened the existing blanket purchase agreement records and procurement permissions; no parallel contract subsystem or new approval threshold was introduced.
- Active agreements may be edited only within the existing scoped edit permission. Cancellation uses the separate cancel permission and must be submitted without piggybacked edits.
- Commercial terms and procurement scope are locked after consumption begins, including payment terms. Fully consumed, expired, or cancelled agreements are immutable through this endpoint.
- Future-dated agreements remain visible as scheduled, but are excluded from the current active filter, active count, and bounded active value.
- A nullable `valid_to` patch is rejected by schema validation; prices, quantities, currency, and validity dates receive input validation.
- BPA create/update/cancel changes are recorded in the existing audit log with before/after changed values.

## Changes

- Added BPA schema validation and computed expiry/scheduled indicators.
- Hardened BPA create/list/update API lifecycle and permission behavior, including commercial-term locking and audit events.
- Updated the blanket-agreements page to use distinct edit/cancel access hints, correctly label scheduled agreements, and exclude them from current active metrics.
- Added endpoint/database regression coverage and a task-scoped disposable PostgreSQL runner. The runner refuses to overwrite prior evidence files and always removes its uniquely named container.

## Verification

- `run_disposable_postgres.ps1 -RunVersion V05`: passwordless PostgreSQL 16 bound only to loopback, unique task-owned database/container, full Alembic upgrade to `20261030_0008 (head)`, focused endpoint/schema tests, and cleanup. Result: **3 passed**; container cleanup verified absent.
- Focused related regression suite `python -m pytest tests/test_gap009_procurement_maturity.py tests/test_m34_s02_t001_bpa_governance.py -q`: **8 passed, 1 skipped**. The skip remains a skip; it is not counted as a pass.
- `python -m compileall -q app/api/v1/endpoints/procurement.py app/schemas/procurement.py app/models/audit_log.py tests/test_m34_s02_t001_bpa_governance.py`: passed.
- Frontend `npm run type-check`: passed.
- Targeted `npx eslint src/app/dashboard/procurement/blanket-agreements/page.tsx src/lib/procurement.ts`: passed.
- `git diff --check` and PowerShell parser validation for the disposable runner: passed.
- Independent read-only review identified and verified fixes for cancellation/edit permission separation, mixed cancellation-plus-edit requests, post-consumption payment-term changes, explicit `valid_to: null`, future-start agreements in active metrics, and evidence overwrite protection. Final follow-up review found no remaining actionable findings and ran no tests or Actions.

## Iteration history and evidence

- V01 failed because the synthetic audit actor was not persisted before writing audit rows; the fixture now persists the actor.
- V02 failed because direct endpoint invocation used FastAPI's `Query` default instead of an explicit limit; the test now supplies the actual limit.
- V03 passed the initial database flow. V04 passed after the lifecycle/permissions/date corrections. V05 is the final run after the final review finding was fixed.
- `disposable-postgres-command-output-V01.log` through `...-V05.log` are the committed command-output evidence. Matching local PowerShell transcripts remain available in the checkout; raw transcripts were left uncommitted rather than normalizing their captured trailing whitespace.

## Source fingerprints at final verification

SHA-256:

- `backend/app/api/v1/endpoints/procurement.py`: `7ad87b5ceb12106f9788e96acd4df94359e3d463956b5c57c74f046617deeb0cb`
- `backend/app/schemas/procurement.py`: `dc5bf3221f5ee7b0a6aadf0c2fc14bd53f3c1772ace17784a13b7429b0982e6e`
- `backend/app/models/audit_log.py`: `6f696e5ab04e08d64b2172b295d0745299ce1349b593892a4b3e643c5c12d9e3`
- `backend/tests/test_m34_s02_t001_bpa_governance.py`: `c987eb6a6a25c855be26a8ad55d8e5e86c0e9058a324ad5b8d6f6e915c8d5b2`
- `frontend/src/app/dashboard/procurement/blanket-agreements/page.tsx`: `09e974a9ec6d47fe4e8dc9eea311c60d0567a8eb4dd26e4d7e826a6a39a4936`
- `frontend/src/lib/procurement.ts`: `4d855135e2caf22d4f7c7de637b6301ae47d4f519741b6e33dde7429b0982e6e`
- `coordination/sessions/M34.S02.T001/run_disposable_postgres.ps1`: `9acad52e837d269a177c99fbac343a2868a2e9d5fd79822edc0d5a5554e72a16`
