# GAP-021 New Product Development / Formula Governance Schema Design

## Summary

GAP-021 should harden the existing NPD, BOM/formula, recipe, and AI formulation surfaces without replacing them. The repository already has useful NPD project models, a rich Advanced BOM engine, recipe versioning, and an AI formulation UI. The next implementation slice should reconcile module ownership, permissions, endpoint guards, frontend guards, and migration ownership before adding new workflow depth.

## Design Goals

- Preserve existing routes and screens.
- Promote NPD, BOM/formula, and recipe surfaces into explicit module ownership.
- Protect formula and stage-gate workflows with dedicated permissions.
- Verify Alembic ownership before changing ORM models.
- Keep AI formulation approval separate from production formula release.
- Avoid a parallel formula architecture.

## Current Model Baseline

`NPDProject`, `NPDStageGate`, and `NPDPilotBatch` already cover project pipeline, stage gates, checklists, and pilot batches.

`AdvancedBOM`, `AdvancedBOMLine`, substitutes, conversion profiles, yield config, and BOM AI recommendations already cover a serious FMCG formula/BOM foundation.

`Recipe`, `RecipeItem`, and `ProcessParameter` already cover simpler formula versioning, ingredients, process parameters, approval, obsolescence, and duplication.

The current design should reuse these models.

## Module Ownership Design

Promote three module-owned routes:

| Module Key | Label | Route Prefix | Import Path |
|---|---|---|---|
| `npd` | New Product Development | `/npd-workflow` | `app.api.v1.endpoints.npd_workflow` |
| `bom` | BOM / Formula Governance | `/bom` | `app.api.v1.endpoints.bom` |
| `recipe` | Recipes / Formulations | `/recipes` | `app.api.v1.endpoints.recipes` |

Remove or comment the corresponding loose endpoint-route ownership entries after promotion to avoid duplicate registry ownership.

Keep frontend paths stable:

- `/dashboard/npd`
- `/dashboard/bom`
- `/dashboard/recipes`
- `/dashboard/ai/formulations`

## Permission Design

Recommended `npd` actions:

- `npd.view`
- `npd.create`
- `npd.edit`
- `npd.approve`
- `npd.advance`
- `npd.pilot`
- `npd.export`

Recommended `bom` actions:

- `bom.view`
- `bom.create`
- `bom.edit`
- `bom.delete`
- `bom.approve`
- `bom.release`
- `bom.archive`
- `bom.cost`
- `bom.ai`
- `bom.export`

Recommended `recipe` actions:

- `recipe.view`
- `recipe.create`
- `recipe.edit`
- `recipe.delete`
- `recipe.approve`
- `recipe.obsolete`
- `recipe.export`

High-risk actions such as approval, release, archive, delete, AI actioning, NPD stage advancement, and pilot batch completion must not be protected by broad `production.view` or authentication-only access.

## Role Grant Design

Admin/Owner receive full permissions.

Production Manager and Factory Manager receive view/create/edit plus selected advance/release capabilities where appropriate, but not broad delete by default.

Quality Manager receives NPD view/approve, recipe view/approve, BOM view/approve/release, compliance/cost visibility, and pilot review authority.

R&D/Product Development role does not currently exist. If added later, it should receive NPD/BOM/recipe create/edit and pilot permissions, but not final release unless paired with QA/regulatory approval.

Read-only Auditor receives view/export only.

AI permissions remain separate under `ai.*`; approving an AI formulation should not equal releasing a production BOM/recipe.

## Migration Ownership Design

GAP-021C should be reconciliation-first.

Before adding columns, inspect live and offline migration state for:

- `npd_projects`
- `npd_stage_gates`
- `npd_pilot_batches`
- `advanced_boms`
- `advanced_bom_lines`
- `bom_substitute_groups`
- `bom_substitutes`
- `bom_conversion_profiles`
- `bom_yield_configs`
- `bom_ai_recs`
- `recipes`
- `recipe_items`
- `process_parameters`

If tables are missing from Alembic ownership, add a safe additive reconciliation migration that creates missing tables and indexes only when absent.

If the tables already exist in the chain, GAP-021C should skip destructive changes and add only governance columns that are clearly needed.

## Additive Schema Recommendations

Do not add a large new formula approval system yet. Add only governance fields if inspection confirms they are missing and needed.

Recommended first-slice NPD fields:

- `company_id`
- `branch_id`
- `department_id`
- `owner_user_id`
- `approved_by_id`
- `approved_at`
- `cancelled_by_id`
- `cancelled_at`
- `launch_approved_at`
- `linked_bom_id`
- `linked_recipe_id`

Recommended first-slice stage-gate fields:

- `approver_user_id`
- `required_role`
- `decision_status`
- `rejected_at`
- `rejection_reason`

Recommended first-slice BOM/recipe governance fields only if absent:

- company/branch/factory scope fields
- explicit `approved_at`, `released_at`, `archived_at`
- status/action user ids
- audit reason fields for archive/obsolete/release

Use nullable fields and safe indexes. Do not enforce new FKs until existing data quality is known.

## API Endpoint Design

NPD:

- list/detail/dashboard: `npd.view`
- create/update/checklist: `npd.create` or `npd.edit`
- approve gate: `npd.approve`
- advance stage: `npd.advance`
- add/update pilot batch: `npd.pilot`

BOM:

- list/detail/dashboard/explosion/compliance: `bom.view`
- create/clone/add line/yield/substitute/conversion: `bom.create`
- update line/header: `bom.edit`
- delete line: `bom.delete`
- lifecycle approve/release/archive: corresponding `bom.approve`, `bom.release`, `bom.archive`
- costing: `bom.cost`
- AI recommendation run/action: `bom.ai`

Recipe:

- list/detail: `recipe.view`
- create/duplicate/add item/add process parameter: `recipe.create`
- update item/process/header: `recipe.edit`
- delete item/process/header: `recipe.delete`
- approve: `recipe.approve`
- obsolete: `recipe.obsolete`

## Frontend Design Implications

Replace nav guards:

- NPD pages from `production.view` to `npd.view`
- BOM pages from `production.view` to `bom.view`
- Recipe shortcut/pages from `production.view` to `recipe.view`

Add page-level guards where missing.

Guard action buttons:

- New NPD Project: `npd.create`
- Approve Gate: `npd.approve`
- Advance Stage: `npd.advance`
- Add Pilot Batch: `npd.pilot`
- New BOM / Create Group / New Profile: `bom.create`
- Archive / lifecycle actions: `bom.archive`, `bom.approve`, `bom.release`
- Recipe Create / Approve / Delete / Obsolete / Duplicate: corresponding `recipe.*`

## AI Formulation Boundary

AI formulation generation remains governed by `ai.create`.

AI formulation approval remains governed by `ai.approve`, but should be documented as recommendation approval, not production formula release.

Any future conversion from AI formulation to recipe/BOM must create a draft controlled record requiring `recipe.create` or `bom.create`, then normal approval/release permissions.

## Test Strategy

GAP-021J should add focused contract tests for:

- `npd`, `bom`, and `recipe` module ownership
- required permission codes in registry and seed data
- conservative role grants
- nav guards no longer relying only on `production.view`
- endpoint sources using dedicated permission dependencies
- AI formulation approval not claiming BOM/recipe release
- migration ownership smoke checks if GAP-021C adds a migration

## Acceptance Criteria for GAP-021B

GAP-021B is complete when this design documents the existing model baseline, module ownership direction, permission families, role grant approach, migration reconciliation strategy, endpoint guard expectations, frontend guard expectations, and AI formulation boundary without implementing migrations or refactors.
