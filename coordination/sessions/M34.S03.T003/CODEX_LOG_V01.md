# M34.S03.T003 — Supplier qualification, preference, and procurement blocking

## Scope and decisions

Implemented the current TASKS.md scope using the existing supplier governance fields and GAP-009 audit direction. New supplier records begin in `PENDING`; only a user with `procurement.approve` can record a qualification or preferred-list decision. Every decision requires a reason and writes a master-data audit event with actor, workflow, permission, decision, and reason. Approval dates and approver lineage are cleared when a supplier leaves `APPROVED`; a non-approved supplier is also removed from the preferred list.

An approval starts today when no effective-from date is supplied. Preferred status requires an active supplier with a currently effective `APPROVED` qualification. Explicit `PENDING`, `CONDITIONAL`, `SUSPENDED`, and `REJECTED` suppliers cannot receive new procurement commitments. Legacy suppliers whose qualification is unrecorded remain usable for backward compatibility; that legacy state is displayed as `LEGACY / UNRECORDED`, not represented as an approval.

Eligibility is checked for direct PO creation, PR-to-PO conversion, PO approval and ordering, RFQ award proposal and final award approval, BPA creation, and BPA release. Existing receipts and settlement of previously created orders are not blocked. Supplier bulk import has a restricted schema, rejects governance columns, and creates pending, non-preferred records without approval lineage.

No migration or owner data was needed. Test records and PostgreSQL contents were synthetic and task-owned.

## Changed areas

- Supplier qualification/preference request schemas, endpoints, date windows, and audited actor lineage.
- Procurement commitment eligibility helper and checks across PO, PR conversion, RFQ award, and BPA paths.
- Supplier import schema and engine-level rejection of governance fields.
- Supplier master and procurement scorecard status display and permission-gated governance controls.
- Focused route, import, eligibility, audit, and disposable-PostgreSQL tests.

## Verification evidence

- Python compile checks passed for the changed backend modules.
- Combined supplier stewardship and M34 sourcing/BPA/scorecard/governance regression run: **59 passed, 11 skipped**. The skips are existing task-database-gated tests and the opt-in T003 PostgreSQL test in the non-database run.
- Task-owned disposable PostgreSQL 16.6 database on loopback: Alembic upgrade to head succeeded; T003 persistence, approval actor/reason audit, preference, expiry-window PO denial, suspension cleanup, and no-PO-write test: **2 passed** (including database-target guard).
- Frontend `npm run type-check`: passed.
- Targeted ESLint for supplier master, procurement scorecard, and supplier API types: passed.
- Targeted Ruff on supplier endpoint/schema and T003/regression test files: passed.
- `git diff --check`: passed (Git emitted line-ending normalization warnings for existing Windows working files).
- An independent read-only review initially found a supplier-import approval bypass. The import path was changed to reject qualification/preference/approval columns and force pending state; the reviewer’s final read-only review reported no remaining findings in the reviewed scope.

The broad Ruff invocation over large pre-existing procurement/import modules reported repository lint findings outside the targeted clean set; no full-module Ruff pass is claimed.

## Acceptance boundary

This verifies local synthetic behavior and persistence. It does not claim real supplier qualification evidence, production acceptance, or approval of any real supplier.
