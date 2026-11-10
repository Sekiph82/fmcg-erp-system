# M23.S02.T002 — Scrap/waste/downtime capture

## Implementation status

Implemented locally; milestone acceptance and consolidated test/review batch remain pending.

## Acceptance basis and boundary

- Root `TASKS.md`: `M23.S02.T002 — Scrap/waste/downtime capture`.
- M23 plan: retain each execution fact against the correct operation and existing quality/inventory boundaries.
- Shop Floor manuals: `docs/user-manual/module-manuals/manufacturing/08-shop-floor.md` and `docs/user-manual/module-manuals/manufacturing/11-oee-reporting.md`; the latter defines waste quantity as scrap quantity and the existing normal/abnormal classification.
- M22 responsibility decision: keep `exec_*` records separate; do not infer a crosswalk or dual-write to standard production `waste_records`.
- No M23-specific independent audit is indexed. Applied `coordination/AUDIT_POLICY.md` and relevant `coordination/AUDIT_INDEX.md` learnings ERP-AL-003, ERP-AL-008, ERP-AL-012, plus the M22 responsibility boundary. No independent verdict is claimed.

## Changes

- Shop Floor scrap now accepts optional existing normal/abnormal waste classification and reason on both incremental scrap logging and final work-order completion; the operation total and activity event retain the quantity/classification/reason. The API rejects zero, negative, NaN, and infinite incremental scrap quantities. General quantity updates reject non-finite or negative values.
- Downtime API categories and impact levels are constrained to the existing enumerations.
- The general Downtime Board can create line-level downtime without an operator session only through authenticated line-edit permission. Operation-linked downtime still requires the authenticated matching session. The service locks the work order, checks active operation/parent state, derives parent and line from that work order, and rejects mismatched or order-only caller links.
- Added an explicit line filter to the downtime board for scoped users and visible request errors. The authenticated ERP user remains the creator/closer; the typed operator label is contextual only.
- Updated the Shop Floor manual. Line/operation downtime remains separate from the standard production-order downtime and waste tables until an explicit M22 crosswalk exists.
- Added focused backend tests for quantity boundaries, schema categories, line-scoped downtime creation, work-order session requirement, and operation-parent linkage. These are deferred to the consolidated M23.S04 test batch.

## Verification performed

- `python -m py_compile backend/app/api/v1/endpoints/shop_floor.py backend/app/services/shop_floor_service.py backend/app/schemas/shop_floor.py backend/tests/test_m23_s02_t002_scrap_waste_downtime.py` — PASS.
- Targeted ESLint for `frontend/src/app/dashboard/shop-floor/terminal/page.tsx` and `frontend/src/app/dashboard/shop-floor/downtime/page.tsx` — PASS.
- `git diff --check` — PASS. Git emitted existing LF-to-CRLF working-copy notices for multiple files.
- No pytest, full suite, database migration, frontend typecheck, independent review, or live-factory acceptance is claimed; these are deferred to M23.S04.
