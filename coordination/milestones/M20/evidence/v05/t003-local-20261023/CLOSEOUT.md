# M20.S05.T003 local closeout — 2026-10-23

## Scope

Cross-module PostgreSQL verification for MPS demand/material planning, BOM and inventory feasibility, warehouse/company authorization, production order release, number-sequence migration, transaction rollback, audit events, and scenario snapshots. Scope follows `coordination/milestones/M20/CODEX_M20_MASTER_PROMPT_V04.md` § M20.S05. No GitHub Actions or remote CI were run.

## Changes

- Strengthened the PostgreSQL-backed release rollback test in `backend/tests/test_m20_v03_acceptance.py` to assert that a failed, rolled-back production release leaves no `MPS_PLAN_RELEASED` audit event for that synthetic plan.
- No production-code defect was established by this bounded task review, so no production behavior was changed.

## Verification

- Fresh task-owned PostgreSQL 16 database, with `M20_DISPOSABLE_TEST_DATABASE=1` and an exact `fmcg_m20_t003_<32 hex>` database name — PASS, `backend/venv/Scripts/python.exe -m pytest -q tests/test_m20_v03_acceptance.py`: 16 passed, 69 warnings, 27.70 seconds. This run included the new rollback-audit assertion. Warnings are existing Pydantic configuration/deprecation and FastAPI `regex` deprecations.
- Alembic migration round-trip in a separate task-owned PostgreSQL database — PASS. `upgrade head` reached `20261022_0011`; downgrade to `20261021_0010` removed all three MPS numbering sequences; re-upgrade returned to `20261022_0011` and recreated `mps_plan_no_seq`, `mps_line_no_seq`, and `mps_whatif_scenario_no_seq`.
- Independent read-only review of the new rollback-audit assertion — no actionable issue found.

## Limits and cleanup

- The integration fixture seeds `MRPResult` directly; it does not run the upstream MRP calculator to produce those rows.
- Inventory feasibility accounts for reserved quantities, but this suite does not exercise a reservation write/consume workflow.
- Full tenant/company/warehouse and concurrency permutations remain partial, as recorded by `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V05.md`.
- The exact task-owned PostgreSQL containers were removed after verification. Connections used local container trust authentication; no database password was used.

These results are bounded local evidence for T003. They do not accept or close M20, establish remote CI status, or replace the independent milestone audit. M20.S05.T004 remains a separate task.
