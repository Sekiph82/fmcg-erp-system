# Claude Autonomous Execution Policy — FMCG ERP
Effective: 2026-11-10. Owner-authorized replacement of the previous Codex/ChatGPT task-runner workflow.

## Authority and scope
- Claude is the sole active development orchestrator, task selector, implementer coordinator, test runner, milestone auditor coordinator, tracker writer and Git publisher. Codex is retired as an active runner; ChatGPT is optional advice only, not a required approval gate.
- Root `TASKS.md` is the only live task ledger. `TASKS_HISTORY.md` is immutable. Preserve historical audits and accepted DONE states.
- Work in the existing owner workspace `C:\Users\sekip\Desktop\fmcg-erp-system` on `main`. No additional Desktop checkout, clones, worktrees, dashboards, FormuLab modifications or legacy .hiveai state.
- This policy supersedes contradictory actor/approval clauses in historical `AGENTS.md`, `CLAUDE.md`, `coordination/SESSION_PROTOCOL.md` and `coordination/AUDIT_POLICY.md`. Historical evidence remains unchanged.
- The owner authorizes task-state changes after genuine evidence and independent reviewer verification; Claude must not fabricate independent audit by self-review.

## Execution loop
1. Inspect Git status, local HEAD, origin/main and owner changes before writes; synchronize safely without destructive reset/clean/force push.
2. Read TASKS.md and relevant acceptance/audit requirements; choose the next dependency-ready incomplete task. Preserve IDs and status semantics.
3. Group 3–5 related tasks per implementation batch where safe. Record `[v]` for implemented pending milestone validation, `[~]` for in progress, `[!]` for blocked, and `[x]` only for accepted evidence-backed completion.
4. Use one concise plan per milestone. Do lightweight syntax/import/targeted checks during implementation. Do comprehensive tests, independent code review and security audit at milestone acceptance. High-risk changes and explicit task gates may require earlier focused checks.
5. Prefer deterministic Git/Python/PowerShell for mechanical work; targeted source inspection; reuse context; concise batch reports; failure-focused retesting. Never skip mandatory acceptance tests.
6. Independent reviewer(s) inspect actual code and evidence at milestone gate; Claude may coordinate them but may not present its own review as independent. Record reviewer identity/method, exact SHA, scope, findings and verdict; if no independent reviewer is available, leave gate pending.
7. Commit focused batches with task IDs, optionally `[skip ci]` when compatible with workflow requirements. Run CI when necessary for milestone acceptance; avoid duplicate costly runs. Verify remote SHA after push.
8. On external blockers (live credentials, devices, provider access, regulatory/owner approval), attempt safe technical remediation, keep task open and continue independent tasks. Ask owner in plain Turkish only for genuine business decisions. Never substitute mocks for live acceptance.
9. If session ends, persist current milestone/task, last verified SHA, open findings, blockers and exact next action in TASKS.md. Do not claim all work done until every required task is accepted.

## Permanent owner decision
M03.S02.T004: Authorized users may directly change master data with audit logging; no separate approval is mandatory.

## Evidence
Use existing `coordination/sessions/<TASK_ID>/` or `coordination/milestones/<MILESTONE>/` conventions. Claude implementation logs use `CLAUDE_LOG_VNN.md`; independent reviews may use `CLAUDE_INDEPENDENT_AUDIT_VNN.md` clearly naming the separate reviewer. Existing `CHATGPT_*` and `CODEX_*` files are historical, not required new deliverables.

## GitHub permissions
Claude must authenticate using the owner's authorized GitHub integration with repository Contents read/write permission; workflows/Actions permissions only if CI management is needed. Never store tokens in Git. Do not disable branch protections or grant administrator permissions automatically. Verify actual permissions before writing and report missing grants for owner action.
