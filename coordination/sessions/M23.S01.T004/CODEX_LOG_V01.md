# M23.S01.T004 — Permission and role-specific action gating

## Acceptance basis

- Canonical scope: root `TASKS.md`, `M23.S01.T004 — Permission and role-specific action gating`.
- Shop Floor workflow: `docs/user-manual/module-manuals/manufacturing/08-shop-floor.md` and the M23.S01.T003 log, which explicitly reserves authentication and role-specific action permission for this task.
- Security baseline: `coordination/AUDIT_POLICY.md`, `coordination/AUDIT_INDEX.md` (`ERP-AL-003`), and the latest applicable strict audit `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md`.
- M22 security precedent: `coordination/sessions/M22.S04.T004/CLAUDE_LOG_V01.md` secures API entry points with authenticated users, action permissions, scope checks, and actor IDs. The M22 responsibility decision remains authoritative: this task preserves the separate `exec_*` family and does not create a crosswalk.
- Virtual-data boundary: `coordination/sessions/M27.S04.T004/CODEX_LOG_V01.md`; no real factory, employee, or production acceptance is represented.

## Implemented

- Every Shop Floor API route now requires the repository's authenticated ERP user dependency.
- Aggregate dashboards, active-session listings, alerts, supervisor records, and AI recommendations require broad production view access. Line-scoped queue/session/downtime/handover/activity reads require a specific `production_line` view scope and constrain their queries to that line.
- Session creation and work-order execution use existing `production.edit`, `production.edit_all`, `production.edit_own_scope`, and `production_execution.update_own_line` permissions. Scoped execution requires line edit scope, an active session bound to the authenticated user, and a matching work-order line. Client-supplied operator/session fields cannot grant authority.
- Handover approval, overrides, AI execution, and recommendation decisions require `production.approve`. Display names are taken from the authenticated ERP user where a supervisor label is shown.
- Authenticated user IDs are persisted separately from virtual operator/profile context on sessions, activity, downtime, handovers, overrides, and AI recommendation actions. Migration `20261104_0011` adds nullable, restrictive user foreign keys and indexes so existing history remains readable while new API writes capture actor identity.
- The Shop Floor workspace limits the operator role to the terminal and hides supervisor controls without approval permission. Terminal mutations are disabled unless the user's selected line is in scope. The terminal restores line context from the authenticated session. The API remains authoritative.
- Fixed the activity-event helper's missing `duration_minutes` argument so the existing downtime-close path can record its paired activity event.
- The manufacturing manual documents the existing permission codes, scope requirements, and the distinction between virtual operator labels and authenticated ERP identity. No new role grants, factory records, employees, or line scopes were fabricated.

## Verification

- `python -m pytest -q tests/test_m23_s01_t004_shop_floor_permissions.py` from `backend`: **6 passed**, 1 existing Starlette/httpx deprecation warning. Cases cover unauthenticated reads and mutations, authenticated denial, line-scoped view/edit, supervisor approval separation, foreign/inactive/mismatched execution sessions, and authenticated actor/downtime duration capture.
- `python -m py_compile` on the changed endpoint, service, model, schema, migration, and focused test: **exit 0**.
- Targeted ESLint on the Shop Floor workspace, operator terminal, and supervisor console: **exit 0**.
- `git diff --check`: passed after removing the one whitespace issue found during review.
- These are focused security checks only. M23-wide tests, PostgreSQL migration upgrade/downgrade, complete frontend type-check/lint, and the consolidated independent code/security review remain pending M23.S04. No live identity, factory, or production database acceptance is claimed.
