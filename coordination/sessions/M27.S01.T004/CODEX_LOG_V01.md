# M27.S01.T004 — Codex implementation evidence

**Status:** COMPLETE — versioned gate definitions, inclusive effective dates, and immutable started versions are implemented and independently reviewed.

**Acceptance source:** Root `TASKS.md` row `M27.S01.T004 — Version/effective-date governance` is authoritative. No task-specific T004 prompt/audit was present. Reviewed `docs/planning/GAP-017_HACCP_WORKFLOW_AUDIT.md`, its schema design, and implementation notes. Existing records identify version control as an auditability gap; existing BOM conversion-profile version/effective-date behavior provides an in-repository pattern. This implementation is scoped to the M27 quality-gate catalog.

## Implemented

- Added positive integer gate versions, unique by `(code, version)`. Existing records migrate as version 1, effective from the migration/current date.
- Effective windows are inclusive: `effective_from <= as_of_date <= effective_to`, with `effective_to` optional. The active-definition list supports an explicit `as_of_date`; by default it returns only versions effective today.
- Versions for a gate code must be sequential and have non-overlapping date windows. Per-code PostgreSQL transaction advisory locks serialize create/update checks, including first-version creation where no row exists yet.
- Once a version has started, its rules and start date cannot change in place; operators create the next version instead. An open-ended started version may be closed once at a date on/after today, but a closed started range cannot be rewritten or reopened. Future versions remain editable drafts until they begin. Gate codes remain immutable.
- The additive migration upgrades legacy single-code uniqueness to `(code, version)`, backfills existing rows as version 1, and refuses unsafe downgrades when multiple versions exist. Its guards support both older persisted schemas and the dynamic fresh-database baseline.

## Verification

- Focused contract/regression tests: **39 passed, 7 skipped**; the skips require the disposable PostgreSQL opt-in.
- Disposable loopback PostgreSQL 16: `alembic upgrade head` passed through `20261029_0030`; **7 database tests passed**, including sequential versions, inclusive as-of selection, overlap rejection, skipped-version rejection, and persisted window validation. The task-owned container/database were removed afterward.
- Python compilation and `git diff --check` passed.
- Independent read-only review confirmed sequential versions, inclusive dates, serialized overlap checks, immutable started versions, and draft edit behavior. Reviewer found no remaining actionable issue and ran no tests/database operations.

## Limits

- Dates and gate rows in tests were synthetic. No real manufacturing or approval records were introduced.
- This task governs definition versions; future M27 transaction and exception tasks own operational gate enforcement and waiver records.
- No production/tenant database, GitHub Actions, deployment, merge, or real-world approval is claimed.
