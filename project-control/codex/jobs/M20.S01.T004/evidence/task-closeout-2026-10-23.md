# M20.S01.T004 — acceptance dataset and regression suite closeout

## Scope and tracker state

The canonical `TASKS.md` row for **M20.S01.T004 — Define MPS acceptance dataset and regression suite** is `[x]`. The explicit next task is **M20.S02.T001 — Consolidate demand inputs: sales orders/forecast/safety stock**. T004 acceptance follows the M20 master execution prompt and the latest applicable strict audit, V05.

The acceptance fixture is synthetic and exercises the MPS material-feasibility service against PostgreSQL-backed BOM, inventory, and plan records. Regression coverage also includes scenario merge/split/shift behavior, demand/material diagnostics, release permission and rollback behavior, and MPS sequence allocation.

## Local verification

- `node --test scripts/codex/job-state.test.mjs scripts/codex/task-queue.test.mjs` — **19 passed**.
- `python -m pytest backend/tests/test_m20_v03_acceptance.py -k disposable_database_guard backend/tests/test_m20_s01_t001_v02_mps_remediation.py -q` — **1 passed, 23 deselected**.
- Disposable PostgreSQL, freshly migrated to Alembic head in a loopback-only Docker container with a `tmpfs` data directory and a random per-run database name: `pytest tests/test_m20_v03_acceptance.py tests/test_m20_remaining_engine.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_mps_sequences.py -q` — **64 passed, 69 warnings in 50.77s**. The database container and generated password were removed/not retained after the run; no owner database was used.
- `python -m py_compile backend/tests/test_m20_v03_acceptance.py`, `node --check scripts/codex/job-state.mjs`, and `git diff --check` — passed.

Warnings were Pydantic protected-namespace/deprecation and FastAPI `regex` deprecations. No warning was suppressed or represented as a test failure.

## Earlier test-scope incident

An earlier, incorrectly scoped T004 test invocation used the normal local `fmcg_erp` compose database and advanced MPS plan/line/scenario sequence counters. It inserted or deleted no business rows. This was disclosed to the owner when it occurred. The later 64-test run above used only the fresh disposable container described above.

## Safety and independent review

The PostgreSQL integration guard now requires explicit opt-in, PostgreSQL on loopback, and exact equality between the live SQLAlchemy database name and a per-run `M20_DISPOSABLE_TEST_DATABASE_NAME` matching `fmcg_m20_<task>_<20-32 hex chars>`. A mismatch fails before integration writes. The Playwright scenario roundtrip requires the same explicit opt-in, a loopback backend URL, and the exact-name format before login or API calls. These name/loopback checks reduce accidental target mismatches but do not prove that a database is disposable; that fact comes from the runner creating a task-owned ephemeral database and starting the backend with the matching `DATABASE_URL` and name. The browser test cannot independently introspect an already-running backend's database connection.

The independent read-only reviewer confirmed the `.next/dev/types` imports were removed, the job-path containment check is portable, and the new database guards address the reviewed findings. The reviewer identified the backend-startup condition above as a run setup invariant. The browser roundtrip was **not rerun after this guard-only change**, so this closeout does not claim fresh Playwright evidence for the final guard revision. GitHub Actions were not run.
