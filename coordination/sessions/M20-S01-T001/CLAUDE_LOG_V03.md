# M20-S01-T001 V03 Factual Execution Log

Task: M20.S01.T001 V03 remediation of the frozen V02 findings.
Builder: Codex.
Authorized branch: `main`.
Canonical remote: `https://github.com/Sekiph82/fmcg-erp-system`.

## Synchronization

- GitHub `origin/main` was fetched at `1c1114cf8908870811f9479cc4c9d11b04d65bf7`.
- The local branch started at V02 implementation commit `8dd477b838eaed221daf8d99021b77a3f67ecc0d`, five commits behind the fetched remote.
- Local `main` was fast-forwarded to `1c1114cf8908870811f9479cc4c9d11b04d65bf7` with `git merge --ff-only origin/main`.
- Pre-existing tracked and untracked owner changes in the working tree were preserved. No reset, clean, force push, or stash was used.

## Implementation

The V03 implementation is limited to the frozen release-path findings:

- `backend/app/services/mps_service.py`
  - Defines the release-required set as all positive, unreleased lines and keeps non-FEASIBLE lines as explicit blockers/counts.
  - Requires every release-required line to resolve before setting the plan to `RELEASED`; partial release remains `APPROVED`.
  - Returns `released_orders`, `skipped_no_recipe`, `skipped_ineligible`, `unresolved_lines`, `release_required_lines`, and `release_complete`.
  - Fails closed when Product is missing or its authoritative UOM is absent/invalid.
  - Removes the local `KG` fallback and derives the order UOM only from `Product.uom`.
- `backend/tests/test_m20_s01_t001_v03_mps_remediation.py`
  - Adds mixed partial-release behavior coverage.
  - Adds missing Product and invalid/missing UOM fail-closed coverage.
  - Adds an endpoint-bound transaction test covering first-order flush followed by a later-line Product failure.

No frontend file, migration, model, schema, tracker, or audit file was changed for V03.

## Commands and results

- `python -m py_compile app/services/mps_service.py app/api/v1/endpoints/mps.py tests/test_m20_s01_t001_mps_hardening.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py`
  - Exit 0.
- `python -c "import app.api.v1.endpoints.mps, app.services.mps_service; print('mps_import_ok')"`
  - Exit 0; printed `mps_import_ok`.
- `python -m pytest tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py -q`
  - `21 passed`, 68 warnings, exit 0.
- `python -m pytest tests/test_m20_s01_t001_mps_hardening.py -q` in an isolated detached worktree at exact V02 base `8dd477b838eaed221daf8d99021b77a3f67ecc0d`
  - `17 passed`, exit 0.
- `python -m pytest tests/ -k "mps or mrp or module_registry or gap007 or gap015 or permission or recipe or warehouse or production" -q -p no:warnings` in the isolated exact V02 base worktree
  - `169 passed, 3 failed, 471 deselected`.
  - The same three failures were reproduced before V03 in `test_gap012_document_knowledge_access.py`, `test_gap013_report_builder_access.py`, and `test_gap014_notification_center_access.py`; each raised `AttributeError: '_IncludedRouter' object has no attribute 'path'`.
- The same broad command in the current dirty workspace returned `168 passed, 9 failed, 471 deselected`; the additional six failures are from pre-existing owner changes copied into the workspace outside V03, including module registry/seed/schema/what-if behavior and the superseded ineligible-line expectation. They were not changed or weakened by V03.
- `python -m alembic heads`
  - Exit 0; printed `20260602_0001 (head)`.
- `git diff --check -- backend/app/services/mps_service.py backend/tests/test_m20_s01_t001_v03_mps_remediation.py`
  - Exit 0; printed `DIFF_CHECK_OK`.
- `docker info`
  - Docker CLI is installed, but the daemon is unavailable: `failed to connect to the docker API ... The system cannot find the file specified.`

## Transaction evidence and limitation

The new endpoint-bound test invokes the real `release_plan` function with a transaction-context fake implementing the existing `async with db.begin()` contract. The first line creates and flushes a ProductionOrder; the later line fails closed because its Product is missing. The transaction context rolls back pending orders and line linkage, and the plan remains `APPROVED`. The assertions confirm zero committed and zero pending orders after the exception.

This is architecture-consistent transaction-bound behavior, but it is not persistent PostgreSQL evidence. A real PostgreSQL-backed rollback test could not be executed because the Docker daemon was unavailable. No persistent rollback claim is made.

## Protected files and remaining work

- `TASKS.md` was not modified by V03. SHA-256 after synchronization: `BC69E6B3AF1C74438732372CA0FC32581FCEB4D958BF125BBD0650AD951A5A69`.
- `TASKS_HISTORY.md` was not modified by V03. SHA-256: `1ADF85FEB9BA607A5A8214A654733E788C8030D32FB752BEED6F53B142E7FB54`.
- `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V01.md` was not modified. SHA-256: `1C49D5B7D2EB9B2FC104F484995712F4183AD05B082FDAB4DD8111CECA13E12B`.
- `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V02.md` was not modified. SHA-256: `6A3434417F43852BB4B9F7D46D4409E4885AA56AD1400AE3CC78638CE469040E`.
- `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V03.md` was not modified. SHA-256: `3C3206072F4790E80755DFF78C0AE6F86CFA5961505088618639641B28E4B667`.
- No `CHATGPT_AUDIT_*.md` file was created or edited.
- No `TASKS.md` or `TASKS_HISTORY.md` lifecycle update was performed.
- The independent ChatGPT audit and tracker update remain external gates.

Final implementation and pushed remote SHA: to be recorded after commit and push.

AWAITING_CHATGPT_AUDIT
