# M27.S01.T003 — Codex implementation evidence

**Status:** COMPLETE — severity, mandatory, and waiver safeguards are implemented and independently reviewed.

**Acceptance source:** The root `TASKS.md` row `M27.S01.T003 — Gate severity/mandatory/waiver rules` is the exact task authority. No M27-specific T003 prompt/audit file was present. The applicable `docs/planning/GAP-017_HACCP_WORKFLOW_AUDIT.md` and implementation notes describe the existing quality/HACCP severity and approval context; no detailed gate-waiver policy is prescribed there. Consistent with the owner's instruction to model the ERP as a realistic virtual operation, this task implements conservative configurable defaults without representing any real factory or staff approval.

## Implemented

- Added gate severity levels `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`; `MEDIUM` is the default.
- Added `is_mandatory`, default true. Critical gates are always mandatory.
- Added `waiver_allowed`, default false, plus explicit `waiver_reason_required` and `waiver_approval_required`, both default true. An enabled waiver cannot disable either safeguard. Critical gates cannot be waived.
- Enforced these invariants in API schemas, service create/update validation, and database check constraints. The migration checks for constraints already created by the dynamic squashed baseline, so fresh-database migration does not add duplicate constraints.
- Waiver execution/approval records and transaction enforcement remain outside this task; the later M27 exception/waiver tasks own those workflows.

## Verification

- Focused contract/regression tests: **38 passed, 6 skipped** in the ordinary run; skipped cases require the disposable database opt-in.
- Disposable loopback PostgreSQL 16: `alembic upgrade head` passed through `20261029_0029`; **6 database tests passed**, including database-level rejection of unsafe critical/waiver combinations. The task-owned container and database were removed afterward.
- Python compilation and `git diff --check` passed.
- Independent read-only review confirmed policy consistency across API schema, service validation, model checks, and migration. Reviewer found no material issue, made no edits, and ran no tests/database operations. An unrelated owner-local `frontend/next-env.d.ts` change was left untouched and unstaged.

## Limits

- No operational gate blocking, waiver workflow, or synthetic human identity was fabricated here; the fields define future behavior for the transaction and exception tasks.
- No production/tenant database, GitHub Actions, deployment, merge, or real-world approval is claimed.
