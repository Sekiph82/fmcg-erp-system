# M20.S05.T004 — virtual factory and F14 evidence (2026-10-29)

## Scope and classification

This receipt covers the owner-authorized synthetic virtual-factory fixture, the V05-F14 `SHIFT_ADD` interval correction, and stricter PostgreSQL currency-code checks. It is bounded local implementation evidence. It is not live factory data, an independent M20 acceptance, or a closure of M20/M21.

Owner decision applied: `Q-M21-S05-T004-M20-DATA`. The fixture represents a synthetic Nairobi FMCG company in KES, two synthetic products with explicit minimum-run and standard-cost values, work center `FILL-01`, an 8-hour `07:00–15:00` shift, a two-operator staffing assumption, 45-minute changeover, 60-minute CIP, and synthetic planner/quality/admin test users. Synthetic employee/operator/machine/shift records are seeded and cleaned up by the PostgreSQL integration test. None of these records describe real people or operations.

The implementation consumes configured minimum runs, setup/CIP time, and same-currency standard costs. Unknown or mismatched inputs remain unknown instead of receiving fabricated defaults. MPS remains work-center-hour based; no claim is made that it verifies a real employee's attendance or qualification.

## V05-F14 remediation

`SHIFT_ADD` now requires a concrete date/start/end interval. The service verifies interval validity and that `hours` matches its duration; rejects overlap with configured calendar shifts and other additions; enforces total remaining daily capacity; and refuses to credit additions against missing or inconsistent calendars. If downtime exists but cannot be compared safely because the work center has no timezone mapping, the added capacity is reported as unresolved/unknown and is not credited. The what-if UI accepts start/end times and shows the derived duration.

A follow-up boundary check showed that a downtime event on the UTC day immediately before or after the local calendar date could otherwise be omitted. Since the work center has no timezone, the service now queries a conservative one-day UTC margin on both sides; any such downtime keeps added capacity unresolved rather than credited. Unit and PostgreSQL tests cover both adjacent UTC-day bounds.

The product standard-cost and scenario impact-currency checks now require three uppercase ASCII letters in PostgreSQL. Migration `20261029_0025` replaces the looser “three uppercase characters” checks; PostgreSQL integration assertions reject malformed values such as `1$A` for both tables.

## Fresh disposable PostgreSQL evidence

- Container: `codex-m20-t004-1f4fa42165e04f6789164d693886187a`, labels `codex.task=M20.S05.T004`, `codex.disposable=true`, `codex.database-purpose=M20-virtual-factory-acceptance`.
- Database: `fmcg_m20_t004_1f4fa42165e04f6789164d693886187a`; loopback-only dynamic port `60522`; PostgreSQL 16; local trust authentication, no password used or saved.
- Migration sequence: `python -m alembic upgrade head`; `python -m alembic downgrade 20261028_0024`; `python -m alembic upgrade head`; `python -m alembic current` → `20261029_0025 (head)`.
- Test command: `python -m pytest -q -W always::pytest.PytestUnraisableExceptionWarning tests/test_m20_strict_findings.py tests/test_m20_remaining_engine.py tests/test_m20_postgres_scenario_savepoint.py tests/test_m20_s01_t001_mps_hardening.py tests/test_m20_s01_t001_v02_mps_remediation.py tests/test_m20_s01_t001_v03_mps_remediation.py tests/test_m20_s01_t002_mps_preservation.py tests/test_m20_v03_acceptance.py tests/test_m20_auth_transaction_boundary.py --tb=short`.
- Final result: **100 passed, 73 warnings, 50.39 seconds**, exit 0. The warnings are recorded in `pytest.log` and are not suppressed. Two preceding attempts failed on intermediate test ordering/count assertions; the corrected final run passed the full command above. Those superseded logs are retained for an honest execution history.
- The task-owned container was removed and its absence verified after the run. The existing application PostgreSQL container was not used by this test.

Additional checks: frontend `npm run type-check` passed; `npm run build` passed; a fresh local frontend run of `npx playwright test e2e/m20-scenario-operations.spec.ts --project=chromium --no-deps --retries=0 --workers=1` passed **3/3 UI serialization tests** against synthetic mocks; backend `py_compile` passed for changed models, schemas, services, migrations and M20 tests; `git diff --check` passed. Raw migration, pytest, type-check, build, Playwright and compile outputs are retained alongside this receipt. The mocked UI run is not a real API/database browser round trip and does not replace the independent visual/trace review.

## Acceptance boundary

The updated behavior and this receipt still require the scheduled independent read-only review at the final implementation SHA. M20 V05 remains `OPEN / CHANGES_REQUIRED` until the independent auditor evaluates F14–F16 and all other mandatory acceptance criteria. UI screenshot/trace review, bounded tenant/company/warehouse and concurrency coverage, development dependency advisory triage, and remote CI (deferred through 2026-10-30) remain separate gates. No GitHub Actions were run, no audit verdict was changed, and no task was marked accepted based on builder tests alone.
