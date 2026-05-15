# GAP-007 - Advanced Manufacturing Capacity Planning / APS Implementation Notes

## Status
GAP-007A through GAP-007L are complete.

This slice hardened the existing Advanced Planning Suite instead of creating a duplicate APS module.

## Files Changed

Backend:

- `backend/app/models/planning.py`
- `backend/app/services/planning_capacity_service.py`
- `backend/app/api/v1/endpoints/planning.py`
- `backend/app/core/module_registry.py`
- `backend/app/db/seed.py`
- `backend/alembic/versions/20260514_0010_aps_planning_tables.py`
- `backend/tests/test_gap007_aps_planning_service.py`

Frontend:

- `frontend/src/lib/planning.ts`
- `frontend/src/app/dashboard/planning/page.tsx`
- `frontend/src/app/dashboard/planning/bottlenecks/page.tsx`
- `frontend/src/components/nav-config.tsx`

Planning docs:

- `docs/planning/GAP-007_APS_CAPACITY_PLANNING_AUDIT.md`
- `docs/planning/GAP-007_APS_CAPACITY_PLANNING_SCHEMA_DESIGN.md`
- `docs/planning/GAP-007_APS_CAPACITY_PLANNING_IMPLEMENTATION_NOTES.md`

## What Was Implemented

### Migration Ownership

The repository already had APS ORM models, schemas, services, and endpoints, but Alembic did not own the planning tables.

Added migration:

- `20260514_0010_aps_planning_tables.py`

The migration creates:

- `planning_scenarios`
- `resource_calendars`
- `operation_queue`
- `capacity_load_snapshots`
- `changeover_matrix`
- `planning_bottlenecks`
- `planning_ai_recs`
- `planning_simulations`

Live local PostgreSQL verification confirmed:

- `alembic current` is `20260514_0010`
- all APS tables exist
- `operation_queue` columns match the intended ORM-backed scheduling payload

### Scheduler Service Reconciliation

The finite scheduler previously referenced related-model fields that do not exist:

- `RoutingStep.step_name`
- `RoutingStep.output_qty_per_hour`
- `MPSLine.product_name`
- `MPSLine.product_code`

The service now uses existing model fields:

- `RoutingStep.operation`
- `RoutingStep.standard_time_minutes`
- `Product.name`
- `Product.sku`
- `WorkCenter.capacity`

Operations with no work center now become blocked operations with a clear block reason instead of producing invalid capacity snapshot rows.

### API Hardening

The planning API no longer generates fake user IDs.

Scenario creation, AI recommendation actions, and simulation publishing now use the authenticated user context.

Planning routes now require planning permissions:

- read: `planning.view`, `planning.view_all`, `planning.view_own_scope`
- create: `planning.create`, `planning.create_all`, `planning.create_own_scope`
- edit: `planning.edit`, `planning.edit_all`, `planning.edit_own_scope`
- calculate: `planning.calculate`, `planning.calculate_all`, `planning.calculate_own_scope`
- approve/publish/lock: `planning.approve`, `planning.approve_all`, `planning.approve_own_scope`

### Frontend Permission UX

The Advanced Planning Suite sidebar now uses `planning.view` instead of `production.view`.

Frontend planning action controls now use explicit planning permissions:

- scenario creation is visible only to users with planning create permission
- AI agent execution is visible only to users with planning calculate permission
- AI accept/reject actions are visible only to users with planning approve permission
- bottleneck resolution is visible only to users with planning edit permission

The AI recommendation action client no longer sends `actioned_by_id`; the backend decides the acting user from the session.

The AI recommendation action request schema now treats `actioned_by_id` as optional for compatibility, while the endpoint ignores client-supplied actor data and records the authenticated user as the actor.

### Permissions And Role Seeds

`planning` is now a module-owned backend registry entry.

The duplicate non-core endpoint route registration for `planning` was removed to avoid double registration.

Seeded planning permissions include broad and scoped variants:

- `planning.view_all`
- `planning.view_own_scope`
- `planning.create_all`
- `planning.create_own_scope`
- `planning.edit_all`
- `planning.edit_own_scope`
- `planning.calculate_all`
- `planning.calculate_own_scope`
- `planning.approve_all`
- `planning.approve_own_scope`

Production-oriented roles received conservative APS grants:

- CEO/COO: broad planning visibility and executive calculate/approve where appropriate
- CTO/Data Manager: planning visibility for operational/system oversight
- Company Admin: planning visibility
- Factory Manager: broad visibility with scoped create/edit/calculate/approve
- Production Manager: broad visibility with scoped create/edit/calculate/approve
- Production Supervisor: scoped view/create/edit/calculate
- Read Only Auditor / Shop Floor Operator: scoped view only

## Checks Run

Backend:

- `python -m py_compile` for migration, planning models/schemas/endpoints/services, module registry, seed, and GAP-007 tests
- `python -m alembic heads`
- `python -m alembic history -r 20260511_0040:20260514_0010`
- `python -m alembic upgrade 20260511_0040:20260514_0010 --sql`
- live `docker compose --env-file .env.development exec -T backend python -m alembic upgrade head`
- live schema verification against local PostgreSQL
- `pytest tests/test_gap007_aps_planning_service.py -q`

Frontend:

- `npm run type-check`
- static checks for removed `actioned_by_id` and planning nav permissions

## Remaining Production-Hardening Follow-Ups

These are not blockers for GAP-007, but they should be handled in later APS work:

- Apply true factory/line/product-category scope filtering to planning scenario reads and writes once planning records carry those scope fields.
- Add richer planner UI for calendars, changeover maintenance, scenario create/edit, and schedule simulation.
- Add browser E2E coverage for APS planning pages once seeded planner personas are available.
- Connect resource calendars to maintenance downtime, generic calendar events, and shift templates.
- Add operator skill and CIP/allergen cleaning constraints only after their source modules provide reliable operational inputs.
- Replace greedy scheduling with a more capable optimizer only after the current deterministic engine is fully tested and trusted.
