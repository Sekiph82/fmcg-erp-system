# AGENTS.md

## Project Identity

This repository is a large-scale FMCG factory ERP/MES platform.
It is intended to operate like an enterprise manufacturing system, not a toy app, demo, or lightweight admin panel.

The system must support:
- production operations
- inventory and warehousing
- procurement
- sales and customer operations
- finance/accounting-related workflows
- quality control
- utilities and infrastructure
- machine and factory-level traceability
- reporting and analytics
- future AI-assisted optimization

All work in this repository must preserve the direction of a serious, scalable, enterprise-grade manufacturing platform.

---

## General Operating Rules

When working in this repository:

- First inspect the current codebase before making decisions.
- Reuse existing architecture, patterns, components, folder structure, naming style, and conventions.
- Do not invent a parallel architecture when one already exists.
- Do not rewrite unrelated modules.
- Do not make broad refactors unless clearly necessary and directly relevant to the requested task.
- Prefer small, reviewable, production-safe changes.
- Prefer extending existing patterns over introducing new frameworks or structural styles.
- Keep implementation grounded in the existing repository, not generic best-practice fantasies.

Always assume this is a real business-critical application.

---

## Development Philosophy

This repository must evolve through controlled, modular, realistic implementation.

The preferred development style is:

1. inspect current implementation
2. identify what already exists
3. identify what is missing
4. implement the next logical missing part
5. keep the change coherent and testable
6. avoid speculative overengineering

Work should feel like continuing a factory system already under construction, not like starting a new side project every time.

---

## Repository Safety Rules

Never do the following unless explicitly required:

- rewrite the whole module
- rename core folders/files without strong reason
- replace current design system with a new one
- replace current state management approach with a different one
- replace current ORM/database approach with a different one
- replace current routing structure with a different one
- delete working code just to produce a cleaner rewrite
- introduce large abstractions without immediate usage
- create fake placeholder files only to appear productive
- hardcode fake data into production logic
- silently break existing pages, forms, APIs, routes, or imports

Minimize blast radius.

---

## Architecture Preservation

Before adding new code, always inspect and preserve:

- frontend framework and app structure
- backend framework and service structure
- ORM/schema/model conventions
- route and controller conventions
- validation style
- auth/permission style
- shared UI components
- shared table, modal, chart, and form patterns
- import/export architecture
- reporting/KPI architecture
- audit logging and status tracking conventions

If a shared pattern exists, reuse it.
If a shared helper exists, use it.
If a shared component exists, extend it before creating a new one.

---

## Code Change Discipline

Every change should be:

- scoped
- understandable
- reviewable
- reversible
- consistent with existing code

Prefer touching the minimum number of files required to implement the task correctly.

Do not change unrelated code "while you are there" unless it is directly blocking the requested work.

When adding new files:
- use naming conventions already used in the repository
- place them in the correct module structure
- avoid dumping logic into random utility folders

When editing existing files:
- preserve style and local conventions
- do not reformat huge unrelated sections
- do not mix unrelated logic changes into one edit

---

## UI / Frontend Rules

All UI work must follow the existing design language and component patterns in the repository.

When implementing frontend:
- reuse existing layouts, page containers, breadcrumbs, cards, tabs, filters, modals, and table components
- reuse existing create/edit/list/detail flow patterns
- preserve current spacing, alignment, field grouping, and navigation style
- preserve existing icon, badge, chip, and status display patterns
- use consistent labels and terminology across modules

Avoid:
- one-off UI styles that do not match the rest of the app
- inconsistent filter placement
- introducing a different UX pattern for similar CRUD screens
- duplicating table or form patterns that already exist elsewhere

For all complex module pages, prefer:
- summary cards at the top
- filters near the table/report/chart
- clean list/detail flow
- explicit status indicators
- export/import actions where the module pattern supports them

---

## Backend Rules

Backend changes must match the current backend architecture exactly.

When adding backend functionality:
- follow existing controller/service/repository or route/service patterns
- use existing validation mechanisms
- use existing error response style
- use existing auth and permission enforcement style
- use existing transaction handling approach
- use existing logging and audit patterns
- preserve existing response envelope patterns if the API uses them

Do not:
- create hidden business logic in controllers if the project uses service layers
- bypass validation
- hardcode IDs or assumptions about relational data
- introduce inconsistent status enums or magic strings

---

## Database / Schema Rules

All schema/model/entity work must respect current conventions.

When adding tables/entities/models:
- follow naming conventions exactly
- define required fields carefully
- define nullability intentionally
- add indexes where query patterns need them
- add uniqueness constraints where business logic needs them
- define relationships explicitly
- add audit/status fields if the codebase convention expects them
- preserve migration discipline

Do not:
- create schema fields "just in case" without purpose
- skip foreign keys if relationships are real
- invent inconsistent enum names
- collapse relational data into blobs when structured relationships are expected

Data model decisions must support real ERP/MES workflows.

---

## Validation Rules

All forms, imports, and APIs must validate input properly.

Validation must cover:
- required fields
- numeric constraints
- date/time formats
- enum/status values
- unit consistency
- relational references
- uniqueness where needed
- impossible ranges or invalid combinations

For imports:
- provide row-level error clarity
- validate headers
- validate required columns
- validate references to related records
- validate units and statuses
- avoid silent partial corruption

Never assume imported data is clean.

---

## CSV Import / Export Rules

This repository makes heavy use of CSV-based workflows.
Any module that fits the existing import/export pattern should support it properly.

When implementing CSV support:
- downloadable template headers must match actual create/edit form fields and backend schema expectations
- required fields must be obvious
- import preview should be used if the repository already supports it
- row-level error reporting should be consistent with other modules
- export columns should match meaningful business fields, not internal-only noise
- imports must not bypass validation

If the codebase already has a universal CSV engine, extend it instead of replacing it.

---

## Dashboard / KPI Rules

This ERP/MES project uses dashboards and KPI logic as serious operational tools.
They are not decorative charts.

When implementing dashboards or KPIs:
- centralize calculations in services/helpers where possible
- do not scatter KPI formulas across multiple UI files
- clearly distinguish estimated values vs actual values
- guard against division-by-zero
- guard against null/missing data
- use realistic KPI naming
- ensure drilldown is possible where architecture supports it
- preserve consistency with existing reporting style

All KPI outputs should support real operational decisions.

---

## Reporting Rules

Reports should be designed for managers, operators, planners, and technical teams.

Good report behavior includes:
- useful filters
- date range selection
- shift/department/line/machine filters where relevant
- CSV or Excel export if supported by the project
- clear totals and summaries
- readable table structure
- trend visibility when appropriate

Avoid reports that:
- dump raw unstructured data
- ignore pagination/performance
- calculate large datasets entirely in the UI when backend aggregation is more appropriate

---

## Permissions and Security

If the repository has role-based access control or module permissions:

- reuse the current permission pattern
- define permissions for new sections consistently
- do not expose privileged operations without checks
- do not create admin-only assumptions unless the repository already does so
- protect create/edit/delete/import/export actions as appropriate

Never bypass authorization patterns.

---

## Status and Workflow Consistency

Manufacturing systems depend on predictable statuses and transitions.

When adding statuses:
- use consistent naming
- use existing status style conventions
- make status progression realistic
- avoid too many overlapping statuses
- keep workflow states understandable

Do not create random status fields that conflict with existing business logic.

---

## Utilities Module Rules

The Utilities Module is a serious operational and costing module for factory infrastructure.

It must be treated as enterprise-grade and include realistic support for:
- utility assets
- utility asset categories
- meters and sensors
- readings
- electricity
- water
- soft water
- steam and boiler
- compressed air
- solar
- treatment chemicals
- wastewater/biological treatment
- utility transactions
- tariffs and bills
- cost allocation
- KPIs
- alarms and anomaly detection
- reports
- cross-module integration

When working on the Utilities Module:
- inspect what has already been built
- determine which phase is complete, partial, or missing
- continue from the next dependency-correct phase
- complete earlier partial phases before jumping to later phases
- implement one coherent slice at a time
- keep schema and CRUD foundations solid before advanced dashboards/reports

Utilities work must integrate cleanly with:
- Production
- Inventory
- Maintenance
- Quality
- Finance

Do not build the Utilities Module as an isolated island.

---

## Phase Progression Rule for Utilities Module

When implementing the Utilities Module, prefer this progression order:

1. module navigation and base scaffolding
2. schema foundations
3. core master data CRUD
4. readings infrastructure
5. shared transaction layer
6. operational submodules
7. tariffs/bills/cost allocation
8. KPI center
9. dashboards
10. alarms/anomaly handling
11. reports
12. cross-module integrations
13. seed/demo data
14. QA and hardening

If a previous phase is only partially complete, finish it before moving forward unless there is a strong dependency reason not to.

---

## Production Module Rules

The Production Module must behave like a real FMCG plant control layer.

Production-related work should support:
- production planning
- scheduling
- production orders
- work orders
- routing
- work centers
- shift logic
- time tracking
- downtime
- yield and waste
- batch tracking
- line/machine linkage
- QC linkage
- utility linkage
- traceability

Do not reduce Production to a simplistic “create order and mark done” flow.

---

## Inventory Rules

Inventory must behave like ERP inventory, not generic stock counting.

Inventory work should support:
- warehouse-level stock
- location-aware stock where relevant
- movement history
- material traceability
- raw material vs packaging vs finished goods logic
- inward and outward transaction integrity
- reservation or planned usage readiness where relevant
- stock impact from production and utility chemical usage where applicable

Never fake inventory by directly overwriting balances without movement logic if the system architecture expects transactions.

---

## Finance / Costing Rules

Finance and costing must be treated seriously.

When touching finance-related logic:
- preserve monetary precision
- preserve currency handling conventions
- keep cost allocation explicit
- do not hardcode pricing assumptions
- keep billing, tariff, invoice, payment, and allocation structures auditable
- ensure utility and production costs can eventually roll up into product costing

Avoid magical hidden calculations.

---

## Quality Rules

Quality features must be traceable and measurable.

When implementing quality-related logic:
- preserve lab result structure
- keep parameter names clear
- preserve pass/fail or acceptance logic where relevant
- link quality data to production, utilities, or batches when meaningful
- avoid burying critical quality fields in free text notes

---

## Maintenance Rules

Maintenance-related work must support equipment reliability, not just maintenance logs.

When integrating with maintenance:
- link repeated anomalies to maintenance flags where relevant
- preserve service intervals
- support calibration concepts for sensors/meters
- support criticality where relevant
- avoid fake integration without real references

---

## AI / Smart Logic Rules

This repository may include AI-assisted features, but AI should be grounded and operationally useful.

When implementing AI-related placeholders or future-ready structures:
- keep them data-driven
- avoid fake “AI” labels on ordinary filters
- prepare proper hooks for future recommendation or anomaly logic
- do not pretend predictive functionality exists unless it is actually implemented
- keep AI outputs explainable where possible

AI features must support real business decisions.

---

## Seed Data Rules

Seed/demo/sample data must be:
- realistic
- schema-consistent
- useful for UI review
- useful for dashboard population
- clearly separated from production logic
- not absurd or placeholder nonsense

Use realistic factory examples.

---

## Testing and Verification Rules

When making meaningful changes:
- check for compile/build issues if applicable
- run relevant tests if the repository supports them
- verify routes and imports
- verify list/create/edit flows
- verify no obvious runtime crashes from empty/null states
- verify schema relationships where relevant

At minimum, avoid shipping broken imports, broken routes, or clearly mismatched field names.

---

## Documentation Rules

When adding docs/comments:
- keep them useful
- keep them aligned with actual implementation
- do not create documentation for features that do not exist
- prefer concise but clear developer-facing notes
- update local module documentation if the repository uses it

---

## Decision Rules When Uncertain

When uncertain:
1. inspect existing similar modules
2. copy the repository’s dominant pattern
3. choose the smallest safe change
4. preserve backward compatibility
5. avoid architecture drift

If two options seem possible, choose the one that:
- reuses more of the existing codebase
- introduces less risk
- is easier to review
- better supports future ERP/MES scale

---

## Preferred Working Style Per Task

For every task:
- understand the exact request
- inspect relevant files first
- identify related existing patterns
- identify the minimum set of changes needed
- implement carefully
- keep changes coherent
- avoid unrelated edits

Think like a senior engineer extending a live manufacturing platform.

---

## Final Quality Bar

Every change should aim to be:
- enterprise-appropriate
- realistic for a factory ERP/MES
- consistent with the repository
- maintainable
- modular
- safe
- useful in real operations

Do not optimize for flashy output.
Optimize for correctness, continuity, and operational value.
