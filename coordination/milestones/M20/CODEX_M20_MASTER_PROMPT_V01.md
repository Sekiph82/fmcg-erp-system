# CODEX M20 MASTER PROMPT V01 — Master Production Scheduling

Repository: https://github.com/Sekiph82/fmcg-erp-system
Authorized branch: `main` ONLY.
Canonical tracker: https://github.com/Sekiph82/fmcg-erp-system/blob/main/TASKS.md (READ ONLY FOR CODEX).
Execution workspace (if available): `C:\Users\sekip\Desktop\fmcg-erp-system`.
Milestone: M20 — Master Production Scheduling.
Owner: ChatGPT (independent auditor and sole `TASKS.md` lifecycle writer).
Builder: Codex (implementation, testing, factual execution logs, GitHub commits).

## 0. Current GitHub truth and hard stop on false progress

At preparation time GitHub `main` is at `80a6a5af12c634317362bbfcf0d691f0cc165e8a`. Re-fetch and compare on startup because main may have advanced. The canonical dashboard and M20 rows say:
- M20 `IN_PROGRESS` (existing capability is PARTIAL).
- M20.S01.T001 `[~]` (NOT DONE).
- Next action: V03 remediation, then factual `CLAUDE_LOG_V03.md` in the existing session, and independent ChatGPT audit.
- M20.S01.T002–T004 and all M20.S02–S05 tasks are unstarted `[ ]`.
- `CHATGPT_AUDIT_V02.md` verdict is `CHANGES_REQUIRED`.
- V03 prompt and auditor-only V03 criteria exist. No `CLAUDE_LOG_V03.md` or `CHATGPT_AUDIT_V03.md` was present in the GitHub session directory when this work order was written.

Do not mark T001 DONE or advance milestone because tests or self-review look green. Only ChatGPT can audit acceptance and update the canonical tracker.

## 1. GitHub-first safety and role contract

1. Safely inspect `git status --porcelain=v1`, current branch, `origin`, `fetch origin main`, and local-vs-remote divergence. Preserve every owner/local tracked and untracked file. No `reset --hard`, `git clean`, forced pushes, deleting evidence, or disruptive stash without safe restoration. Stop and document only if safe synchronization is genuinely impossible.
2. Work/push ONLY to existing `main`. Do NOT create, resurrect, push, or use `hiveai*` or any other branch. Avoid PR-based detours; honor current single-branch owner policy.
3. Read `AGENTS.md` for ERP architecture but explicitly follow the newer canonical root-only tracking contract when older `.hiveai` instructions conflict. Do not write any `.hiveai` control-plane files.
4. Do NOT modify `TASKS.md` or `TASKS_HISTORY.md`. `PLANS.md` is architectural reference only.
5. Codex implements and verifies its own work; its log is a factual claim/evidence index, not independent acceptance. Do NOT create/edit `CHATGPT_AUDIT_*.md` or `CHATGPT_AUDIT_CRITERIA_*.md`. Do not assign PASS/FAIL audit verdicts. ChatGPT performs independent audits and tracker updates after Codex commits.
6. Use no credentials, unsafe sample data, bogus test passes, or claims about production/live devices/providers without actual evidence.

## 2. Mandatory first task: M20.S01.T001 V03 frozen-remediation handoff

This block takes precedence over the later M20 plan. It is the unfinished task, not a new milestone kickoff.

Read:
- `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_V02.md` (frozen F-V02-001..004).
- `coordination/sessions/M20-S01-T001/CHATGPT_PROMPT_V03.md` (authoritative execution details for this revision).
- `coordination/sessions/M20-S01-T001/CHATGPT_AUDIT_CRITERIA_V03.md` is **FOR CHATGPT ONLY**. Do not self-audit against or edit it.
- MPS service, API, MRP/Recipe/Product/Warehouse/ProductionOrder models, transaction conventions, existing V01/V02 tests and migrations.

Required implementation:
A. Whole-plan release: remove `release_complete = created > 0`. Define and enforce complete release based on all required lines, including explicit handling of ineligible versus FEASIBLE unresolved lines. One created PO + a second missing recipe must NOT mark the plan RELEASED. Return truthful counts and lifecycle.
B. Master-data integrity: remove `uom=product.uom.value if product and product.uom else "KG"`. Missing Product or missing/invalid authoritative UOM must fail closed. Reuse existing models/validation without inventing product-specific defaults.
C. Transaction proof: demonstrate via endpoint-/DB-transaction behavioral test that first PO flush followed by a later failure leaves zero committed partial POs and no surviving linkage/false lifecycle state. Prefer PostgreSQL-backed test. If runtime cannot support it, provide strongest valid test and record the exact gap; do not claim persistent rollback without proof.
D. Regression proof: run focused V01/V02/V03 MPS tests and relevant MRP, production, auth, registry suites; classify any historical 3 failures by exact base-vs-head reproduction, without weakening tests. Run compile/import, `python -m alembic heads`, and `git diff --check`.
E. Preserve API/auth/RBAC, migration ownership, existing MPS UI and other previously accepted behavior. Do not implement broader M20.S02–S05 in this frozen remediation.

Mandatory artifact for the V03 closure attempt:
`coordination/sessions/M20-S01-T001/CLAUDE_LOG_V03.md`

Although the legacy filename says CLAUDE, retain it **exactly** for existing session protocol and `TASKS.md` continuity; the content must identify `Builder: Codex`. Do not rename or delete past Claude logs. Record synchronized baseline SHA, implementation SHA(s), exact diff/file list, executed commands, real test outcomes, failures and corrections, atomicity evidence, before/after regression proof, remaining risks, protected-file hash/diff checks, and pushed final SHA. No self-audit verdict.

Commit/push V03 implementation and factual log to GitHub `main`, then STOP this gated execution at `AWAITING_CHATGPT_AUDIT`. Do not silently move on to T002 until ChatGPT publishes `CHATGPT_AUDIT_V03.md` and updates `TASKS.md`.

## 3. M20 milestone roadmap to resume ONLY after independent T001 acceptance

After ChatGPT accepts the previous gate, execute the next task according to the **then-current** root `TASKS.md`, not a stale copy of this document. For each task use its own `coordination/sessions/<TASK_ID>/` work session. ChatGPT writes audit criteria and subsequent independent audit; Codex writes implementation and factual `CODEX_LOG_V01.md` (or explicitly prescribed legacy filename) and leaves tracker untouched.

### M20.S01 — MPS Domain Reconciliation
- T001: Map and harden existing MPS models/APIs/UI/services (currently IN_PROGRESS; V03 first).
- T002: Preservation/regression proof of planning-board, capacity, campaigns, what-if capabilities; no rebuild.
- T003: Map missing state/data invariants with concrete source cross-reference; implement only bounded, task-authorized corrections.
- T004: Representative MPS acceptance dataset and focused deterministic regression suite.

### M20.S02 — Demand & Supply Coupling
- T001: Consolidate sales-order, forecast and safety-stock demand using existing MRP semantics.
- T002: Reconcile on-hand, reserved, incoming procurement/production and planned availability without double counting.
- T003: Link to existing recipe/BOM explosion and material feasibility, preserving UOM/yield and shortage truth.
- T004: Per-line shortage/constraint reasons, backend API and frontend consistency.

### M20.S03 — Capacity & Campaign Planning
- T001: Validate work-center/machine capacity units, calendars, shifts and downtime against existing resource data.
- T002: Bound campaign grouping, stable sequencing and setup changes.
- T003: Model existing changeover/CIP/allergen restrictions only where authoritative data exists; no invented production facts.
- T004: Persist and render overload reasons/recalculation with deterministic regressions.

### M20.S04 — Approval, Release & Scenarios
- T001: Tighten draft→approve→release contract and partial/atomic behavior, reusing T001 hardening.
- T002: Ensure real principal identity, permission checks and auditable transitions.
- T003: Preserve and validate persisted what-if assumptions, scenario isolation, supported change types and explicit estimates.
- T004: Compare scenario KPI impacts for service/cost/capacity with clearly labeled estimates, not fake accuracy.

### M20.S05 — Verification & Closure
- T001: Broad focused MPS backend/integration regression.
- T002: Frontend typecheck/build and relevant UI or Playwright flows for planning-board, campaigns, capacity and what-if.
- T003: MPS→MRP→ProductionOrder, BOM, inventory, warehouse, RBAC and migration proof on best available DB/runtime.
- T004: Emit factual final acceptance evidence for ChatGPT auditor; only ChatGPT closes M20 in `TASKS.md`.

## 4. Required ERP-wide invariants for every M20 task

- Extend, never duplicate, existing FastAPI services, Next.js UI, SQLAlchemy/Alembic, PostgreSQL/Redis, module registry, role/permission and audit patterns.
- Recheck tenant/company/plant/warehouse scope, approved lifecycle and authorization for every affected route.
- Prevent duplicate PO creation, wrong-stock or plan quantities, unit inconsistencies, races, and silent partial commits. Respect transaction ownership and unique constraints. No `count()+1` uniqueness assumptions without concurrency-safe proof.
- Validate product/recipe lifecycle, effective date, stock/material feasibility and UOM through authoritative master data.
- Preserve capacity unit consistency, partial-period conservation, planned/actual distinctions and realistic manufacturing semantics.
- Test negative and positive cases plus rollback/idempotency/ordering where applicable; tests must be capable of catching reverted behavior rather than merely searching source strings.
- Never turn production credentials, live financial/provider tests, physical factory tests, or unexecuted suites into asserted PASS.
- Investigate CI failures with actual workflow/job evidence; unrelated red CI is not permission to assert green.
- No wholesale refactor, no unrelated cleanup, no blanket rewriting fixtures, no test disabling.

## 5. Codex execution log contract (each authorized task)

A factual session log must contain:
1. Task/revision, synced start SHA, final implementation SHA(s), latest remote SHA and branch.
2. All changed files and exact intent, with hashes or diff evidence for protected tracker files.
3. Commands and true results, scope-specific green/red/skipped test counts, migrations and frontend checks when touched.
4. Failures and attempts, regressions, unknowns, unresolved owner/external gates.
5. Links to GitHub commits, relevant Actions jobs and evidence; no fabricated logs or screenshot claims.
6. Confirmation no `TASKS.md`, `TASKS_HISTORY.md`, auditor files, or legacy branch was modified.
7. Statement `AWAITING_CHATGPT_AUDIT` after push, with exact log URL.

## 6. Milestone master handoff and autonomy

Work continuously on authorized scope without repeated questions, fixing recoverable errors. **Do not self-close tasks or skip audit gates.** The immediate authorized deliverable is V03 only. Later M20 work may proceed only after ChatGPT audits V03, changes tracker and publishes each next execution scope. If that gate is absent, stop cleanly at `AWAITING_CHATGPT_AUDIT`, not with a fictional milestone completion.
