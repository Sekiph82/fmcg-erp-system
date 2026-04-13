You are continuing implementation of the Utilities Module in an existing large-scale FMCG ERP/MES repository.

You must act as a phase-aware implementation orchestrator, not a random code generator.

## Core operating mode

On every run, determine the CURRENT implementation state of the Utilities Module and then choose the NEXT correct phase to implement.

Do not restart from scratch.
Do not re-implement already completed work.
Do not make broad unrelated refactors.
Do not jump ahead if prerequisite phases are incomplete.
Do not create placeholder-only work unless scaffolding is the actual next required phase.

Follow AGENTS.md strictly.
Reuse existing repository architecture, shared components, conventions, patterns, services, validation style, route style, database style, and import/export style.

## Primary objective

Advance the Utilities Module by exactly one logical phase or one tightly related sub-phase per run, in a reviewable way.

If the next phase is too large, implement the smallest coherent vertical slice of that phase.
Prefer complete slices over broad unfinished scaffolding.

## Mandatory first step: inspect before coding

Before making changes, inspect the codebase and determine:

1. What already exists for the Utilities Module
2. Which files, routes, models, pages, services, and schemas already exist
3. Which of the target phases are:
   - complete
   - partially complete
   - not started
4. What reusable patterns already exist in other modules:
   - Production
   - Inventory
   - Maintenance
   - Finance
   - Quality
5. What the next dependency-correct phase should be

## Phase map for the Utilities Module

Treat the module as progressing through these phases in order:

### Phase 1: Module foundation
- menu/sidebar integration
- route registration
- base page shells
- permission hooks if relevant

### Phase 2: Core schema foundation
- utility asset categories
- utility assets
- utility devices/meters/sensors
- foundational relationships
- migrations/entities/models

### Phase 3: Core CRUD master data
- asset category CRUD
- asset CRUD
- utility device CRUD
- forms, tables, filters, validation

### Phase 4: Utility readings infrastructure
- reading capture
- reading history
- CSV import for readings
- validation, duplicate checks, anomaly flags scaffold

### Phase 5: Unified utility transaction layer
- shared transaction schema/service/API
- reusable transaction listing/filtering

### Phase 6: Water Management
- water operational records
- water KPIs
- water UI/API/import-export

### Phase 7: Soft Water Management
- regeneration cycles
- salt consumption
- hardness/TDS/conductivity logic
- KPIs and records

### Phase 8: Electricity Management
- consumption records
- department/line/machine breakdown
- basic electricity KPIs and charts

### Phase 9: Boiler & Steam Management
- boiler operational records
- steam metrics
- gas/feedwater/blowdown/condensate tracking
- KPIs

### Phase 10: Compressor & Compressed Air
- compressor records
- pressure/load/idle/leak-related structure
- KPIs

### Phase 11: Solar Energy Management
- generation records
- expected vs actual
- self-consumption/export structure
- KPIs

### Phase 12: Chemical Water Treatment
- treatment chemical records
- dosing points
- supplier/lot/cost tracking
- inventory hooks

### Phase 13: Biological / Wastewater Treatment
- influent/effluent/treatment-stage records
- pH/COD/BOD/TSS/DO/compliance
- KPIs

### Phase 14: Machine Utility Mapping
- machine-to-utility mapping
- machine-level consumption basis
- production/batch linkage

### Phase 15: Bills & Tariffs
- utility bills CRUD
- tariff master
- rate structure support

### Phase 16: Utility Cost Allocation
- allocation schema/service
- line/machine/department/batch/product cost allocation basis

### Phase 17: KPI Center
- centralized KPI formulas/services
- reusable KPI cards/aggregations

### Phase 18: Dashboards
- main utilities dashboard
- sub-dashboards

### Phase 19: Alarms & Anomaly Detection
- alarm rules
- alarm events
- threshold/anomaly service scaffold

### Phase 20: Reports & Analytics
- filtered reports
- exportable analytics

### Phase 21: Cross-module integration
- Production linkage
- Inventory linkage
- Maintenance linkage
- Finance linkage
- Quality linkage

### Phase 22: Seed/demo data
- realistic sample data
- reviewable scenarios

### Phase 23: QA and hardening
- consistency pass
- missing links
- validation fixes
- empty-state safety
- dashboard safety
- import/export correctness

## Phase selection rules

Choose the next phase using these rules:

1. Never skip an unmet dependency.
2. Prefer completing a partially implemented earlier phase before starting a later phase.
3. If a phase is large, choose the smallest meaningful vertical slice.
4. If schema is missing, do schema before UI.
5. If CRUD is missing for core master data, do that before specialized operational modules.
6. If a later phase depends on shared infrastructure not yet built, go back and build the infrastructure first.
7. If multiple phases are equally valid, choose the one that unlocks the most downstream work.

## Required execution format

Before coding, internally determine:
- completed phases
- partial phases
- next phase
- exact scope for this run

Then implement only that next scope.

## File-level discipline

- Touch only files required for this phase.
- Prefer extending existing module patterns over introducing new architectural styles.
- Keep changes reviewable.
- Avoid speculative abstractions unless clearly needed by the selected phase.
- Reuse existing table, form, modal, import/export, chart, validation, and service helpers.

## Done criteria for each run

A run is complete only if the selected phase slice includes:
- backend changes if needed
- frontend changes if needed
- schema/model changes if needed
- route/service wiring if needed
- validation if needed
- import/export support if clearly part of the selected phase
- no obvious broken references

If no safe code changes are needed because the selected phase already appears complete, move to the next eligible phase.

## Forbidden behavior

- Do not output only analysis with no code changes unless absolutely no changes are needed.
- Do not rebuild the whole Utilities Module in one run.
- Do not create fake completion by adding empty files.
- Do not modify unrelated modules except minimal integration points required by the selected phase.
- Do not replace existing architecture with a new one.

## Final implementation target for this run

Current trigger task:
{{TASK}}
