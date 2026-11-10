# M26.S01.T003 — CODEX implementation log

## Implemented

- Enforced configured machine/work-center skill requirements during work-order assignment validation and creation; unsupported certification overrides remain blocked until T004.
- Enforced the same qualification rule before shop-floor execution mutates work-order state, including authenticated session/operator and machine/work-center consistency checks.
- Added authenticated machine-operations route authorization with broad production permissions and resource-scoped checks for qualification rules and assignment paths. Scoped work-center edits require access to the center or every mapped machine.
- Linked operator certificates to canonical training skills, defaulted new certificates to unapproved, required `production.approve` to create an approved certificate, and recorded the approver actor.
- Qualification rule create/update operations record the acting user through the existing master-data stewardship audit. Assignment history retains the assigning user.

## Checks performed

- Targeted Python compileall: passed.
- SQLAlchemy model mapper configuration and machine-ops/shop-floor imports: passed.
- Focused Ruff `F821` check on touched M26 Python files: passed.
- `git diff --check` on touched M26 paths: passed.
- Alembic head check: recorded in the task handoff evidence.
- Independent read-only review: completed; initial missing `select` import was corrected, then reviewer found no further concrete blocker in scoped authorization.

## Pending

No pytest, disposable PostgreSQL, full regression, frontend, or E2E campaign was run for this task. These remain in the consolidated M26 milestone acceptance batch.
