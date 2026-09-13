# FMCG ERP / MES Audit Policy

Canonical repository: `Sekiph82/fmcg-erp-system`
Canonical branch: `main`
Canonical live tracker: repository-root `TASKS.md`

## Ownership model

- **Claude/Codex = implementer and test runner.**
- **ChatGPT = independent auditor, prompt author, audit-memory owner, and sole writer of `TASKS.md` lifecycle/progress/task-closure state.**
- Claude/Codex may read `TASKS.md` but must not edit it unless the owner explicitly overrides this policy for a specific task.
- Implementation state is handed back through the matching versioned implementation log, never by self-closing the tracker.

## Canonical session layout

Every material task uses one session directory:

`coordination/sessions/<TASK_ID>/`

Example:

`coordination/sessions/M20-S01-T001/`

Each revision is versioned and linked one-to-one:

- `CHATGPT_AUDIT_CRITERIA_VNN.md`
- `CHATGPT_PROMPT_VNN.md`
- `CLAUDE_LOG_VNN.md`
- `CHATGPT_AUDIT_VNN.md`

Optional owner-controlled evidence:

- `OWNER_FINDINGS_VNN.md`
- `CHATGPT_OWNER_GATE_VNN.md`
- `OWNER_PLAYTEST_VNN.md`

The active prompt version determines the required implementation log version:

`CHATGPT_PROMPT_VNN.md -> CLAUDE_LOG_VNN.md -> CHATGPT_AUDIT_VNN.md`

## Evidence levels

### E0 — claim/assumption
A file exists, a feature is claimed complete, or a test is expected to pass but was not actually run. E0 cannot establish audit PASS.

### E1 — implementer-run evidence
Claude/Codex ran the check and recorded the result. Useful but not independent.

### E2 — reproducible implementer evidence
The log contains commit/tree state, exact command/check, expected outcome, explicit failure condition, actual result, and relevant evidence paths/URLs.

### E3 — ChatGPT independent evidence
ChatGPT inspects the actual GitHub state, exact commits/diffs/files/contracts/tests/logs and independently cross-checks behavior where available.

Only ChatGPT audit files may assign independent verdicts such as:

- `AUDITED_PASS`
- `CHANGES_REQUIRED`
- `BLOCKED`
- `NOT_INDEPENDENTLY_VERIFIED`
- `OWNER_REQUIRED`

### E4 — owner decision
Human-controlled product, operational, visual, regulatory, credential, factory-device, or business-policy gates remain owner/external-provider controlled until explicitly resolved.

## Pre-prompt strict audit law

Before ChatGPT issues a material implementation/correction prompt, it must audit the whole active task/sprint surface, not merely the latest diff.

The pre-prompt audit must perform two conceptually separate passes:

### Pass A — implementation/state sweep
Inspect, where applicable:

- models/schema/migrations;
- public API/service entry points;
- authentication/RBAC/scope enforcement;
- state machines and transition ordering;
- transaction/rollback/idempotency/concurrency behavior;
- upstream ERP dependencies;
- downstream consumers;
- inventory/accounting/traceability side effects;
- frontend/API contract consistency;
- imports/exports/reporting;
- background/event behavior;
- observability and operational failure paths.

### Pass B — evidence/test/policy sweep
Reconcile:

- tracker requirement vs implemented behavior;
- prompt requirement vs source;
- audit criterion vs actual evidence;
- test vs claimed behavior;
- direct observability and false-positive risk;
- aggregate test-count claims vs individually required validations;
- migration/CI/build/deployment evidence;
- prior reusable audit learnings.

ChatGPT must not stop after the first material defect.

## Coverage ledger

Before freezing findings for a correction prompt, ChatGPT should build a task/requirement coverage ledger containing, as applicable:

- requirement/task;
- production owner/path;
- public entry points;
- canonical state touched/read;
- upstream assumptions;
- downstream assumptions;
- applicable adversarial classes;
- direct evidence/tests;
- false-positive risk;
- status: `PROVEN`, `GAP`, `DEFECT`, `OWNER_GATE`, or `NOT_APPLICABLE`.

No correction prompt should be issued while a material applicable row has an unexplained `GAP`.

## Frozen finding set

For critical/stateful work, ChatGPT must sweep the entire relevant attack surface before issuing a correction prompt and then freeze the finding set in `CHATGPT_AUDIT_VNN.md`.

The next revision should address that complete frozen set rather than creating finding-by-finding prompt churn.

A later newly discovered finding is acceptable only when:

1. a genuinely new runtime/external fact was unavailable during the frozen sweep; or
2. the correction itself introduced a new defect that could not reasonably have existed in the pre-correction source.

## ERP/MES criticality rule

The following are critical by default:

- authentication, authorization, tenant/company/branch/warehouse/factory scoping;
- inventory reservations/movements/valuation;
- production planning/release/execution/material consumption/FG receipt;
- BOM/recipe/yield/conversion truth;
- quality hold/release gates;
- traceability/recall/genealogy;
- procurement receiving/invoice matching/landed cost;
- finance posting/reconciliation/tax/fiscalization/payment flows;
- payroll/statutory calculations;
- migrations and destructive/bulk data operations;
- webhooks/events/idempotency/retry/DLQ;
- AI actions capable of changing operational state;
- any workflow that can duplicate, lose, misvalue, corrupt, or silently mutate canonical business state.

Critical work normally requires two-stage closure:

1. implementation audit;
2. auditor-authored adversarial validation pass.

Stage 2 may be skipped only when ChatGPT can independently establish sufficient E3 runtime evidence and records why the second stage is unnecessary.

## Minimum adversarial classes

For applicable critical flows, audit/test design should probe:

- invalid/malformed input;
- missing/foreign relational references;
- boundary/min/max values;
- stale/mismatched status;
- unauthorized user/scope;
- repeated request/re-entry;
- duplicate ownership/duplicate posting;
- partial failure after earlier mutation;
- transaction rollback;
- cancel/reset/reversal;
- completion/post/release called twice;
- concurrency/race-like contention;
- idempotency key reuse;
- immutable/audit-history bypass;
- cross-company/branch/warehouse leakage;
- null/empty data;
- currency/UOM/date precision and conversion boundaries where relevant.

## Direct observability and sensitivity

A test must directly observe the behavior it claims to protect. An unrelated earlier failure must not make a negative test green.

For high-risk invariants, prefer sensitivity/load-bearing tests: removing or bypassing the intended protection should make the test fail for the intended reason.

## Regression locks

When a task should not alter accepted architecture, audit criteria should identify protected files/contracts/blobs or explicitly bounded authorized-change areas where practical.

Protected-code identity is evidence, not a substitute for behavioral testing.

## Implementer log requirements

Every material revision must create the matching:

`coordination/sessions/<TASK_ID>/CLAUDE_LOG_VNN.md`

The log must record at minimum:

- active prompt and criteria paths/URLs;
- synchronized starting `HEAD` and `origin/main`;
- preserved pre-existing local/owner work;
- exact changed-file list;
- implementation summary;
- exact commands/checks and actual results;
- expected outcomes/failure conditions for material checks;
- negative/boundary/regression coverage;
- failures encountered and corrections made;
- migration/schema evidence when applicable;
- build/type-check/test/CI evidence when applicable;
- commit SHA(s) and pushed remote state;
- blockers/unverified assumptions;
- explicit confirmation that root `TASKS.md` was read but not modified.

A green aggregate test count never substitutes for a prompt-mandated individual command.

## Safe Git synchronization

Every implementer prompt begins by safely reconciling:

`C:\Users\sekip\Desktop\fmcg-erp-system`

with:

`https://github.com/Sekiph82/fmcg-erp-system`

Rules:

- GitHub `main` is canonical current-state authority.
- Preserve all pre-existing tracked and untracked local/owner work.
- Never use destructive reset/clean/restore merely to obtain a clean tree.
- Never force push.
- Prefer fast-forward reconciliation where safe.
- If local owner work prevents safe synchronization, stop as `BLOCKED` rather than erasing it.

## ChatGPT audit responsibilities

After the implementer returns `AWAITING_AUDIT`, ChatGPT must:

1. read the matching prompt, criteria, and implementation log;
2. inspect actual GitHub commit(s), exact diff and changed files;
3. audit the whole active task/sprint surface, not just the newest patch;
4. validate criteria item-by-item or by clearly mapped groups;
5. treat implementer tests as E1/E2, not independent proof;
6. inspect test sensitivity and false-positive risk;
7. record runtime/credential/environment limitations explicitly;
8. publish `CHATGPT_AUDIT_VNN.md`;
9. update `coordination/AUDIT_INDEX.md` with reusable learnings when material;
10. update root `TASKS.md` itself to audited truth;
11. only then issue the next versioned prompt/criteria pair.

## Closure law

- Claude/Codex never self-closes a task or milestone.
- ChatGPT closes tasks individually based on independent audit evidence.
- Proven unrelated tasks remain closed when a defect is found elsewhere.
- Dependent milestones do not advance through an unresolved critical defect.
- Automated green evidence cannot close owner/external-provider/business-policy gates.
- Historical audit/prompt/log artifacts are immutable evidence. New revisions supersede behavior prospectively; they do not rewrite older evidence to pretend newer behavior existed earlier.
