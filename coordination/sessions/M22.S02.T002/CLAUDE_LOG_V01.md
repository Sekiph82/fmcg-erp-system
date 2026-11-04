# M22.S02.T002 — Split/merge work orders

## Scope and starting point

- Required actor: CODEX; canonical task source: root `TASKS.md`.
- Task was explicitly `IN_PROGRESS` before implementation.
- Starting commit and `origin/main`: `b01f77cd8bd83700b32bb27e332e67368dcba2e6`.
- The local canonical checkout was fetched and compared with `origin/main`; there was no commit divergence. Existing local control-state changes and unrelated owner artifacts were left untouched.
- No task-specific M22.S02.T002 acceptance or audit document was present. The implementation follows the M22 responsibility decision and the M22.S02.T001 routing/transition contracts: canonical `production_orders` / `work_orders` only; no cross-write into the separate `exec_*` subsystem.

## Implemented

- Split planned work orders into 2–20 positive quantities at three-decimal precision; the sum must exactly equal the source planned quantity.
- Merge 2–20 distinct compatible work orders only when they belong to the same planned, unapproved production order and share route step (including both being manual/unrouted), work center, operation, operator, and planned window. The merged quantity cannot exceed the parent planned quantity.
- Both operations are limited to unstarted work orders. Split/merge refuse active schedules and any direct linked operational record found through registered foreign keys, preserving assignments, labor, QC, waste, time, downtime, planning, and other module references.
- Source rows remain as cancelled history. Replacement rows retain the same production-order parent (and therefore product, batch, UOM, and warehouse context). Immutable genealogy edges capture action, source, result, transferred quantity, actor, and timestamp; existing immutable transition events capture source cancellation and result creation.
- Added authenticated split, merge, and lineage-read API routes, plus order-detail controls for split quantities, compatible-source selection, and lineage viewing.
- Added a disposable-PostgreSQL regression test guarded to an exact loopback `fmcg_m22_s02_t002_<hex>` database without a password.
- Migration `20261104_0005` drops T001's one-work-order-per-routing-step unique constraint, creates constrained/append-only genealogy storage, and refuses downgrade if it would destroy lineage or make the unique constraint impossible to restore.

## Review and verification

- Independent read-only review found and corrected three issues: the split API response now selects exactly the new result IDs, routing locks follow Routing → RoutingStep → WorkCenter to match existing routing mutation paths, and the regression test passes its database session to the merge service.
- `git diff --check` passed before the final small edits; it will be rerun before staging.
- `python -m alembic heads` resolves the new revision as the sole head (`20261104_0005`); no migration was applied to a database.
- PostgreSQL integration tests, Alembic migration execution, frontend type-check/build, and end-to-end checks were deliberately not run per the owner’s milestone-batched test preference. No runtime acceptance is claimed.
- No GitHub Actions were run. Publication will use a `[skip ci]` commit only after final static review and task-state validation.
