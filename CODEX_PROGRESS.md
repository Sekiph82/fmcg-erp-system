# CODEX PROGRESS

## Last Updated
2026-05-16T14:30:00+03:00

## Last Completed Task
GAP-025L: Final checks complete — Multi-Company / Multi-Branch / Franchise Scaling. GAP-025 is complete.

## Current Working Task
GAP-028L: Run checks and record result: Full User Manual Generation. (GAP-026/027 already DONE; GAP-028K BLOCKED — skip per user override.)

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
- `20260516_0010` - NPD Formula Governance Reconciliation
- `20260516_0020` - IoT Machine Streaming Reconciliation (GAP-022C)
- `20260516_0030` - Maintenance Predictive Reconciliation (GAP-023C)
- `20260516_0040` - AI Prompt Registry Reconciliation (GAP-024C)
- `20260516_0050` - Multi-Company Warehouse Reconciliation (GAP-025C, current head)

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
| GAP-022A-L | True IoT / Machine Streaming | IoT promoted to ModuleDefinition, 6 permissions, ORM aligned, endpoint guards, frontend guards, nav guard, migration 20260516_0020, 22 tests |
| GAP-023A-L | ML-Based Predictive Maintenance | Reconciliation migration 20260516_0030, 7 permissions (predict/review_prediction/export added), endpoint guards, 7 page guards, 25 tests |
| GAP-024A-L | AI Agent Governance and Prompt Registry | ai_prompts table (migration 20260516_0040), AIPrompt ORM, schemas/ai.py, resolve_prompt() helper, 5 prompt CRUD endpoints, ai.export+ai.configure permissions, 9 frontend page guards, 28 tests |
| GAP-025A-L | Multi-Company / Multi-Branch / Franchise Scaling | company promoted to ModuleDefinition, 6 company.* permissions, _check_company_access helper, 12 endpoints rewritten with company.* guards, Warehouse company_id/branch_id (migration 20260516_0050), WarehouseBase schema fields, companies page RequirePermission guard, 22 tests |

## Files Changed In This Turn (GAP-025)
- `backend/alembic/versions/20260516_0050_multi_company_warehouse_reconciliation.py`
- `backend/app/models/master.py` (Warehouse company_id/branch_id columns added)
- `backend/app/schemas/master.py` (WarehouseBase company_id/branch_id fields added)
- `backend/app/core/module_registry.py` (company promoted to ModuleDefinition)
- `backend/app/db/seed.py` (6 company.* permissions + role grants for admin/company_admin/ceo/coo/cto)
- `backend/app/api/v1/endpoints/company.py` (full rewrite: company.* guards + _check_company_access)
- `frontend/src/app/dashboard/companies/page.tsx` (RequirePermission company.view guard added)
- `backend/tests/test_gap025_multi_company_branch.py`
- `docs/planning/GAP-025_MULTI_COMPANY_BRANCH_AUDIT.md`
- `docs/planning/GAP-025_MULTI_COMPANY_BRANCH_SCHEMA_DESIGN.md`
- `docs/planning/GAP-025_MULTI_COMPANY_BRANCH_IMPLEMENTATION_NOTES.md`
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

## Tests/Checks Run This Turn (GAP-025)
- `py_compile` on 7 GAP-025 files (migration, master model, master schema, module_registry, seed, company endpoints, company model) - all passed.
- `alembic heads` - single head `20260516_0050` confirmed.
- `pytest tests/test_gap025_multi_company_branch.py -q` - passed, 22 tests.
- `npm.cmd run type-check` - passed (no type errors).
- `npm.cmd run lint --max-warnings=0` - passed with no warnings/errors.

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
| ai | ModuleDefinition | view, create, edit, approve, export, configure |
| shelf_life | ModuleDefinition | view, create, edit, approve, hold, dispose, report |
| gs1 | ModuleDefinition | view, create, edit, approve, print, report, admin |

## Next Task
Continue from GAP-025A. Inspect the next unimplemented gap in TASKS.md roadmap. Create an audit doc before any implementation. Do not implement large code during the audit task.
