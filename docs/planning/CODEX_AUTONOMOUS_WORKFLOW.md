# Codex Autonomous Workflow

This repository uses file-based memory so Codex can resume large ERP implementation work across multiple runs without relying on chat history.

## Required Startup Routine

Every future Codex session must begin by reading:

1. `TASKS.md`
2. `CODEX_PROGRESS.md`
3. `docs/planning/ERP_ROADMAP_IMPLEMENTATION_PLAN.md`
4. `docs/planning/ERP_ROADMAP_STATUS_MATRIX.md`

Then Codex must select the first `TODO` task whose dependencies are satisfied and work on only that task unless the task is tiny and its check task can be safely completed in the same run.

## Checkpoint Rules

Before stopping, Codex must update:

- `TASKS.md`
- `CODEX_PROGRESS.md`
- `docs/planning/ERP_ROADMAP_STATUS_MATRIX.md` when roadmap status changes
- any task-specific documentation created or changed in the run

If interrupted or near limits, Codex must stop starting new code work, finish the safest current edit, run the quickest relevant check, and mark the current task `DONE`, `IN_PROGRESS`, `BLOCKED`, `SKIPPED`, or `NEEDS_USER_REVIEW`.

## Status Rules

- `TODO`: Not started.
- `IN_PROGRESS`: Started but not complete.
- `DONE`: Acceptance criteria and relevant checks are complete.
- `BLOCKED`: Cannot proceed without a missing dependency, failing prerequisite, or user-provided input.
- `SKIPPED`: Intentionally not applicable and documented.
- `NEEDS_USER_REVIEW`: Implementation or documentation exists but requires user decision/review before proceeding.

## Development Rules

- Work incrementally.
- Preserve existing architecture and working features.
- Do not invent roadmap features that are not present in the planning document.
- Do not hardcode secrets or commit local `.env` files.
- Do not make destructive database changes without migrations.
- Add or update tests for each backend/frontend feature task.
- Keep incomplete or mock/stub features honestly labelled.

## Resume Prompt

Use this exact prompt in a future session:

> Continue from TASKS.md and CODEX_PROGRESS.md. Pick the next incomplete task.
