# CODEX PROGRESS

## Last Updated
2026-05-16T07:17:04+03:00

## Last Completed Task
GAP-021L: Final checks complete - New Product Development / Formula Governance. GAP-021 is complete.

## Current Working Task
GAP-022A: Audit current implementation - True IoT / Machine Streaming. Next step: inspect existing IoT, machine streaming, telemetry, utilities, production, frontend routes, models, migrations, and tests; create `docs/planning/GAP-022_TRUE_IOT_MACHINE_STREAMING_AUDIT.md`.

## Alembic Migration Chain (This Worktree)
- `20260511_0010` - Enterprise Accounting Core
- `20260511_0020` - Operational Posting Integration
- `20260511_0030` - Access Scopes (GAP-SEC-001C)
- `20260511_0040` - Finance Journal Scopes
- `20260515_0010` - CRM/Sales Scope Reconciliation
- `20260515_0020` - HRMS Payroll Reconciliation
- `20260515_0030` - Document Knowledge Reconciliation
- `20260515_0040` - Report Builder Schedule Run Log
- `20260515_0060` - GS1 Product Config Fields
- `20260516_0010` - NPD Formula Governance Reconciliation (current head)

## Completed GAPs In This Worktree Slice
| GAP | Title | Key Output |
|---|---|---|
| GAP-013A-L | Custom Report Builder Access | Module promoted, 6 permissions seeded, tests passed |
| GAP-014A-L | Notification Center Access | Module promoted, 6 permissions seeded, tests passed |
| GAP-015A-L | Navigation Sidebar Registry | Nav-config audit, dead guards fixed, 10 tests passed |
| GAP-016A-L | API Docs / Developer Portal | Metadata hardening, OpenAPI tags, 8 tests passed |
| GAP-017A-L | HACCP Audit-Grade Workflow | PDCA closure, audit scheduling, 4 endpoints added, 10 tests |
| GAP-018A-L | GS1 / Label Printing | Runtime bug fix, module promoted, 10 tests |
| GAP-019A-L | Shelf-Life / FEFO / Expiry Control | Module promoted to MODULE_DEFINITIONS, 7 permissions, 10 tests |
| GAP-020A-L | Consumer Complaint and Recall Linkage | Module promoted, 8 permissions seeded, endpoint/nav/page guards, 10 tests |
| GAP-021A | NPD / Formula Governance Audit | Audit documented NPD, BOM/formula, recipe, AI formulation, permissions, migration ownership, and governance gaps |
| GAP-021B | NPD / Formula Governance Schema Design | Designed module ownership, permission families, endpoint/frontend guards, AI boundary, and reconciliation-first migration direction |
| GAP-021C-L | NPD / Formula Governance Implementation | Reconciliation migration, module promotion, dedicated permissions, endpoint/page guards, 11 tests, final checks |

## Files Changed In This Turn
- `backend/app/api/v1/endpoints/consumer_complaints.py`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`
- `frontend/src/components/nav-config.tsx`
- `frontend/src/app/dashboard/quality/consumer-complaints/page.tsx`
- `backend/alembic/versions/20260516_0010_npd_formula_governance_reconciliation.py`
- `backend/app/api/v1/endpoints/npd_workflow.py`
- `backend/app/api/v1/endpoints/bom.py`
- `backend/app/api/v1/endpoints/recipes.py`
- `frontend/src/app/dashboard/npd/page.tsx`
- `frontend/src/app/dashboard/npd/[id]/page.tsx`
- `frontend/src/app/dashboard/bom/page.tsx`
- `frontend/src/app/dashboard/bom/[id]/page.tsx`
- `frontend/src/app/dashboard/bom/[id]/explode/page.tsx`
- `frontend/src/app/dashboard/bom/[id]/costing/page.tsx`
- `frontend/src/app/dashboard/bom/[id]/compliance/page.tsx`
- `frontend/src/app/dashboard/bom/compare/page.tsx`
- `frontend/src/app/dashboard/bom/conversion/page.tsx`
- `frontend/src/app/dashboard/bom/substitutes/page.tsx`
- `frontend/src/app/dashboard/recipes/page.tsx`
- `frontend/src/app/dashboard/recipes/[id]/page.tsx`
- `backend/tests/test_gap020_consumer_complaint_recall.py`
- `backend/tests/test_gap021_npd_formula_governance.py`
- `docs/planning/GAP-020_CONSUMER_COMPLAINT_RECALL_SCHEMA_DESIGN.md`
- `docs/planning/GAP-020_CONSUMER_COMPLAINT_RECALL_IMPLEMENTATION_NOTES.md`
- `docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_AUDIT.md`
- `docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_SCHEMA_DESIGN.md`
- `docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_IMPLEMENTATION_NOTES.md`
- `TASKS.md`
- `CODEX_PROGRESS.md`

## GAP-020 Summary
- `consumer_complaints` promoted from `EndpointRouteDefinition` to `ModuleDefinition`.
- Dedicated permissions added: `view`, `create`, `edit`, `delete`, `approve`, `close`, `link_recall`, `export`.
- Admin receives full complaint permissions; quality manager receives operational permissions without delete; quality officer and sales managers receive intake/update permissions without delete or recall linkage; read-only auditor receives view/export.
- Consumer complaint endpoint now requires dedicated permissions.
- Close/resolution updates require `consumer_complaints.close`.
- Recall escalation/link fields require `consumer_complaints.link_recall`.
- Consumer Complaints nav now uses `consumer_complaints.view`.
- Consumer Complaints page now has page-level view guard and create/edit action guards.
- No DB migration, model change, schema extraction, or service extraction was added by design.

## GAP-021A Summary
- NPD project model/endpoints/pages exist with stage gates, checklists, stage advancement, and pilot batches.
- Advanced BOM/formula engine exists with lifecycle, formula/packaging/multilevel/rework/co-product support, lines, costing, compliance, conversion profiles, substitutes, yield config, and AI recommendations.
- Recipe CRUD exists with items, process parameters, approve/obsolete/duplicate flow.
- AI formulation UI exists and can generate/list/approve/favorite formulations, but approval is not clearly converted into controlled recipe/BOM/NPD records.
- Main gaps: weak or missing dedicated permissions, loose module ownership, unclear migration ownership, soft links, and missing controlled governance bridge.

## GAP-021B Summary
- Preserve existing NPD, BOM/formula, recipe, and AI formulation surfaces.
- Promote `npd`, `bom`, and `recipe` into module-owned routes in later implementation tasks.
- Add dedicated permission families for NPD, BOM/formula, and recipe governance.
- Treat AI formulation approval as recommendation approval, not production formula release.
- GAP-021C should inspect migration ownership before adding any migration and should stay additive.

## GAP-021C-L Summary
- Added additive merge-head reconciliation migration `20260516_0010_npd_formula_governance_reconciliation.py`.
- Alembic now has a single head: `20260516_0010`.
- Skipped model/schema/service rewrites after inspection because existing NPD, advanced BOM, recipe, schema, CRUD, and service surfaces are functional and compile/import cleanly.
- Promoted `npd`, `bom`, and `recipe` into `ModuleDefinition` ownership and removed duplicate loose endpoint-route entries.
- Added dedicated exact and scoped/all permission tuples for NPD, BOM/formula, and recipe governance.
- Added conservative role grants for admin, executive, production, quality, factory, and auditor roles.
- Hardened NPD, BOM, and recipe endpoints with dedicated permission dependencies and dynamic lifecycle checks.
- Updated NPD, BOM, recipe, and related BOM frontend pages to use page/action guards.
- Fixed nav ownership so NPD uses `npd.view`, BOM uses `bom.view`, and Recipes / BOM uses `recipe.view`.
- Added `backend/tests/test_gap021_npd_formula_governance.py` with 11 focused contract tests.
- Added `docs/planning/GAP-021_NPD_FORMULA_GOVERNANCE_IMPLEMENTATION_NOTES.md`.

## Tests/Checks Run This Turn
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\api\v1\endpoints\consumer_complaints.py app\core\module_registry.py app\db\seed.py tests\test_gap020_consumer_complaint_recall.py` - passed.
- `cd backend; .\venv\Scripts\python.exe -m pytest tests\test_gap020_consumer_complaint_recall.py -q` - passed, 10 tests.
- `cd backend; .\venv\Scripts\python.exe -c "import app.api.v1.endpoints.consumer_complaints; import app.main; print('gap020 endpoint and app imports ok')"` - passed; existing optional dependency diagnostics for missing `pyotp` and `dateutil` plus unrelated SQLAlchemy/Pydantic warnings remain.
- `cd frontend; npm.cmd run type-check` - passed.
- `cd frontend; npm.cmd run lint` - passed with no warnings/errors.
- GAP-020 schema design and implementation notes heading checks - passed.
- GAP-020/GAP-021 docs size checks - passed.
- GAP-020/GAP-021 docs secret-pattern check - no matches.
- GAP-021 audit heading check - passed.
- GAP-021 schema design heading check - passed.
- GAP-021 schema design size check - passed, 7691 bytes.
- GAP-021 schema design secret-pattern check - no matches.
- `cd backend; .\venv\Scripts\python.exe -m py_compile alembic\versions\20260516_0010_npd_formula_governance_reconciliation.py` - passed.
- `cd backend; .\venv\Scripts\python.exe -m alembic heads` - passed, single head `20260516_0010`.
- `cd backend; .\venv\Scripts\python.exe -m alembic history -r "20260515_0030:"` - passed, `20260516_0010` mergepoint confirmed.
- `cd backend; .\venv\Scripts\python.exe -m alembic upgrade 20260516_0010 --sql` - passed, offline SQL rendered and includes NPD, recipe, and advanced BOM create statements.
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\models\npd.py app\models\bom.py app\models\recipe.py` - passed.
- `cd backend; .\venv\Scripts\python.exe -c "from sqlalchemy.orm import configure_mappers; import app.models.npd, app.models.bom, app.models.recipe; configure_mappers(); print('gap021 npd/bom/recipe mappers ok')"` - passed with existing unrelated SQLAlchemy relationship warnings.
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\schemas\bom.py app\schemas\recipe.py app\api\v1\endpoints\npd_workflow.py` - passed.
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\services\bom_service.py app\services\bom_explosion_service.py app\services\bom_scaling_service.py app\services\bom_costing_service.py app\services\bom_compliance_service.py app\services\bom_ai_service.py app\crud\recipe.py app\api\v1\endpoints\npd_workflow.py` - passed.
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\api\v1\endpoints\npd_workflow.py app\api\v1\endpoints\bom.py app\api\v1\endpoints\recipes.py app\core\module_registry.py app\db\seed.py` - passed.
- `cd frontend; npm.cmd run type-check` - passed after GAP-021 frontend guard updates.
- `cd frontend; npm.cmd run lint` - passed after GAP-021 frontend guard updates.
- `cd backend; .\venv\Scripts\python.exe -m py_compile tests\test_gap021_npd_formula_governance.py` - passed.
- `cd backend; .\venv\Scripts\python.exe -m pytest tests\test_gap021_npd_formula_governance.py -q` - passed, 11 tests.
- `cd backend; .\venv\Scripts\python.exe -c "import app.api.v1.endpoints.npd_workflow, app.api.v1.endpoints.bom, app.api.v1.endpoints.recipes, app.core.module_registry, app.db.seed; print('gap021 endpoint registry seed imports ok')"` - passed.
- GAP-021 implementation notes file exists, heading check passed, size 8935 bytes, secret-pattern check no matches.
- `git status --short --untracked-files=all` - reviewed.

## Known Blockers
- Docker daemon unavailable in the recent session context, so live `alembic upgrade head` remains blocked when migrations are involved.
- GAP-028K remains blocked because full user manual generation requires screenshot captures first.
- Local backend venv app import still logs existing optional dependency diagnostics for missing `pyotp` and `dateutil`; this did not fail GAP-020 checks.
- GAP-021 used offline Alembic SQL rendering only; no live PostgreSQL or production database was touched.

## Module Registry Status
| Module Key | Type | Permission Actions |
|---|---|---|
| users | ModuleDefinition | view, create, edit, delete |
| roles | ModuleDefinition | view, create, edit, delete |
| inventory | ModuleDefinition | DEFAULT_ACTIONS |
| production | ModuleDefinition | view, create, edit, approve, export |
| planning | ModuleDefinition | view, create, edit, approve, calculate, export |
| npd | ModuleDefinition | view, create, edit, approve, advance, pilot, export |
| bom | ModuleDefinition | view, create, edit, delete, approve, release, archive, cost, ai, export |
| recipe | ModuleDefinition | view, create, edit, delete, approve, obsolete, export |
| procurement | ModuleDefinition | full actions |
| finance | ModuleDefinition | full actions + configure |
| sales | ModuleDefinition | full actions |
| hr | ModuleDefinition | full actions |
| payroll_ke | ModuleDefinition | view, create, approve, export |
| quality | ModuleDefinition | view, create, edit, approve, export |
| consumer_complaints | ModuleDefinition | view, create, edit, delete, approve, close, link_recall, export |
| maintenance | ModuleDefinition | DEFAULT_ACTIONS |
| utilities | ModuleDefinition | DEFAULT_ACTIONS |
| reports | ModuleDefinition | view, create, edit, run, export, admin |
| notifications | ModuleDefinition | view, manage, send, configure, report, admin |
| documents | ModuleDefinition | view, create, edit, approve, archive, export |
| knowledge_base | ModuleDefinition | view, create, edit, publish, delete, admin |
| esign | ModuleDefinition | view, request, sign, cancel, admin |
| ai | ModuleDefinition | view, create, edit, approve, export |
| shelf_life | ModuleDefinition | view, create, edit, approve, hold, dispose, report |
| gs1 | ModuleDefinition | view, create, edit, approve, print, report, admin |

## Next Task
Continue from GAP-022A. Inspect current IoT / machine streaming implementation and create `docs/planning/GAP-022_TRUE_IOT_MACHINE_STREAMING_AUDIT.md`. Do not implement large code during the audit task.
