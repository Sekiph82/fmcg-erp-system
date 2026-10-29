# M27.S03.T001 — Hold/quarantine enforcement

## Scope and assumption

Implemented the exact `TASKS.md` task, `M27.S03.T001 — Hold/quarantine enforcement`. The task row did not link a separate acceptance document. The applicable system findings were checked against `docs/planning/GAP-017_HACCP_WORKFLOW_AUDIT.md`, `docs/planning/GAP-008_WAREHOUSE_MANAGEMENT_DEPTH_AUDIT.md`, its implementation notes, and `docs/planning/GAP-019_SHELF_LIFE_FEFO_AUDIT.md`.

Synthetic operating assumption: a quality hold/quarantine is a lot-wide disposition. Every stock row for that lot becomes unavailable across warehouses until an authorized release completes. A hold preserves existing reservations; release restores only `max(on_hand - reserved, 0)`. A passed inspection records its result but cannot clear an existing hold. Mandatory lot inspections that do not pass prevent release, active finished-goods release gates are rechecked by every release path, and dispatch checks lot disposition even when no dispatch gate is configured. Tests use synthetic records only.

## Changes

- Connected QMS lot hold/release to physical `Stock` rows and `Lot.is_quarantine`; changed stock rows receive adjustment movements with the acting user recorded.
- Preserved reserved quantities during hold and release; only the available balance changes.
- Made lot-linked non-ACCEPT QC decisions place the lot on hold even if a caller disables the legacy `apply_quarantine` flag. ACCEPT updates QC status but does not clear a held/quarantined disposition; a newly accepted unheld lot remains dispatch eligible.
- Prevented generic lot release from bypassing active mandatory finished-goods release templates, including rejection of accepted QC without production-order traceability.
- Added lot disposition checks to shipment dispatch. Gated dispatch and release lock all same-lot inspections in deterministic order before locking the lot and stock, keeping QC, release, and dispatch transactions aligned.
- Kept access checks at the existing QMS endpoints and returned HTTP 422 for blocked release attempts. No schema migration was needed.

## Verification

- `python -m compileall -q app tests/test_m27_s03_t001_hold_quarantine.py tests/test_m27_s03_t001_hold_quarantine_db.py` — passed.
- Focused QMS regression suite — 36 passed, 7 skipped. The skipped cases are guarded disposable-PostgreSQL tests, which were separately run below.
- `coordination/sessions/M27.S03.T001/run_disposable_hold_quarantine_tests.ps1` — passed on a fresh task-owned PostgreSQL 16 database after migrations through `20261029_0031`; 1 database integration test passed. It used synthetic rows, a random database/container name, loopback-only binding, no mounted volume, and no password; the script verified and removed its task-labelled container.
- `coordination/sessions/M27.S02.T004/run_disposable_dispatch_gate_tests.ps1` — dispatch regression passed on a fresh task-owned PostgreSQL 16 database after migrations through `20261029_0031`; 1 database integration test passed with synthetic data and the task-owned container removed.
- Independent read-only review identified and cleared release-gate bypass, no-gate eligibility regression, inspection/lot lock ordering, and untraceable-QC edge cases. No remaining actionable issue was reported.
- `git diff --check` — passed.

## Evidence files

- `backend/tests/test_m27_s03_t001_hold_quarantine.py`
- `backend/tests/test_m27_s03_t001_hold_quarantine_db.py`
- `backend/tests/test_m27_s02_t004_dispatch_gate.py`
- `coordination/sessions/M27.S03.T001/run_disposable_hold_quarantine_tests.ps1`
