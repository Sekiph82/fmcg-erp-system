# M13.S03.T004 — Implementation prompt V01

Implement and rehearse the finance period-close task in `TASKS.md` against the acceptance criteria in `CHATGPT_AUDIT_CRITERIA_V01.md`.

Use only synthetic records in a uniquely task-owned loopback PostgreSQL database. Preserve owner changes and never connect tests to the configured application database unless the exact URL is proven to point at the disposable task database. Keep the change within finance period-close behavior, its regression tests, and this task's evidence. Do not use live bank/eTIMS credentials or make claims about live provider behavior.

Inspect the current period, check, posting and permission flows before edits. Preserve `finance.configure` for checklist maintenance and `finance.approve` for close/lock. Reuse the existing status enum and actor/timestamp fields. Implement fail-closed handling for pending/failed checks, explicit reasoned waivers, legal period transitions, and concurrency-safe serialization between checklist changes and closing. Reject duplicate/invalid transitions without changing the original state. Prove that posting into a closed period is rejected.

Run the focused unit/API tests and the exact disposable PostgreSQL rehearsal after migration to head. Record all results and cleanup truthfully in `CODEX_LOG_V01.md`; keep intermediate failures. Run a read-only independent review before marking the task complete. Do not modify `TASKS.md` in the implementer pass; return the completed log and evidence for tracker closure.
