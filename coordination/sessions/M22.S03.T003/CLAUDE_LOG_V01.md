# M22.S03.T003 — Material/QC prerequisites before release

Date: 2026-11-04
Actor: CODEX
State: IMPLEMENTED; acceptance and M22 milestone verification pending.

## Scope and acceptance material

- Canonical scope: root `TASKS.md`, exact row `M22.S03.T003 — Material/QC prerequisites before release`.
- Domain boundary: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md` keeps release authority on the canonical parent `ProductionOrder`, with material and quality facts attributable to that order; it does not authorize changes to the separate `exec_*` model family.
- Existing quality behavior: `docs/planning/GAP-017_HACCP_WORKFLOW_AUDIT.md`, `backend/app/services/qms_service.py`, and the canonical `LotQualityStatus` model. Production-release QMS gates remain configuration-driven; inventory lots with an explicit non-released/held/quarantined disposition are not treated as usable material.
- Governance: `coordination/AUDIT_POLICY.md` and `coordination/AUDIT_INDEX.md`. The latest strict audit available is `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md`; it is not an M22 task verdict. No M22.S03.T003-specific prompt, acceptance matrix, or audit artifact was present.

## Implementation

- Canonical production-order release now validates every nonoptional recipe input against active material and source-warehouse availability. It converts recipe-item units to the material inventory unit, applies the existing recipe loss percentage, rounds the requirement upward to inventory precision, and aggregates repeated lines for the same material.
- Blocked stock, quarantined lots, lots expired by the order's scheduled start date, and lots with an explicit QMS hold/quarantine/non-`RELEASED` disposition do not count toward readiness. Existing configured production QMS gates remain the QC policy authority; this change does not invent mandatory inspection rules for every product or material.
- The check locks the relevant stock and existing lot-quality rows for the transaction, but does not reserve stock. Material issue continues to recheck and post actual consumption through the existing path.
- Recipe quantities follow the existing completion path, which scales each item by `actual_quantity / planned_quantity`; therefore release readiness checks the recipe quantity for the full planned order plus loss, rather than multiplying by planned output a second time.
- Added guarded disposable-PostgreSQL integration cases for shortage/rollback, exact usable quantity, blocked/quarantined/expired stock, explicit held/unreleased QMS lot dispositions, and missing source warehouse. No schema change or owner/factory data was added.

## Validation and review status

- `python -m py_compile backend/app/services/production_service.py backend/tests/test_m22_s03_t003_material_release_gate_db.py` passed.
- `git diff --check` passed.
- PostgreSQL integration tests and comprehensive tests are deferred to M22 milestone verification under the milestone-batched test policy. No test PASS or runtime/database acceptance is claimed.
- Consolidated independent M22 source review and security review remain pending at milestone acceptance.

## Synchronization and preserved work

- At task continuation, local `HEAD` and cached `origin/main` both resolved to `cc6610ea123e1d7285f0e7d4f5678925e1f70ef5`.
- The unrelated tracked owner edit `frontend/next-env.d.ts` and unrelated untracked files were not modified or staged.
- FormuLab and other checkouts were not modified.
