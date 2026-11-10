# M23 — Shop Floor Execution: implementation plan

## Scope and guardrails

Root `TASKS.md` is the task authority. The milestone implements the virtual ERP shop-floor workflow; no live facility, employee, device, or production data is implied. Preserve the separate active `exec_*` model family described by `coordination/milestones/M22/M22_S01_T001_RESPONSIBILITY_DECISION_V01.md`. Authentication must use existing ERP identities and RBAC; a typed operator label remains contextual data.

## Task sequence and batches

| Sprint | Tasks | Implementation focus | Validation checkpoint |
|---|---|---|---|
| M23.S01 Operator Workspace | T001–T004 | Touch-safe operator terminal, operation actions, session context, authenticated role/action gating | Focused auth checks only for critical security regressions; defer suite to M23.S04 |
| M23.S02 Runtime Capture | T001–T004 | Actual quantity/time, waste/downtime, material issue confirmation, in-process QC | Keep each persisted fact tied to the correct execution operation and existing quality/inventory boundaries |
| M23.S03 Resilience and Exceptions | T001–T004 | Responsive acceptance, online-only initial release policy, safe retry/idempotency, exception/escalation workflow | Offline policy is recorded in `M23_S03_T002_OFFLINE_POLICY_V01.md`; M23.S04 remains the consolidated validation checkpoint |
| M23.S04 Acceptance | T001–T004 | API, UI/E2E, production/QC/inventory integration, milestone closeout | One consolidated suite, independent code review, and security review; accept tasks only against evidence |

## Current implementation checkpoint

- M23.S01–S04 are complete and accepted after M23.S04.T004 consolidated verification; no live factory, staff, device, or production acceptance is implied.
- M23.S03.T002 establishes online-only authoritative Shop Floor reads/writes; offline mutation queues and automatic replay are prohibited. Reconnection revalidates the authenticated user and permissions, refreshes Shop Floor state, and requires reconciliation before retry.
- M23.S03.T003 provides request-scoped idempotent retries for work-order actions and downtime start/stop using migration `20261104_0012`; authenticated actor/key uniqueness and concurrency behavior were verified with disposable PostgreSQL.
- M23.S03.T004 exposes offline, reconnect, ambiguous server outcomes, and state-refresh recovery in the terminal and downtime modal. Final mocked Chromium recovery E2E passed all three scenarios.
- M23.S04 final evidence and the consolidated independent review are recorded in `coordination/sessions/M23.S04.T004/CODEX_LOG_V01.md`. The M23 backend suite passed 62 tests plus the separately gated S03 DB suite of 8 tests; one intentionally gated test was skipped in the S04 DB invocation and passed in the S03 invocation.
- Next dependency-ready work is governed by root `TASKS.md`; M24 material reservation begins after the M05 inventory baseline, M22 production execution, and M23 Shop Floor close.
## Evidence policy

Routine work receives lightweight diff/syntax checks only. Run comprehensive M23 tests, migration validation, frontend checks, consolidated independent review, and security audit at M23.S04. Any focused test run is limited to a specific security or observed-failure risk and is recorded with its exact command/result.

