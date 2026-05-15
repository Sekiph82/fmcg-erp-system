# GAP-007B - APS Capacity Planning Schema Design

## Gap
Advanced Manufacturing Capacity Planning / APS

## Decision
Do not create a second APS architecture.

The repository already contains an advanced planning model and service layer under:

- `backend/app/models/planning.py`
- `backend/app/schemas/planning.py`
- `backend/app/services/planning_capacity_service.py`
- `backend/app/services/planning_scenario_service.py`
- `backend/app/services/planning_bottleneck_service.py`
- `backend/app/services/planning_simulation_service.py`
- `backend/app/services/planning_ai_service.py`
- `backend/app/api/v1/endpoints/planning.py`

GAP-007 should harden and reconcile this existing layer instead of adding duplicate planning tables.

## Current Schema Assets

The existing APS schema already defines the right core concepts:

| Table / Model | Purpose | Design Status |
|---|---|---|
| `planning_scenarios` / `PlanningScenario` | Named planning runs linked to MPS plans and planning horizon | Keep |
| `resource_calendars` / `ResourceCalendar` | Day-level work-center availability, holiday, and maintenance availability | Keep, later integrate with generic calendar and maintenance |
| `operation_queue` / `OperationQueue` | Finite scheduled operations generated from MPS/routing inputs | Keep |
| `capacity_load_snapshots` / `CapacityLoadSnapshot` | Per-work-center/date capacity utilization snapshots | Keep |
| `changeover_matrix` / `ChangeoverMatrix` | Work-center product-family transition/changeover time | Keep |
| `planning_bottlenecks` / `PlanningBottleneck` | Detected constrained resources and recommendations | Keep |
| `planning_ai_recs` / `PlanningAIRec` | Planner-facing AI recommendations, not auto-executed | Keep |
| `planning_simulations` / `PlanningSimulation` | What-if frame for schedule changes and published impact | Keep |

## Migration Finding

The planning ORM models are imported in `backend/app/models/__init__.py` and the planning route is registered in `backend/app/core/module_registry.py`, but no Alembic migration file currently declares the APS planning tables.

GAP-007C should therefore create an additive migration for the existing planning model tables, unless live database inspection proves they are already owned by an existing migration under a different name.

## Service/Schema Reconciliation Needed

The finite scheduling service is valuable but not yet aligned with every related model:

| Area | Current Issue | Recommended Fix |
|---|---|---|
| Routing step name | `planning_capacity_service.py` reads `step.step_name`, but `RoutingStep` exposes `operation` | Use `RoutingStep.operation` when building `OperationQueue.step_name` |
| Routing throughput | Service checks `step.output_qty_per_hour`, but `RoutingStep` exposes `standard_time_minutes` and `WorkCenter.capacity` | Derive run minutes from `standard_time_minutes` first; fall back to work-center capacity/default rate |
| MPS product display | Service reads `MPSLine.product_name` / `product_code`, but `MPSLine` exposes `product` relationship and `Product.name` / `Product.sku` | Load/join `Product` and cache `Product.name` / `Product.sku` in `OperationQueue` |
| User attribution | Planning endpoint uses a generated UUID as auth placeholder | Replace `_user_id()` with current authenticated user before enabling writes broadly |
| Route security | Planning endpoints currently expose create/calculate/lock actions without scoped permissions | Apply `planning.view_*`, `planning.edit_*`, `planning.calculate_*`, and production/factory scope checks in later GAP-007 tasks |
| Calendar overlap | `ResourceCalendar` and generic calendar resources both exist | Keep `ResourceCalendar` as production work-center capacity calendar; later add explicit synchronization/import from generic calendar or maintenance downtime |

## Minimal Additive Schema Direction

GAP-007C should focus on migration ownership for the existing APS tables:

1. Create `planning_scenarios`.
2. Create `resource_calendars`.
3. Create `operation_queue`.
4. Create `capacity_load_snapshots`.
5. Create `changeover_matrix`.
6. Create `planning_bottlenecks`.
7. Create `planning_ai_recs`.
8. Create `planning_simulations`.
9. Add the same unique constraints and key indexes already expressed in the ORM.
10. Do not add new speculative APS tables in this migration.

## Deferred Schema Ideas

These are not part of the immediate migration unless a later implementation task proves they are required:

| Future Need | Preferred Direction |
|---|---|
| Operator skill constraints | Integrate existing `OperatorProfile`, `OperatorSkillCert`, and training skill matrix; do not create duplicate skill tables |
| CIP / cleaning constraints | Reuse `OperationQueue.cleanup_minutes` first; later add a small cleaning-rule table only when linked to allergen/QMS data |
| Machine downtime windows | Feed maintenance and downtime events into `ResourceCalendar` or a derived calendar import job |
| Alternate resources | Add only after routing/work-center substitution rules are designed |
| Drag/drop schedule board | Use existing `OperationQueue` order/timing fields first; add board-specific fields only if frontend needs persistable draft moves |

## Acceptance Criteria For GAP-007B

- Existing APS planning models, services, schemas, and endpoints are documented.
- The design avoids duplicate APS architecture.
- Required migration work for GAP-007C is identified.
- Service/model mismatches are explicitly listed before implementation.
- Later tasks have a conservative, dependency-correct direction.

## GAP-007C Recommendation

Proceed with an additive Alembic migration for the existing planning models and a small compile/import check. After the migration exists, GAP-007D/F should reconcile service field usage before relying on live scheduling calculations.
