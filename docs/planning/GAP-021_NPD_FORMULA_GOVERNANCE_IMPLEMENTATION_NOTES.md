# GAP-021 New Product Development / Formula Governance Implementation Notes

## Summary

GAP-021 hardens the existing NPD, advanced BOM/formula, and recipe surfaces into owned, permissioned ERP modules. The implementation preserves the current NPD, BOM, recipe, and AI formulation architecture and focuses on migration reconciliation, module ownership, dedicated permissions, backend endpoint guards, frontend guards, tests, and documentation.

## Audit Findings From GAP-021A

The audit found substantial existing functionality:

- NPD projects, stage gates, checklists, pilot batches, and dashboard pages already exist.
- Advanced BOM/formula models, services, endpoints, and pages already support formula lifecycle, lines, yield, conversion profiles, substitutes, costing, compliance, explosion, and AI recommendations.
- Recipe models, CRUD, approval, obsolescence, duplication, items, process parameters, pages, and imports already exist.
- AI formulation UI exists, but its approval path is not the same as controlled production formula release.

The main gaps were weak module ownership, missing dedicated permission families, auth-only or unprotected mutation endpoints, broad `production.view` frontend guards, and unclear Alembic ownership for NPD/BOM/recipe tables.

## Design Decision From GAP-021B

No parallel formula architecture was added.

No model rewrite was added.

No schema extraction or service-layer refactor was added because the existing ORM, Pydantic, CRUD, and service surfaces are already functional for this hardening slice.

The selected implementation path was reconciliation-first: verify or add Alembic ownership, promote module registry ownership, add dedicated permissions and conservative role grants, harden endpoints and pages, and document current limits.

## Migration Reconciliation

Added `backend/alembic/versions/20260516_0010_npd_formula_governance_reconciliation.py`.

The migration merges the existing Alembic heads `20260515_0040` and `20260515_0060` into one head, `20260516_0010`.

It creates missing NPD, recipe, and advanced BOM/formula tables only when absent:

- `npd_projects`
- `npd_stage_gates`
- `npd_pilot_batches`
- `recipes`
- `recipe_items`
- `process_parameters`
- `advanced_boms`
- `advanced_bom_lines`
- `bom_substitute_groups`
- `bom_substitutes`
- `bom_conversion_profiles`
- `bom_yield_configs`
- `bom_ai_recs`

No destructive schema changes were made.

## Model, Schema, and Service Decisions

GAP-021D was skipped after inspection because existing `NPDProject`, stage gate, pilot batch, advanced BOM, and recipe ORM models already match the reconciliation migration.

GAP-021E was skipped because BOM and recipe schema modules already cover current contracts, and NPD endpoint-local schemas compile and validate.

GAP-021F was skipped because existing BOM service modules, recipe CRUD helpers, and NPD endpoint-local stage-gate logic are functional and import cleanly.

## Module Registry Changes

Promoted these surfaces into `ModuleDefinition` ownership:

- `npd` at `/npd-workflow`, import path `app.api.v1.endpoints.npd_workflow`
- `bom` at `/bom`, import path `app.api.v1.endpoints.bom`
- `recipe` at `/recipes`, import path `app.api.v1.endpoints.recipes`

Removed the duplicate loose endpoint-route ownership entries for `npd_workflow`, `bom`, and `recipes`.

## Permissions and Seed Role Grants

Registered dedicated permission families:

- `npd.view`, `npd.create`, `npd.edit`, `npd.approve`, `npd.advance`, `npd.pilot`, `npd.export`
- `bom.view`, `bom.create`, `bom.edit`, `bom.delete`, `bom.approve`, `bom.release`, `bom.archive`, `bom.cost`, `bom.ai`, `bom.export`
- `recipe.view`, `recipe.create`, `recipe.edit`, `recipe.delete`, `recipe.approve`, `recipe.obsolete`, `recipe.export`

Seed data also includes scoped/all variants for planning-era role compatibility.

Admin receives full exact permissions. Executive and read-only roles receive view/export style access. Production Manager receives operational NPD/BOM/recipe permissions excluding broad delete/archive/AI. Quality Manager receives approval/release visibility where appropriate, excluding create/delete/AI overreach. Read-only Auditor receives view/export only.

## API Endpoint Protection Changes

NPD endpoints now use dedicated permissions:

- list/detail/dashboard: `npd.view`
- create: `npd.create`
- update/checklist: `npd.edit`
- advance stage: `npd.advance`
- approve gate: `npd.approve`
- pilot batches: `npd.pilot`

BOM endpoints now use dedicated permissions:

- list/detail/dashboard/explosion/scaling/compliance/substitute/conversion/AI list: `bom.view`
- create/clone/substitute/conversion creation: `bom.create`
- header/line/yield mutation: `bom.edit`
- line delete: `bom.delete`
- lifecycle transition: dynamic `bom.edit`, `bom.approve`, or `bom.release`
- archive: `bom.archive`
- costing: `bom.cost`
- run/action AI recommendation: `bom.ai`

Recipe endpoints now use dedicated permissions:

- list/detail: `recipe.view`
- create/duplicate: `recipe.create`
- update/add item/add process parameter: `recipe.edit`
- delete recipe/item/process parameter: `recipe.delete`
- approve: `recipe.approve`
- obsolete: `recipe.obsolete`

## Frontend Guard Changes

Navigation now uses dedicated permissions:

- Recipes shortcut: `recipe.view`
- NPD section and NPD Projects: `npd.view`
- BOM section and BOM child pages: `bom.view`

NPD pages now use `RequirePermission` for `npd.view` and action guards for create, edit checklist, approve gate, advance stage, and pilot batch capture.

BOM pages now use `RequirePermission` for `bom.view` or `bom.cost` as appropriate, and action guards for create, edit, delete, lifecycle, archive, costing link, AI actions, substitutes, and conversion profiles.

Recipe pages now use `RequirePermission` for `recipe.view` and action guards for create/import, delete, approve, obsolete, duplicate, item mutation, and process-parameter mutation.

## AI Formulation Boundary

AI formulation remains an advisory surface. `bom.ai` now governs BOM AI recommendation execution and actioning. AI formulation approval does not release a production BOM or recipe.

A future conversion flow should create a controlled draft recipe or BOM and then use the normal `recipe.*` or `bom.*` approval/release permissions.

## Tests Added and Commands Run

Focused tests were added in `backend/tests/test_gap021_npd_formula_governance.py`.

Commands run:

- `cd backend; .\venv\Scripts\python.exe -m py_compile alembic\versions\20260516_0010_npd_formula_governance_reconciliation.py`
- `cd backend; .\venv\Scripts\python.exe -m alembic heads`
- `cd backend; .\venv\Scripts\python.exe -m alembic history -r "20260515_0030:"`
- `cd backend; .\venv\Scripts\python.exe -m alembic upgrade 20260516_0010 --sql`
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\models\npd.py app\models\bom.py app\models\recipe.py`
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\schemas\bom.py app\schemas\recipe.py app\api\v1\endpoints\npd_workflow.py`
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\services\bom_service.py app\services\bom_explosion_service.py app\services\bom_scaling_service.py app\services\bom_costing_service.py app\services\bom_compliance_service.py app\services\bom_ai_service.py app\crud\recipe.py app\api\v1\endpoints\npd_workflow.py`
- `cd backend; .\venv\Scripts\python.exe -m py_compile app\api\v1\endpoints\npd_workflow.py app\api\v1\endpoints\bom.py app\api\v1\endpoints\recipes.py app\core\module_registry.py app\db\seed.py`
- `cd backend; .\venv\Scripts\python.exe -m py_compile tests\test_gap021_npd_formula_governance.py`
- `cd backend; .\venv\Scripts\python.exe -m pytest tests\test_gap021_npd_formula_governance.py -q`
- `cd frontend; npm.cmd run type-check`
- `cd frontend; npm.cmd run lint`

## Known Limitations and Follow-Ups

- NPD project to BOM/recipe linkage remains a soft string reference.
- NPD stage gate approvals still use free-text approver fields rather than strict user/role-backed signatures.
- Checklist keys remain JSON-based and are not yet backed by governed checklist templates.
- AI formulation approval is not yet connected to controlled draft recipe/BOM creation.
- No new audit-log trail was added for stage-gate and lifecycle actions in this slice.
- No CSV export/reporting workflow was added for NPD portfolio governance.

## Acceptance Criteria Snapshot

- Module ownership is explicit for NPD, BOM, and recipe.
- Dedicated permissions are registered in module registry and seed data.
- Backend endpoints no longer rely on broad authenticated access or `production.view` for high-risk formula/NPD mutations.
- Frontend nav and page/action guards use dedicated permissions.
- Migration ownership is reconciled into a single Alembic head without destructive changes.
- AI formulation approval remains documented as separate from production formula release.
- Focused contract tests pass.
