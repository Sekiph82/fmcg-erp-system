# M29 — Maintenance / OEE Upgrade execution plan

## Scope and sequence

`TASKS.md` is authoritative. M29.S01 and M29.S02 contain implemented work that remains pending consolidated M29.S04 verification. Continue M29.S03 in dependency order:

1. M29.S03.T001 — standardize availability, performance, and quality calculations.
2. M29.S03.T002 — implement a consistent reason-code hierarchy.
3. M29.S03.T003 — connect explainable predictive risk to maintenance actions.
4. M29.S03.T004 — reconcile OEE calculations with recorded production facts.
5. M29.S04.T001–T003 — add the consolidated maintenance, calibration, and OEE verification coverage.
6. M29.S04.T004 — run milestone acceptance and record the independent code/security review.

Do not treat this plan as task authority or mark implementation tasks accepted before M29.S04 evidence exists.

## T001 calculation contract

- Store and return ratios from 0 to 1; render percentages only in the UI.
- Availability requires observed actual run time / planned time, where observed run time cannot exceed planned time less recorded downtime. If runtime is missing, availability remains unknown even when planned time and downtime are present.
- Performance is recorded total output / ideal output for the effective run time, using the recorded ideal cycle or machine rated capacity. Cap the reported ratio at 1.0.
- Quality is recorded good output / recorded total output.
- Leave a component unknown when its necessary source facts are absent or invalid. Do not treat missing production counts as perfect performance or quality.
- OEE is the product of all three known components; otherwise OEE remains unknown.
- Correct historical derived KPI columns from their existing source facts only. Preserve source production times, downtime, cycle rates, and output counts.

## T004 production-fact reconciliation

- Do not infer actual runtime from planned time minus downtime. A not-yet-started or unfinished order without an actual end time has unknown availability.
- Invalid runtime facts make time-dependent components unknown but do not erase an independently valid good/total quality ratio.
- Production-order quantity attainment is not a substitute for performance: the production order does not supply an ideal cycle or accepted-good count, so those components remain unknown until the source facts exist.
- Keep the OEE reconciliation checks separate from full M29 milestone verification; database migrations and the consolidated suite remain scheduled for M29.S04.

## Relevant implementation surfaces

- `backend/app/services/oee_calculation.py`
- `backend/app/services/production_service.py`
- `backend/app/crud/production_advanced.py`
- `backend/app/services/machine_operator_service.py`
- OEE schemas, API summary, migration, and production OEE UI/client types.
- Latest applicable audits: `docs/planning/GAP-007_APS_CAPACITY_PLANNING_AUDIT.md`, `docs/planning/GAP-022_TRUE_IOT_MACHINE_STREAMING_AUDIT.md`, and `docs/planning/GAP-023_ML_PREDICTIVE_MAINTENANCE_AUDIT.md`.

## Validation and review batch

Avoid full test suites after individual tasks. Use lightweight syntax/import, targeted lint/type checks, migration-head and diff checks while implementing. Run the consolidated M29 test, migration, frontend, and security/code-review campaign at M29.S04; run a focused earlier check only to diagnose a concrete failure or risky change. Preserve task-to-evidence traceability in `coordination/sessions/M29.Sxx.Txxx/CODEX_LOG_V01.md`.
