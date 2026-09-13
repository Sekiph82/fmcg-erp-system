# FMCG ERP / MES Session Protocol

This repository uses GitHub session directories as the communication bus between ChatGPT and Claude/Codex.

## Session identity

Use the canonical tracker task ID as the session folder name where practical:

`coordination/sessions/M20-S01-T001/`

A task remains in the same session directory through all correction/validation revisions.

## Revision lifecycle

### V01

ChatGPT performs the pre-prompt strict audit and publishes together:

1. `CHATGPT_AUDIT_CRITERIA_V01.md`
2. `CHATGPT_PROMPT_V01.md`

Claude/Codex safely syncs the local workspace with GitHub `main`, implements the prompt, runs required validations, and publishes:

3. `CLAUDE_LOG_V01.md`

ChatGPT then independently audits actual GitHub state and publishes:

4. `CHATGPT_AUDIT_V01.md`

### If V01 passes

ChatGPT updates root `TASKS.md` and either closes the task/sprint or advances to the next tracker task.

For critical work, an implementation pass may still require a V02 adversarial validation revision before final closure.

### If V01 has findings

ChatGPT does not immediately issue a narrow fix after the first defect. It finishes the whole-task/sprint attack-surface sweep, builds the coverage ledger, and freezes the complete finding set in `CHATGPT_AUDIT_V01.md`.

Then ChatGPT publishes:

- `CHATGPT_AUDIT_CRITERIA_V02.md`
- `CHATGPT_PROMPT_V02.md`

V02 addresses the frozen correction/validation set only, unless genuinely new evidence appears.

The chain continues V03, V04, etc. without rewriting historical evidence.

## Roles

### ChatGPT owns

- pre-prompt source audit;
- audit criteria;
- execution prompt;
- independent post-run audit;
- reusable audit learnings;
- root `TASKS.md` lifecycle/progress/task closure;
- owner/external gate recording;
- next revision scope.

### Claude/Codex owns

- safe local/GitHub synchronization;
- scoped implementation;
- migrations where authorized;
- test execution;
- implementation evidence;
- exact changed-file and command/result log;
- commits/pushes;
- handoff as `AWAITING_AUDIT` or `BLOCKED`.

Claude/Codex does not write independent audit verdicts and does not edit root `TASKS.md` under the normal policy.

## Standard short handoff prompt

The human-facing prompt given to Claude should remain intentionally short. The detailed contract lives in GitHub.

Typical form:

```text
First safely sync C:\Users\sekip\Desktop\fmcg-erp-system with origin/main from:
https://github.com/Sekiph82/fmcg-erp-system

GitHub main is source of truth. Preserve all pre-existing local work; no destructive reset/clean/restore and no force push.

Read the audit criteria:
<CRITERIA_URL>

Then execute exactly:
<PROMPT_URL>

Do not modify TASKS.md. Complete the required tests, commits/pushes and matching CLAUDE_LOG_VNN.md, then hand back for independent audit.
```

## Standard audit-criteria structure

Use only sections relevant to the task, but consider:

A. Governance / safe sync / authorized scope
B. Protected architecture / non-goals
C. Authentication / RBAC / scope
D. Domain state-machine invariants
E. Data/schema/migration integrity
F. Transaction / rollback / idempotency / concurrency
G. Upstream dependency integration
H. Downstream side effects and cross-module integrity
I. Frontend/API contract and UX behavior
J. CSV/import/export/reporting where applicable
K. Background jobs/events/retry/DLQ where applicable
L. AI grounding/explainability/human approval where applicable
M. Regression locks and protected files/contracts
N. Required tests/build/type-check/migration checks
O. Implementation-log requirements
P. Closure law

Criteria IDs should be stable within a revision, e.g. `M20S01-V01-001`.

## Standard independent audit structure

A ChatGPT audit should contain:

1. Verdict
2. Exact audit basis and commit range
3. Evidence limitations (E1/E2/E3/E4)
4. Whole-task/sprint coverage ledger
5. Pass A implementation/state sweep
6. Pass B evidence/test/policy sweep
7. Accepted evidence
8. Frozen findings, if any
9. Sibling-failure/attack-surface sweep result
10. Required adversarial validation if critical
11. Criteria-to-evidence reconciliation
12. Tracker closure/next actor decision

## Owner/external gates

When engineering audit passes but an owner, accountant, regulator, provider, credential, device, or production-environment decision remains:

- retain the engineering audit PASS;
- create an owner/external gate record when useful;
- keep the affected tracker item open/blocked/owner-required;
- do not ask Claude to fake or simulate closure of an external gate.

A new owner finding may legitimately create a new revision even after an engineering PASS. The new revision must preserve the prior engineering result and scope itself to the newly observed fact.
