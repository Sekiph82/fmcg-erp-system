# FMCG ERP / MES Audit Index

This file is ChatGPT-owned repository audit memory. Claude/Codex reads and applies relevant learnings but does not edit audit conclusions or create audit verdicts.

Canonical policy:
`coordination/AUDIT_POLICY.md`

## Active audit learnings

| ID | Applies to | Learning | Required future check | Source |
| --- | --- | --- | --- | --- |
| ERP-AL-001 | Tracker governance | Root `TASKS.md` is the only live project tracker. Historical `.hiveai` state must not be revived as competing authority. | Claude/Codex reads but does not edit `TASKS.md`; ChatGPT updates it after audit. | M00 governance reconciliation |
| ERP-AL-002 | Existing enterprise modules | Presence of models/pages/endpoints does not prove enterprise completion. Many M20-M35 areas are PARTIAL foundations, not greenfield. | Reconcile existing capability before adding code; never duplicate a module merely because roadmap wording sounds new. | M00 capability inventory/reconciliation |
| ERP-AL-003 | Authentication / authorization | Hard-coded/system-user execution in production business endpoints bypasses real actor and RBAC truth. | Every privileged ERP action must use the repository's authenticated current-user + permission/scope pattern and record the real actor. | M20 pre-task strict audit |
| ERP-AL-004 | Workflow states | Error text/comments are not workflow enforcement. A state transition must be implemented by exact guards. | Add direct negative tests for illegal transitions and repeated release/post/approve calls. | M20 pre-task strict audit |
| ERP-AL-005 | Release eligibility | Descriptive comments such as “FEASIBLE only” do not count if the database query/service omits the corresponding predicate. | Audit service queries and downstream object creation for exact eligibility predicates. | M20 pre-task strict audit |
| ERP-AL-006 | Mutable operational status | Generic PATCH schemas can accidentally let clients author system-derived status/feasibility fields. | Separate planner-editable fields from engine-owned state or enforce transition-specific mutation guards. | M20 pre-task strict audit |
| ERP-AL-007 | Aggregate green tests | Aggregate pass counts are supporting evidence only and can hide omitted required validations. | Log prompt-mandated checks individually and audit their sensitivity. | Strict audit policy |
| ERP-AL-008 | Local workspace safety | Pre-existing tracked/untracked local changes are owner work until proven otherwise. | Preserve them; if safe sync cannot proceed, return BLOCKED rather than resetting/cleaning/restoring. | Owner workflow rule |
| ERP-AL-009 | External/live integrations | Source-complete integrations are not production-accepted without real credentials/sandbox/live evidence. | Keep eTIMS/M-Pesa/bank/WhatsApp/device/provider gates separate from source-code completion. | M00 strict audit |
| ERP-AL-010 | Critical ERP closure | Stateful/financial/inventory/production/security changes risk correlated implementation-test assumptions. | Use two-stage closure with auditor-authored adversarial validation unless ChatGPT has sufficient independent E3 runtime evidence. | `coordination/AUDIT_POLICY.md` |
| ERP-AL-011 | Test observability | A negative test can pass because an unrelated earlier guard fired. | Arrange fixtures so unrelated requirements are valid and the intended invariant is the only failure cause. | Strict audit policy |
| ERP-AL-012 | Cross-module integrity | Local success can still violate downstream inventory, finance, quality, traceability, or production assumptions. | Every critical task explicitly names upstream/downstream consumers and checks transactional side effects. | ERP/MES audit adaptation |
| ERP-AL-013 | Migration truth | Model presence is not migration ownership proof. | Verify Alembic ownership, single head, fresh DB and representative upgrade behavior when schema changes occur. | M00 P1 DB-MIGRATION-005 |
| ERP-AL-014 | Audit artifact mapping | Evidence must be version-addressable and revision-matched. | Enforce `CHATGPT_PROMPT_VNN -> CLAUDE_LOG_VNN -> CHATGPT_AUDIT_VNN` within one session directory. | ScrubBots coordination model adapted for ERP |

## Session protocol

For material task `<TASK_ID>`:

`coordination/sessions/<TASK_ID>/`

Each revision normally contains:

- `CHATGPT_AUDIT_CRITERIA_VNN.md`
- `CHATGPT_PROMPT_VNN.md`
- `CLAUDE_LOG_VNN.md`
- `CHATGPT_AUDIT_VNN.md`

Owner/external gates may add `OWNER_FINDINGS_VNN.md` or `CHATGPT_OWNER_GATE_VNN.md`.

## Audit history

| Cycle | State | Notes |
| --- | --- | --- |
| M00 | COMPLETE | Repository capability inventory, M01-M19 audit, M20-M35 reconciliation, strict source/history audit. |
| M20-S01-T001 | ACTIVE | First FMCG session to migrate fully to versioned criteria/prompt/log/audit coordination. |
