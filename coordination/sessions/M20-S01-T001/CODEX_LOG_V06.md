# M20.S01.T001 V06 Codex Implementation Log

## Status

`AWAITING_CHATGPT_AUDIT`

Builder: Codex
Implementation head: `21612da51a3a7169d5031069a03aeb30d32b94df`
Implementation commits: `431130d`, `5d8e966`, `fade01e`, `21612da`
GitHub Actions run: https://github.com/Sekiph82/fmcg-erp-system/actions/runs/39456732735
Backend job: https://github.com/Sekiph82/fmcg-erp-system/actions/runs/39456732735/job/118745459839

## Scope and Safety

- Continued from the published V06 prompt and V05 independent audit.
- Used `main` only; no branch, reset, clean, stash, rebase, force-push, or destructive database operation was used.
- Preserved the existing dirty owner worktree. Only the M20 test fixture and development bootstrap files were staged for V06 implementation commits, plus this log.
- `TASKS.md`, `TASKS_HISTORY.md`, and `CHATGPT_AUDIT_*` files were not edited by the V06 implementation commits.

## Corrections

### PostgreSQL fixture dependency ordering

Rollback, concurrent-release, and deletion-gap fixtures now flush `Product`/`Warehouse`, then `Recipe`/`MPSPlan`, before constructing dependent `MPSLine` rows. This prevents NULL `mps_id` foreign keys and keeps the real PostgreSQL setup path intact.

### Fresh development database sequence

CI uses the development bootstrap path, which creates current-model tables and stamps Alembic instead of replaying every migration. `backend/scripts/dev_migrate.py` now creates and high-water initializes `mps_po_number_seq` on both fresh and untracked create-all paths, matching migration `20261019_0010` and preserving existing numeric `PO-MPS-*` values.

### Real PostgreSQL proof behavior

The real rollback and concurrency tests no longer convert PostgreSQL probe exceptions into skips. They skip only when the configured database is not PostgreSQL. Shared async engine pools are disposed before each PostgreSQL proof test so pytest event-loop boundaries cannot reuse a connection from another loop.

## Verification

### Local

- `python -m py_compile backend/scripts/dev_migrate.py backend/tests/test_m20_s01_t001_v03_mps_remediation.py` — passed.
- `git diff --check` on scoped V06 files — passed.
- Local focused run — `4 passed, 2 skipped`; the two database tests require PostgreSQL, which was unavailable locally. No local PostgreSQL pass is claimed.

### GitHub-hosted PostgreSQL CI

Run `39456732735` used PostgreSQL 16 and completed the migration/bootstrap and single-head checks successfully. The M20 remediation file reported:

`tests/test_m20_s01_t001_v03_mps_remediation.py ......`

This is **6 passed, 0 skipped**, covering the mixed-release contract, three invalid-product/UOM cases, persisted rollback after injected late flush failure, concurrent distinct PO allocation, deletion-gap monotonicity, and retry allocation. The full backend result was `642 passed, 7 failed`; no M20 test failed.

### Remaining backend failures

The seven remaining failures are pre-existing and outside M20.S01.T001:

- `tests/test_etims_skeleton.py::test_simulation_connector_returns_accepted`
- `tests/test_etims_skeleton.py::test_http_connector_uses_mock_no_real_network`
- `tests/test_gap012_document_knowledge_access.py::test_document_knowledge_esign_routes_register_from_module_registry`
- `tests/test_gap013_report_builder_access.py::test_report_builder_routes_register_from_module_registry`
- `tests/test_gap014_notification_center_access.py::test_notification_routes_register_from_module_registry`
- `tests/test_hardening.py::test_registry_route_registration_loads_enabled_modules`
- `tests/test_hardening.py::test_endpoint_route_registration_loads_non_core_routes`

The first two are eTIMS response/httpx contract failures. The remaining five are `_IncludedRouter` versus `.path` route-wrapper failures. They were not weakened or changed in V06.

### Frontend audit

The separate frontend job failed at `npm audit --audit-level=critical` before typecheck/build. The exact audit result was `23 vulnerabilities (2 moderate, 20 high, 1 critical)`. Remediation would require dependency changes, including force/major upgrades, outside this M20 task; no unrelated frontend dependency change was made and frontend PASS is not claimed.

## Protected Files and Acceptance Snapshot

- [x] MPS fixture FK ordering corrected.
- [x] Fresh/dev bootstrap creates and initializes the MPS sequence.
- [x] PostgreSQL rollback, concurrency, sequence high-water/deletion-gap behavior executed in GitHub CI without skips.
- [x] Implementation commits pushed to `main`.
- [x] Factual V06 log published in the required session directory.
- [x] `TASKS.md`, `TASKS_HISTORY.md`, and ChatGPT audit files were not edited by V06 implementation commits.
- [ ] Independent ChatGPT audit and tracker acceptance remain pending.

Final state: `AWAITING_CHATGPT_AUDIT`.
