# M06.S03.T002 — Implementation prompt V01

Verify only `M06.S03.T002 — Verify landed-cost accounting integration` from root `TASKS.md`, using `CHATGPT_AUDIT_CRITERIA_V01.md` in this directory.

Safely fetch and inspect `origin/main` from `C:\Users\sekip\Desktop\fmcg-erp-system`; preserve all pre-existing owner work. Read current landed-cost service/API/models, the GAP-001/GAP-002 audits, and the accepted M13.S03.T001 criteria, prompt, tests and log. Confirm the audited implementation commit is an ancestor of current main and inspect whether relevant paths changed afterward.

Run the existing `tests/test_m13_landed_cost_posting.py` on a fresh PostgreSQL 16.6 disposable container. The test module deliberately requires its original strict `M13_S03_T001_DISPOSABLE_TEST_DATABASE` opt-in and database-name prefix. Use that unchanged guard and transparently record that the suite is being rerun as evidence for this M06 verification checkpoint. Run `tests/test_gap002_posting_integration.py`, compile the affected landed-cost service/API and test, and run `git diff --check`.

Use one independent source-only reviewer who does not edit, run tests, or access the database. If current evidence remains valid and no in-scope defect is found, make no production-code changes; document the verification. Do not claim supplier invoice/AP/GRNI integration, live provider readiness, or production acceptance. Remove only the exact task-owned database container and verify absence. Commit/push only task-owned verification records when all checks pass, using `[skip ci]`; never run GitHub Actions for M20 through 2026-10-30.
