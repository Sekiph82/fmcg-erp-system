# CODEX Implementation Log — M27.S03.T002

## Scope

Implemented the M27.S03.T002 deviation and quality-gate waiver approval workflow in the canonical FMCG ERP repository. The linked acceptance material for this task is the latest M27 HACCP workflow audit and implementation notes in `docs/planning/GAP-017_HACCP_WORKFLOW_AUDIT.md` and `docs/planning/GAP-017_HACCP_WORKFLOW_IMPLEMENTATION_NOTES.md`.

## Changes

- Added a version-specific `QualityGateWaiver` record and migration `20261029_0032` with request, decision, expiry, and revocation audit fields, scoped uniqueness for pending requests, database checks, and restrictive foreign keys.
- Added API endpoints to list, request, approve/reject, and revoke waivers. Requests must cite a linked, open deviation and match the exact GRN line, production order, lot, or shipment line represented by the gate's module/event.
- Enforced noncritical-only eligibility, a required reason, different requester and approver, quality approval permission, and a fixed 24-hour approval period. Expiry or serialized revocation ends approval; a later deviation status change does not rewrite an already-approved decision.
- Applied approved waivers only to the exact gate-definition version and business scope. A waiver can satisfy missing required-template evidence; failed or unresolved QC inspections, critical gates, and hold/quarantine/release eligibility controls continue to block.
- Scoped request, approval, revocation, and list access to every warehouse in the record's scope. Approval and revocation serialize on the same module/event advisory lock as gate use.
- Added independent deviation resolution/closure checks: resolution requires root cause and immediate action and a separate quality approver; closure requires a second reviewer distinct from both reporter and resolver; closed deviations are immutable.

## Verification

- `python -m compileall -q backend/app backend/alembic/versions/20261029_0032_quality_gate_waivers.py backend/tests/test_m27_s03_t002_waiver_approval_db.py backend/tests/test_m27_s03_t002_waiver_contract.py` — passed.
- Focused waiver, gate-definition, receiving, production, finished-goods, and dispatch tests — **72 passed**.
- Fresh disposable PostgreSQL 16 migration through `20261029_0032` and task integration test — **1 passed**. The runner used a task-named database and random container bound to loopback only, synthetic records, no database password or volume mount, and removed the container afterward. Image ID: `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`.
- `git diff --check` — passed.
- Independent read-only review — no remaining actionable findings after fixes for warehouse-scope authorization and advisory-lock serialization.

## Notes

The task did not specify a waiver duration or capability matrix. The implementation uses the existing quality permissions and access scopes and a fixed 24-hour period as the synthetic operational policy. A separate broad test collection attempt included the existing T001 DB test file, which currently has a Python syntax error from a literal `\n` at its final line; that unrelated file was not modified. T001's own task log records its isolated database evidence.
