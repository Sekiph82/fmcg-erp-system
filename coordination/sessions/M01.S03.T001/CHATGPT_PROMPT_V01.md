# M01.S03.T001 — Execution Prompt V01

Execute only `M01.S03.T001 — Prove always-running background/event dispatch ownership` from root `TASKS.md`.

Read `CHATGPT_AUDIT_CRITERIA_V01.md`, the applicable M01.S03.T004 audit log, `docs/PROJECT_INVENTORY.md`, and GAP-013/GAP-014 audit records. Trace service composition, FastAPI lifespan, worker dependencies, event persistence, pending/retry paths, and representative scheduled endpoints. Record exact evidence and any absence of a resident owner in `CODEX_LOG_V01.md`.

This is a read-only proof task. Do not send events or outbound HTTP, invoke provider/production services, start or alter application containers, add a worker framework, or claim the dispatch capability works unless actual resident ownership and execution evidence establish it. If the source confirms there is no worker, complete the proof honestly as a documented capability gap; leave feature work for an explicitly scoped task. Preserve unrelated work and follow the project queue instructions for task boundaries and safe Git synchronization.
