# M27.S02.T001 — Codex implementation evidence

**Status:** COMPLETE — configured mandatory receiving gates now stop GRN posting until the required incoming QC inspections are accepted and passed.

**Acceptance source:** The root `TASKS.md` row `M27.S02.T001 — Receiving gate` is authoritative. No task-specific audit was linked. Reviewed `docs/planning/GAP-008_WAREHOUSE_MANAGEMENT_DEPTH_AUDIT.md` and schema design, plus `docs/planning/GAP-017_HACCP_WORKFLOW_AUDIT.md`. Existing code already modeled GRNs, incoming QC inspections, required QC templates, and quality gate definitions, but GRN posting did not consult gate configuration or QC evidence.

## Implemented

- An active mandatory quality gate for `ON_RECEIPT` in `procurement` applies to a GRN using its received date. For every accepted GRN line, posting requires one inspection per required template with incoming QC type, mandatory/blocking/release flags, and an `ACCEPT` decision in `PASSED` status. A missing inspection returns 422 before stock movement, stock balance, GRN status, or PO receipt totals are changed. With no configured receiving gate, existing receipt behavior remains available.
- Both incoming-inspection API paths derive GRN, line, supplier, item, lot, and warehouse identity from the persisted GRN line. Scoped authorization uses the derived warehouse. Active receiving-gate templates make the inspection mandatory and blocking.
- Inspection test-result names, types, units, specifications, and criticality come from the linked template parameter. Results now reference the exact `QCTemplateParameter` row through nullable `template_parameter_id`; migration `20261029_0031` adds the FK and index. Mandatory receiving inspections cannot be accepted until every template parameter has a recorded result.
- Inspection edits, result additions/deletions, and decisions lock and refresh the inspection row before status checks. Receiving-gate configuration and posting share advisory scope locks; multi-scope changes acquire locks in stable sorted order.

## Verification

- Focused contract/regression suite: **45 passed**.
- Fresh disposable PostgreSQL 16: `alembic upgrade head` reached `20261029_0031`; the combined contract, regression, and database suite reported **47 passed**. Database tests confirmed the template-parameter FK/index and that an active receiving gate blocks a GRN line without a passing inspection. The temporary database/container were removed.
- Python compilation and `git diff --check` passed.
- Independent read-only reviewer confirmed the gate check precedes GRN posting mutations, scope derivation and authorization are preserved on both incoming-QC API paths, mutation locks prevent stale status changes, and the new template parameter linkage is consistent. No actionable issues remained; reviewer ran no tests or database operations.

## Limits

- Gate definitions, inspections, and test values used synthetic records. No factory, operator, supplier, production record, or approval was represented as real.
- No production database, GitHub Actions, deployment, merge, or real-world approval is claimed.
