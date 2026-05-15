# GAP-007 Advanced Manufacturing Capacity Planning / APS Audit

## Scope

Planning document requirement: advanced manufacturing capacity planning / APS must support finite capacity scheduling, machine calendars and downtime windows, operator skill matrix, product-family changeover time, CIP/cleaning time, bottleneck detection, drag-and-drop schedule board, schedule simulation before release, automatic rescheduling after breakdown, and planned-vs-actual production variance.

This audit inspects what is already present before adding schema or behavior.

## Current Repo Status

Overall status: **Partial**.

The repo has meaningful production, advanced production, MRP, and MPS foundations. It does not yet have a full APS engine.

## Existing Foundations

| Area | Current status | Evidence | Notes |
|---|---|---|---|
| Production plans/orders | Existing | `backend/app/models/production.py`, `backend/app/api/v1/endpoints/production.py`, `frontend/src/lib/production.ts` | Plans, plan lines, production orders, lifecycle actions, material consumption, finished-goods receipt, downtime logs, OEE summary, and production report exist. |
| Work centers | Existing | `backend/app/models/production_advanced.py`, `frontend/src/app/dashboard/production/work-centers/page.tsx` | Work centers support machine/line/cell/manual type, capacity value/UOM, setup time, ideal cycle time, labor/machine hourly costs, location, department, and status. |
| Routing | Partial | `Routing`, `RoutingStep`, routing page | Product routings and steps exist with work center, standard time, setup time, and parallel flag. Missing alternate resources, product-family changeover matrix, yield-dependent routing, and validated route-to-order generation. |
| Work orders | Partial | `WorkOrder`, `/production-adv/work-orders`, work-order UI | Executable operations exist but are manually created and not clearly generated from routing/production orders by an APS service. |
| Shifts | Existing | `Shift`, shifts page, schedule shift reference | Shift definitions exist. Missing machine calendars, exceptions, holidays, planned maintenance windows, and per-line availability calendars. |
| Scheduling | Partial | `ProductionSchedule`, `/production-adv/schedules`, scheduling page | Machine-level schedules exist and same-work-center overlap detection flags conflicts. Missing finite-capacity solver, drag/drop board, simulation, automatic rescheduling, and release workflow. |
| Downtime | Partial | `DowntimeLog`, `DowntimeEvent`, downtime pages | Downtime capture exists. Missing direct use of downtime windows as planning constraints and automatic rescheduling after breakdown. |
| OEE / variance | Partial | `OEERecord`, `production_service._compute_oee`, reports | OEE and planned-vs-actual production quantities are present. Missing APS feedback loop from actuals into future capacity promises. |
| MRP / demand planning | Existing/partial | `backend/app/api/v1/endpoints/mrp.py` | MRP runs, forecasts, suggestions, and conversion hooks exist. Needs tighter handoff from MRP suggestions into finite-capacity production schedules. |
| MPS / capacity planning | Partial | `backend/app/api/v1/endpoints/mps.py`, `mps_capacity_service` imports | MPS exposes capacity scheduling/heatmap/reschedule service hooks. Needs audit in GAP-007B before deciding whether to extend MPS or production-advanced as the APS home. |
| Frontend module surface | Existing/partial | `frontend/src/app/dashboard/production/advanced`, `scheduling`, `routing`, `work-centers` | Many screens exist, mostly list/create/edit flows. Scheduling UI is table/modals, not an interactive planning board. |
| CSV/import support | Existing/partial | `backend/app/api/v1/endpoints/bulk_import.py` adapters for work centers, routings, routing steps, production schedules | Useful for master-data setup. Missing APS-specific import templates for calendars, downtime windows, changeover matrix, and operator skills. |

## Important Gaps

| Requirement | Current repo status | Gap |
|---|---|---|
| Finite capacity scheduling | Partial | Conflict detection exists, but no solver assigns operations into available windows based on capacity, routing sequence, priorities, shifts, or downtime. |
| Machine calendars and downtime windows | Missing/partial | Shift definitions and downtime logs exist, but there is no resource calendar model for availability, maintenance windows, holidays, or planned downtime. |
| Operator skill matrix | Missing | Labor logs store free-text operator data, but there is no operator skill/qualification table connected to scheduling. |
| Changeover time by product family | Missing | Routing steps have setup time, but no product-family changeover matrix or sequence-dependent setup calculation. |
| CIP/cleaning time | Missing/partial | Time-tracking categories include cleaning and routing setup exists, but CIP/cleaning is not modeled as a schedule constraint with product/category/allergen rules. |
| Bottleneck detection | Partial | OEE/AI insight flags can identify low OEE/high downtime, but no capacity load vs available capacity bottleneck report exists. |
| Drag-and-drop schedule board | Missing | Current scheduling UI is a table with modals. |
| Schedule simulation before release | Missing | No dry-run/simulation entity or endpoint for proposed schedule changes. |
| Automatic rescheduling after breakdown | Missing/partial | Downtime and conflict APIs exist, but no rescheduler consumes downtime events to move affected work. |
| Planned-vs-actual production variance | Partial | Production reports and OEE records include planned/actual quantities and downtime; not yet used for capacity model calibration. |

## Risks Found

- Production planning logic is split between base production, advanced production, MRP, MPS, shop-floor, and calendar modules. GAP-007B must choose one integration path rather than creating a parallel APS island.
- `ProductionSchedule` can be created even if a conflict exists; the conflict is flagged, not blocked or routed through approval.
- Several advanced production endpoints use only authentication dependency in the inspected snippets, not the full scoped production permission helper used by base production orders.
- Scheduling filters accept dates as strings in CRUD, while the schema uses datetimes. GAP-007B should normalize this before deeper scheduling logic.
- Work centers have capacity values but not calendarized available minutes/capacity buckets.
- Operator information is largely free text, which cannot support skill-constrained scheduling.

## Recommended GAP-007B Design Direction

Use an additive APS layer that reuses existing production-advanced entities:

- Keep `WorkCenter`, `Routing`, `RoutingStep`, `WorkOrder`, `Shift`, and `ProductionSchedule`.
- Add explicit resource-calendar and planning-rule concepts only where missing.
- Prefer services that calculate capacity buckets and schedule proposals before adding UI-heavy board work.
- Keep existing schedule table working; add simulation/preview first, then later interactive board.

Candidate next design pieces:

- `WorkCenterCalendar` or `ResourceCalendar`
- `WorkCenterCalendarException` / downtime window
- `ProductFamily` or mapping for changeover rules if no existing family field can be reused
- `ChangeoverRule`
- `CIPRule` or cleaning rule
- `OperatorSkill` / `WorkCenterSkillRequirement`
- `ScheduleSimulationRun`
- `ScheduleSimulationOperation`
- APS service helpers for capacity buckets, conflict/blocking checks, and dry-run scheduling

## Files Inspected

- `backend/app/models/production.py`
- `backend/app/api/v1/endpoints/production.py`
- `backend/app/schemas/production.py`
- `backend/app/crud/production.py`
- `backend/app/services/production_service.py`
- `backend/app/models/production_advanced.py`
- `backend/app/api/v1/endpoints/production_advanced.py`
- `backend/app/schemas/production_advanced.py`
- `backend/app/crud/production_advanced.py`
- `backend/app/api/v1/endpoints/mrp.py`
- `backend/app/api/v1/endpoints/mps.py`
- `backend/app/core/module_registry.py`
- `frontend/src/lib/production.ts`
- `frontend/src/lib/productionAdvanced.ts`
- `frontend/src/app/dashboard/production/advanced/page.tsx`
- `frontend/src/app/dashboard/production/work-centers/page.tsx`
- `frontend/src/app/dashboard/production/routing/page.tsx`
- `frontend/src/app/dashboard/production/scheduling/page.tsx`
- `backend/alembic/versions/d4e5f6a7b8c9_advanced_production_module.py`
- `backend/app/api/v1/endpoints/bulk_import.py`

## GAP-007A Result

GAP-007A is complete as an audit-only task. No application code was changed.
