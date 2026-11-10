# M22.S04.T004 — M22 closeout evidence

## Scope and acceptance basis

- Canonical scope is root `TASKS.md`, exact row `M22.S04.T004 — Close M22`.
- Domain boundary: `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md`. `ProductionOrder` owns the canonical production commitment; routed `WorkOrder` rows are child operations; `exec_*` remains a separate active model family with no inferred crosswalk.
- Governance reviewed: `coordination/AUDIT_POLICY.md` and `coordination/AUDIT_INDEX.md`. The latest applicable strict audit available is `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V06.md`; it is historical bounded M20 evidence, not an M22 verdict. No M22-specific acceptance matrix or prior M22 closeout audit exists.
- At start and final validation, canonical Git root was `C:\Users\sekip\Desktop\fmcg-erp-system`, branch `main`; local HEAD and fetched `origin/main` both resolved to `0db8dc68c971661dbda55f6992f3b4e70e4da84d` (0/0 divergence). Unrelated working-tree changes and generated evidence were preserved; no broad staging or cleanup was performed.

## Remediation applied during closeout

- Secured every subcontracting route with authenticated procurement-view access; mutations additionally require procurement create, approve, or edit permission. Broad read permission is required for aggregate responses because this API does not yet filter each result by warehouse scope.
- Subcontract order creation, approval, issue, receipt, and completion now receive the authenticated user ID. Completion rejects a missing actor and persists `completed_by_id`; migration `20261104_0009` adds the nullable actor FK with `ON DELETE RESTRICT`. Linked-work-order subcontract creation also requires production edit permission in the parent order's source or target warehouse scope before service mutation.
- Production work-order detail and genealogy reads authorize against the parent production order. PATCH locks the parent/operation context and checks edit scope before updating. Read authorization uses `can_view_scope`, preserving existing broad `production.view` grants as well as supported scoped grants.
- Frontend dependency audit initially reported 1 high and 16 moderate findings. `follow-redirects` was pinned to patched `1.16.2`; the advisory's remaining vulnerable `minimatch` trees were pinned to `11.0.1`. Final audit is clean; ESLint toolchain compatibility was checked across the complete frontend source tree in bounded batches.

## Consolidated validation evidence

- Fresh PostgreSQL schema migration: `alembic upgrade head` succeeded through `20261104_0009`; `alembic current` reports `20261104_0009 (head)`. Receipts: `evidence-V03/m22_full_campaign_fresh_template_migration.log`, `evidence-V03/m22_full_campaign_template_current.log`.
- All ten M22 task-owned PostgreSQL regression suites passed on separate task-named loopback/passwordless databases cloned from the freshly migrated schema; each database was dropped after its test. Total: **31 passed**. Per-suite receipts and machine summary: `evidence-V03/*_final.pytest.log`, `evidence-V03/m22_full_campaign_summary.json`.
- API authentication/authorization/scope regressions: **7 passed**, `evidence-V03/m22_security_api_final.pytest.log`.
- Subcontract completion actor and linked-work-order PostgreSQL regression: **2 passed**, `evidence-V03/subcontract_link_actor_regression.pytest.log`; the test asserts the stored completion actor equals the authenticated synthetic user.
- Additional cross-module regressions from the closeout campaign: M08 transition guard **15 passed**, M08 inventory atomicity **5 passed**, M27 production/quality **42 passed, 7 skipped**, and M27 production gate **1 passed**. These tests exercise related downstream paths; they are not counted in the 31 M22-suite total. Receipts are in `evidence-V02/`.
- Frontend TypeScript `npm run type-check` exited 0; receipt `evidence-V03/frontend_typecheck_after_overrides.log`.
- ESLint passed over all **962** `frontend/src` JavaScript/TypeScript files in 13 bounded batches (12 × 80 files and a final 2-file batch), every exit 0. Receipts: `evidence-V03/frontend_source_lint_batch_*.log` and `evidence-V03/frontend_source_lint_chunked_summary.json`. The focused production/work-order/subcontracting lint also passed for 36 files.
- Final `npm audit --json`: **0 vulnerabilities across 498 dependencies**; receipt `evidence-V03/npm_audit_final_V03.json`. Intermediate audit receipts are preserved; the final audit supersedes them.
- Python compile checks passed for changed API, service, model, migration, and test files. `git diff --check` passed (Git emitted existing line-ending normalization warnings only).

## Validation limits and audit state

- Repository-wide `npm run lint` and a single-process `eslint src` attempt were interrupted after sustained high memory use while the tool traversed the large workspace. No PASS is claimed for those interrupted commands; the bounded run subsequently linted all 962 source files successfully. Details are preserved in `evidence-V03/frontend_lint_scope_note.md`.
- No real factory, employee, production database, credentials, or live integration result is represented. PostgreSQL checks used only synthetic records in disposable local databases.
- Consolidated independent read-only reviewer verdict: **M22 passes the code and disposable-database acceptance review; no remaining source-level security, actor-attribution, or migration blocker.** The reviewer confirmed the 31/31 M22 PostgreSQL campaign, 7/7 API security tests, 2/2 actor regression, `20261104_0009` fresh migration head, 962/962 source-lint files, type-check exit 0, and 0/498 npm audit. The first review's findings—unauthenticated subcontracting mutations, missing parent work-order scope checks, and one high dependency advisory—were fixed and re-reviewed. No live populated-production migration or production acceptance is claimed.
