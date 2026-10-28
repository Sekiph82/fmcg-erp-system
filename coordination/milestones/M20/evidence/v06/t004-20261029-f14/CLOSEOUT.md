# M20.S05.T004 — virtual factory and F14 evidence (2026-10-29)

## Scope and classification

This receipt covers the owner-authorized synthetic virtual-factory fixture and the V05-F14 SHIFT_ADD interval correction. It is bounded local implementation evidence. It is not live factory data, an independent M20 acceptance, or a closure of M20/M21.

Owner decision applied: `Q-M21-S05-T004-M20-DATA`. The fixture represents a synthetic Nairobi FMCG company in KES, two synthetic products with explicit minimum-run and standard-cost values, work center `FILL-01`, an 8-hour `07:00–15:00` shift, a two-operator staffing assumption, 45-minute changeover, 60-minute CIP, and synthetic planner/quality/admin test users. Synthetic employee/operator/machine/shift records are seeded and cleaned up by the PostgreSQL integration test. None of these records describe real people or operations.

The implementation consumes configured minimum runs, setup/CIP time, and same-currency standard costs. Unknown or mismatched inputs remain unknown instead of receiving fabricated defaults. MPS remains work-center-hour based; no claim is made that it verifies a real employee's attendance or qualification.

## V05-F14 remediation

`SHIFT_ADD` now requires a concrete date/start/end interval. The service verifies interval validity and that `hours` matches its duration; rejects overlap with configured calendar shifts and other additions; enforces total remaining daily capacity; and refuses to credit additions against missing or inconsistent calendars. If downtime exists but cannot be compared safely because the work center has no timezone mapping, the added capacity is reported as unresolved/unknown and is not credited. The what-if UI accepts start/end times and shows the derived duration.

## Fresh disposable PostgreSQL evidence

- Container: `codex-m20-t004-9057a3745afa4d89be700f4eb381afef`, labels `codex.task=M20.S05.T004`, `codex.disposable=true`, `codex.database-purpose=M20-virtual-factory-acceptance`.
- Database: `fmcg_m20_t004_9057a3745afa4d89be700f4eb381afef`; loopback-only dynamic port `52432`; PostgreSQL 16; local trust authentication, no password used or saved.
- Migration sequence: `python -m alembic upgrade head`; `python -m alembic downgrade 20261028_0023`; `python -m alembic upgrade head`; `python -m alembic current` → `20261028_0024 (head)`.
- Test command: `python -m pytest -q -W always::pytest.PytestUnraisableExceptionWarning tests/test_m20_strict_findings.py tests/test_m20_remaining_engine.py tests/test_m20_postgres_scenario_savepoint.py tests/test_m20_s01_t001_mps_hardening.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py tests/test_m20_s01_t002_mps_preservation.py tests/test_m20_v03_acceptance.py tests/test_m20_auth_transaction_boundary.py --tb=short`.
- Result: **100 passed, 73 warnings, 56.98 seconds**, exit 0. The warnings are recorded in `pytest.log` and are not suppressed.
- The task-owned container was removed and its absence verified after the run. The existing application PostgreSQL container was not used by this test.

Additional checks: frontend `npm run type-check` passed; backend `py_compile` passed for changed models, schemas, services, migrations and M20 tests; `git diff --check` and `git diff --cached --check` passed. Raw migration, pytest, type-check and compile outputs are retained alongside this receipt.

## Acceptance boundary

The updated behavior and this receipt still require the scheduled independent read-only review at the final implementation SHA. M20 V05 remains `OPEN / CHANGES_REQUIRED` until the independent auditor evaluates F14–F16 and all other mandatory acceptance criteria. UI screenshot/trace review, bounded tenant/company/warehouse and concurrency coverage, development dependency advisory triage, and remote CI (deferred through 2026-10-30) remain separate gates. No GitHub Actions were run, no audit verdict was changed, and no task was marked accepted based on builder tests alone.
