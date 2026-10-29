# M01.S03.T001 — Background/Event Dispatch Ownership Audit Criteria V01

## Task authority and source scope

The sole task row is `M01.S03.T001 — Prove always-running background/event dispatch ownership` in root `TASKS.md`. The task-specific scope is verification of the existing runtime and ownership path; it does not authorize sending outbound events or adding new delivery behavior. The latest applicable local audit trail is `coordination/sessions/M01.S03.T004/CODEX_LOG_V02.md`, which records that M01.S03.T001 had no separate task acceptance material and remained partial. Relevant capability audits are `docs/PROJECT_INVENTORY.md`, `docs/planning/GAP-013_CUSTOM_REPORT_BUILDER_AUDIT.md`, and `docs/planning/GAP-014_NOTIFICATION_CENTER_AUDIT.md`.

## Acceptance criteria

1. Inspect development and production service topology and establish whether an always-running worker/scheduler has a single explicit owner, restart policy, health signal, and graceful lifecycle.
2. Inspect backend startup/lifespan and dependency manifests for a scheduler or worker runtime, rather than relying on comments or feature labels.
3. Trace event creation through persistence, pending delivery selection, retry handling, and the public API. Distinguish a persisted pending attempt or manually invoked endpoint from autonomous dispatch.
4. Check representative scheduled-domain integrations cited in the audits (report schedules and notifications) for an actual periodic trigger.
5. Report `PROVEN`, `GAP`, or `NOT_APPLICABLE` per criterion and state whether any process owns dispatch continuously. Do not claim successful dispatch if no resident worker exists.
6. Keep this proof task read-only with respect to application behavior: no outbound HTTP, provider calls, external publication, database writes, deployment changes, new package, or undocumented business behavior.
7. Record exact files, command/source evidence, environment limits, and independent read-only review in the matching implementation log. A task completion means the ownership proof is finished; it does not assert that the missing runtime capability exists. Keep the M01 milestone status truthful.

## Required outcome

Establish from actual code and runtime configuration whether autonomous dispatch is owned. If no owner exists, document the precise gap and retain that limitation in the tracker evidence. Do not manufacture synthetic worker success or claim production operation.
