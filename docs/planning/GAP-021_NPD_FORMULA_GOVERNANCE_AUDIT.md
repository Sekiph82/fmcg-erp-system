# GAP-021 New Product Development / Formula Governance Audit

## Summary

GAP-021 is not starting from zero. The repository already has NPD project models and pages, a richer Advanced BOM/formula engine, recipe CRUD, and an AI formulation screen. The gap is that these surfaces are only loosely connected and do not yet behave like one governed NPD-to-formula-to-launch workflow.

The most important risks are missing dedicated module ownership for NPD/BOM/recipe, weak route-level permissions on NPD and recipe endpoints, no permissions at all on the BOM endpoint, unclear Alembic ownership for the NPD and advanced BOM tables, soft links between NPD projects and BOM/recipes, and no controlled approval bridge from AI formulation to approved formula/BOM/recipe.

## Business Importance

FMCG product development needs controlled formula governance. An NPD project should be able to link to a recipe or BOM, pass stage-gate approvals, verify allergen/nutrition/label/regulatory readiness, run pilot batches, approve formulas, and launch only after quality, finance, regulatory, production, and commercial signoff.

Current implementation provides useful building blocks but does not yet enforce the governance chain end to end.

## Files Inspected

- `backend/app/models/npd.py`
- `backend/app/api/v1/endpoints/npd_workflow.py`
- `frontend/src/app/dashboard/npd/page.tsx`
- `frontend/src/app/dashboard/npd/[id]/page.tsx`
- `backend/app/models/bom.py`
- `backend/app/schemas/bom.py`
- `backend/app/api/v1/endpoints/bom.py`
- `backend/app/services/bom_service.py`
- `backend/app/services/bom_scaling_service.py`
- `backend/app/services/bom_explosion_service.py`
- `backend/app/services/bom_costing_service.py`
- `backend/app/services/bom_compliance_service.py`
- `backend/app/services/bom_ai_service.py`
- `frontend/src/lib/bom.ts`
- `frontend/src/app/dashboard/bom/*`
- `backend/app/models/recipe.py`
- `backend/app/schemas/recipe.py`
- `backend/app/api/v1/endpoints/recipes.py`
- `backend/app/crud/recipe.py`
- `frontend/src/lib/recipes.ts`
- `frontend/src/app/dashboard/recipes/*`
- `frontend/src/app/dashboard/ai/formulations/page.tsx`
- `frontend/src/lib/aiApi.ts`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`
- `backend/alembic/versions/*` search results for NPD/BOM/recipe ownership

## Existing NPD Coverage

`backend/app/models/npd.py` defines:

- `NPDProject`
- `NPDStageGate`
- `NPDPilotBatch`
- `NPDStage`
- `NPDCategory`
- `NPDPilotBatchOutcome`

The NPD project captures project code, name, category, stage, target launch date, estimated COGS, estimated selling price, soft BOM/recipe id, regulatory checklist, launch readiness checklist, brand, market, notes, and activity flag.

The endpoint `backend/app/api/v1/endpoints/npd_workflow.py` exposes:

- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `PATCH /projects/{project_id}`
- `POST /projects/{project_id}/advance-stage`
- `POST /projects/{project_id}/gates/{gate_id}/approve`
- `PATCH /projects/{project_id}/checklist`
- `POST /projects/{project_id}/pilot-batches`
- `GET /dashboard`

The frontend NPD pages support project list/dashboard, project creation, detail view, stage gate approval, stage advance, checklist toggles, and pilot batch capture.

## Existing BOM / Formula Coverage

`backend/app/models/bom.py` defines an enterprise-oriented BOM/formula engine:

- `AdvancedBOM`
- `AdvancedBOMLine`
- `BOMSubstituteGroup`
- `BOMSubstitute`
- `BOMConversionProfile`
- `BOMYieldConfig`
- `BOMAIRec`

It includes lifecycle states, formula/intermediate/packaging/multilevel/rework/co-product BOM types, product links, version/revision, effectivity dates, reviewer/approver/releaser fields, quality/label/compliance soft links, costing fields, allergen/nutrition JSON, substitute policies, conversion profiles, yield/loss categories, and AI recommendations.

The BOM endpoint exposes dashboard, create/list/detail/update, clone, lifecycle advance/archive, lines, explosion, scaling, costing, comparison, compliance summary, AI recommendation actions, yield configs, substitute groups, substitutes, and conversion profiles.

The BOM frontend pages cover master list, detail, explosion, costing, compliance, substitutes, conversion profiles, and version comparison.

## Existing Recipe Coverage

`backend/app/models/recipe.py` defines:

- `Recipe`
- `RecipeItem`
- `ProcessParameter`
- `RecipeStatus`

Recipe supports product versioning, draft/approved/obsolete status, validity dates, creator/approver, ingredients, loss percentage, alternatives, and process parameters.

The recipe endpoint supports list/create/detail/update/delete, approve, obsolete, duplicate as new version, item CRUD, and process-parameter CRUD.

The frontend recipe pages use `frontend/src/lib/recipes.ts` and cover recipe list, new recipe, detail, approval, duplication, ingredients, and process parameters.

## Existing AI Formulation Coverage

`frontend/src/app/dashboard/ai/formulations/page.tsx` uses `frontend/src/lib/aiApi.ts` to generate, list, approve, favorite, and inspect AI formulations.

The UI clearly warns that approval is disabled in AI mock mode. This is good governance UX, but the approved AI formulation is not clearly converted into a controlled NPD project, recipe, or advanced BOM in the current inspected files.

## Existing Permissions / Roles / Navigation

Current route ownership is partial:

- `npd_workflow` is an `EndpointRouteDefinition`, not a `ModuleDefinition`.
- `bom` is an `EndpointRouteDefinition`, not a `ModuleDefinition`.
- `recipes` is an `EndpointRouteDefinition`, not a `ModuleDefinition`.

Seed data has scoped visibility permissions:

- `bom.view_all`
- `recipe.view_all`

The frontend navigation currently gates:

- NPD by `production.view`
- BOM by `production.view`
- Recipes/BOM shortcut by `production.view`
- AI formulation by `ai.view`

No dedicated `npd.*`, `bom.*`, or `recipe.*` permission family is registered for create/edit/approve/release/export/admin style governance.

## Authentication and Permission Findings

`npd_workflow.py` requires authenticated users but does not use dedicated permission dependencies. Any authenticated user can create projects, update projects, approve gates, advance stages, update checklists, and add pilot batches.

`recipes.py` requires authenticated users but does not use dedicated permission dependencies. Any authenticated user can create, update, delete, approve, obsolete, duplicate, and change recipe items/process parameters.

`bom.py` does not show `get_current_user`, `require_permission`, or equivalent dependency usage on the inspected route list. That makes BOM create/update/delete/archive/AI actions a high-risk permission gap.

## Migration Ownership Findings

Searches found references to `advanced_boms` from other migrations, but no clear migration ownership for all advanced BOM tables in `backend/app/models/bom.py`.

Searches did not clearly find Alembic ownership for `npd_projects`, `npd_stage_gates`, or `npd_pilot_batches`.

Recipe references appear in a production AI migration, but full ownership of `recipes`, `recipe_items`, and `process_parameters` was not clearly established in the inspected search results.

GAP-021B/C should verify the real live Alembic chain and decide whether a reconciliation migration is needed before changing models.

## Missing Pieces

- Dedicated `npd` module definition and permission family.
- Dedicated `bom` or `formula` module definition and permission family.
- Dedicated `recipe` module definition and permission family.
- Route-level permission enforcement for NPD actions.
- Route-level permission enforcement for recipe destructive and approval actions.
- Any visible route-level auth/permission enforcement on BOM endpoint actions.
- Hard relationship from NPD project to approved recipe/BOM.
- Approval workflow connecting formula/BOM readiness to NPD stage advancement.
- Governance bridge from AI formulation approval into controlled recipe/BOM records.
- Migration ownership for NPD and possibly BOM/recipe tables.
- Audit trail for stage-gate changes and formula/BOM approvals beyond local fields.
- Page/action guards in NPD frontend.
- CSV/export/reporting support for NPD portfolio governance.

## Partial Pieces

- NPD stage gates exist, but approvals are free-text `approved_by` rather than user/role backed.
- NPD checklist fields exist as JSON, but keys are not validated against a governed checklist definition.
- `NPDProject.bom_recipe_id` exists, but it is a string soft link rather than a typed relationship.
- BOM lifecycle exists, but endpoint permission protection is not yet aligned with lifecycle risk.
- Recipe approval exists, but permission checks are broad authentication only.
- AI formulation approval exists in the AI surface, but productization into recipe/BOM/NPD is not clear.

## Risks

- Unauthorized authenticated users may approve NPD gates or recipes.
- Unauthorized users may mutate BOMs if the endpoint is reachable without auth/permission dependencies.
- NPD launch can advance based on checklist toggles without verifying actual BOM, label, allergen, nutrition, costing, or regulatory records.
- Soft BOM/recipe links can drift or point to missing records.
- AI-generated formulation approval can be mistaken for controlled formula approval.
- Lack of migration ownership may cause runtime table mismatch in fresh environments.

## Recommended GAP-021B Design Direction

GAP-021B should design a reconciliation-first governance slice:

- promote NPD into a module-owned route with dedicated permissions
- decide whether BOM and recipe should be separate module definitions or a single formula governance permission family
- verify migration ownership before adding new migration work
- avoid replacing the existing BOM/recipe/NPD engines
- keep AI formulation as an input surface, not a source of approved production formulas
- design endpoint guards for view/create/edit/approve/release/archive/export/admin actions
- define how NPD project links to approved recipe/BOM in a future migration if current schema is insufficient

## Acceptance Criteria for GAP-021 Completion

GAP-021 should be considered complete only when:

- NPD/formula governance module ownership is explicit.
- Dedicated permissions are seeded and used by backend and frontend.
- NPD stage gates and recipe/BOM lifecycle actions require approval permissions.
- BOM endpoint mutations are not public or auth-only.
- Migration ownership is verified or reconciled.
- AI formulation approval is clearly separated from controlled production formula release.
- Tests cover registry, seed permissions, endpoint guards, and frontend nav/page guards.
