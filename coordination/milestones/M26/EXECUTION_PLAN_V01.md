# M26 — Machine & Operator Intelligence execution plan

## Scope and dependencies

- Canonical tracker: root `TASKS.md`; M26 is the next explicitly selected milestone after M24.
- Dependencies are ready for this software scope: M11 maintenance core, M14 HR/operator/shift foundations, and M22/M23 are implemented; M25 is closed. M11/M14 remain partial only for later enterprise extensions.
- M26 contains 12 tasks across qualification matrix (S01), performance intelligence (S02), anomaly/feedback (S03), and closure (S03.T004).
- No owner business decision is listed for M26. Qualification rules are configured as data; no real employees, factory assets, or certification records are assumed or seeded.

## Existing architecture and acceptance references

- Reuse `Machine`, `OperatorProfile`, `OperatorSkillCert`, `WorkOrderAssignment`, `SkillMaster`, and `EmployeeSkillProfile`; do not add a duplicate skill registry or employee skill profile.
- `docs/planning/GAP-007_APS_CAPACITY_PLANNING_AUDIT.md` identifies the missing operator skill matrix. `GAP-007_APS_CAPACITY_PLANNING_SCHEMA_DESIGN.md` and `GAP-007_APS_CAPACITY_PLANNING_IMPLEMENTATION_NOTES.md` direct future APS work to integrate existing machine/operator and training skill models.
- `docs/planning/GAP-022_TRUE_IOT_MACHINE_STREAMING_AUDIT.md` keeps `machine_operator` distinct from IoT and flags missing auth/permissions on existing machine-ops routes. Do not expose new unauthenticated write surfaces; include scoped authorization and actor audit in the assignment enforcement slice before it is accepted.
- Existing skill/certification expiry fields and statuses in `OperatorSkillCert` should be preserved; S01.T002 owns expiry behavior and S01.T003 owns enforcement.

## Implementation batches

1. **S01.T001–T004, qualification matrix:** connect qualifications to canonical training skills; define machine/work-center requirements, expiry status behavior, assignment/execution checks, and audited supervisor override. Keep unsupported assignment blocked unless the approved override path is used.
2. **S02.T001–T004, operational performance:** derive operator, machine, labor-cost, and shift/team comparisons from existing authenticated production/labor/runtime facts; preserve source IDs and units and label unavailable facts explicitly.
3. **S03.T001–T003, anomaly and feedback:** S03.T001 uses a transparent machine-specific rule for recorded downtime intervals: compare target-period events with the preceding 30 days, require at least five valid non-overlapping prior events, and flag durations above the prior-event median plus three median absolute deviations. Correlate only recorded downtime/quality/waste in T002 and provide evidence-backed handoff to maintenance/training/planning in T003. Do not claim predictive AI or live IoT behavior where no such evidence exists.
4. **S03.T004, acceptance:** run one consolidated disposable-PostgreSQL/migration/regression/frontend/E2E campaign, one independent code/security review, resolve findings, then accept task rows with evidence.

## Validation and safety

- During implementation use compile/import checks and focused tests only for a concrete failure or high-risk invariant. Do not run a full suite after each task.
- At milestone acceptance validate fresh Alembic upgrade, authorization and scope isolation, status/expiry behavior, assignment atomicity and audit lineage, relevant UI/type/lint/API parity, and synthetic mocked E2E workflows.
- Do not use live credentials, production databases, real employee data, or factory devices. Keep M26 software evidence separate from any physical-factory acceptance.
- The initial origin fetch found `HEAD == origin/main == 0db8dc68c971661dbda55f6992f3b4e70e4da84d` (0/0 divergence). The worktree contains extensive unrelated local changes; preserve them and publish only after a scoped safety review.
