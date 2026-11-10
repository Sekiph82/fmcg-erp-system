# M24.S01.T004 — FEFO/lot recommendation enforcement

**State:** implemented; pending M24 milestone validation and consolidated review.  
**Acceptance material:** no task-specific acceptance file is present; root `TASKS.md` and the M24 interpretation in `coordination/milestones/M24/EXECUTION_PLAN_V01.md` define the scope.  
**Applicable audit:** `coordination/AUDIT_INDEX.md` ERP-AL-004/010/011/012/013, `coordination/AUDIT_POLICY.md` critical inventory, direct-observability, migration, and cross-module rules, plus `docs/planning/GAP-019_SHELF_LIFE_FEFO_AUDIT.md`. GAP-019 records that WMS product-pick enforcement is deferred pending WMS endpoint coordination; this task enforces FEFO in the separate production-material reservation flow and does not claim WMS shipment-pick enforcement.

## Starting synchronization and preserved work

- Verified canonical repository root: `C:\Users\sekip\Desktop\fmcg-erp-system`.
- Fetched `origin/main`; local `HEAD` and `origin/main` were both `0db8dc68c971661dbda55f6992f3b4e70e4da84d`, ahead/behind `0/0`.
- The worktree already contained unrelated owner/project changes. They were preserved and not staged, reset, cleaned, stashed, or overwritten.
- Root `TASKS.md` was read and not manually edited by this implementation.

## Implementation

- Production material reservation candidates now use FEFO order: earliest eligible expiry first; lots without expiry after dated lots; untracked stock last. Equal expiry is ordered deterministically by manufacture date, lot number, then stock-row ID.
- Expired, quarantined, held, non-released, explicitly non-FEFO-eligible, blocked, or unavailable stock cannot be recommended or allocated. A missing lot-quality release record is treated as ineligible.
- A fixed-lot request must identify an eligible lot, have enough available quantity, and match the first eligible FEFO recommendation. A non-FEFO fixed request returns the recommended lot identity without mutating stock. A non-fixed lot hint does not override the computed FEFO allocation.
- The existing `fefo_lot_candidate` reservation field records the computed recommendation for downstream display and traceability. The generated list continues to use reservation allocations as its source of truth.
- This does not change WMS product/shipment picking or claim physical execution; those remain outside M24.S01.T004.
- Extended the disposable PostgreSQL suite with synthetic released/unreleased, expired, dated, and non-expiring lots, FEFO allocation order, fixed non-FEFO rejection, recommendation identity, and no-mutation assertions.

## Checks performed

- `python -m py_compile app/services/material_flow_service.py tests/test_m24_s01_t001_material_reservation_db.py`: passed.
- `python -m ruff check tests/test_m24_s01_t001_material_reservation_db.py`: passed.
- SQLAlchemy `configure_mappers()` smoke check for material-flow, WMS, and quality models: passed.
- `python -m alembic heads`: one head, `20261108_0013`.
- `git diff --check`: exited 0. Git emitted pre-existing CRLF normalization warnings for unrelated changed files; no whitespace error was reported. The new M24 test file was separately scanned for trailing whitespace and had none.
- PostgreSQL tests, migration application, API tests, and E2E tests were not run; they remain in the consolidated M24 acceptance campaign. No test PASS is claimed.

## Changed files for this task

- `backend/app/services/material_flow_service.py`
- `backend/tests/test_m24_s01_t001_material_reservation_db.py`
- `coordination/milestones/M24/EXECUTION_PLAN_V01.md`
- `coordination/sessions/M24.S01.T004/CODEX_LOG_V01.md`

## Pending acceptance

Database behavior, fresh/upgrade migration behavior, API authorization and warehouse isolation, rollback and concurrency behavior, frontend type/build checks, and consolidated independent code/security reviews remain unverified until M24 milestone acceptance.
