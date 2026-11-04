# M34.S04.T002 — Tolerance/exception approval

## Scope

Implemented configured tolerance behavior and guarded finance exception approval for three-way invoice matching. Tolerance rules now validate nonnegative finite thresholds and normalized names/roles; optional absolute thresholds and approval roles can be cleared explicitly. Matching honors manual approval for within-tolerance variance and the configured beyond-tolerance payment hold, while missing sources, duplicates, blocked lines, and overbilling remain hard stops. Exception approval requires a reviewable variance, a justification, and every configured approval role from the authenticated actor; superusers retain the explicit override.

When both percentage and absolute limits are configured, both must pass. Absolute quantity and price differences are measured on the current invoice line. For subsequent invoices, quantity variance and its percentage use the remaining accepted quantity after prior matched invoices. This keeps tolerance evaluation consistent with the cumulative overbilling guard.

## Verification

- Focused T001/T002 unit suite: 18 passed.
- Fresh task-owned PostgreSQL 16.6 run: 7 passed; Alembic upgraded to `20261104_0001 (head)`; disposable container cleanup verified. Detailed runner, migration, pytest, and cleanup output is in the matching `*-V03.log` files in this session directory.
- The PostgreSQL regressions include configured-role denial/success, manual within-tolerance approval, explicit nonblocking tolerance policy, absolute-plus-percentage quantity policy, clearing optional policy fields, hard-stop overbilling, and a subsequent invoice for the 1 unit remaining after 9 of 10 accepted units were previously matched.
- Targeted Ruff, Python compilation, and `git diff --check` passed. The service file reports 15 Ruff findings, identical in count and content to the pre-existing HEAD version; the baseline/current comparison is recorded in the verification report.
- Independent read-only review found the subsequent-invoice quantity-basis defect, which was corrected and regression-tested. The follow-up review reported no remaining actionable findings in the reviewed scope.

## Assumptions and limits

No monetary tolerance defaults or real staff/factory records were invented. The task uses synthetic supplier/invoice data and virtual role names only. Payment release follows the explicit configured `block_payment_beyond_tolerance` flag for tolerance-only variance statuses; that setting does not bypass the documented hard-stop statuses. Existing `datetime.utcnow()` deprecation warnings and the service's pre-existing Ruff findings remain outside this task's scope.
