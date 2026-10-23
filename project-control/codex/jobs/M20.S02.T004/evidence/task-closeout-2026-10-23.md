# M20.S02.T004 — Per-line shortage and constraint diagnostics

## Scope and implementation

The persisted MPS line diagnostic now has a typed API response contract. Every evaluator issue carries a reason code, priority, provenance, required date, and planned quantity; material shortage reasons retain material identity, required/available/short quantities, UOM, lead time, latest order date, substitution policy, and excluded receipt explanations. The endpoint retains its existing permission and warehouse-scope checks. Read-time enrichment derives missing line metadata and safe reason defaults for previously stored diagnostics without rewriting historical rows. Stored priorities remain unchanged; absent material-short priorities derive as HIGH and other blocking evaluator reasons derive as CRITICAL.

The MPS constraints page now presents line identity/status, planned quantity and required date, then each issue's priority, material, quantities, timing, substitution/receipt context, and source. It shows unavailable values explicitly and does not promote a constrained line to FEASIBLE.

## Verification

- `python -m pytest tests/test_m20_v03_acceptance.py -q --disable-warnings` on a fresh, task-owned PostgreSQL 16 disposable database with a loopback-only port and tmpfs data directory — **12 passed, 67 warnings**. The generated password was not saved or reported; test environment and database container were removed after each run.
- Focused PostgreSQL diagnostics test covers new persisted fields, typed response parsing, and read-time enrichment of a legacy diagnostic missing the new fields — **1 passed** after the final legacy-priority derivation change.
- `python -m pytest tests/test_m20_remaining_engine.py -q` — 30 passed.
- `npm run type-check` in `frontend` — passed.
- `python -m py_compile app/schemas/mps.py app/services/mps_advanced_service.py app/api/v1/endpoints/mps.py tests/test_m20_v03_acceptance.py` — passed.
- `git diff --check` — passed.

## Independent review and limits

An independent read-only reviewer found no concrete correctness, compatibility, or security issue in the response model, scoped API, legacy enrichment, or presentation. The reviewer did not run tests or access a database. GitHub Actions were not run, consistent with the M20 CI hold through 2026-10-30. The latest M20 audit still records milestone-wide owner-data, CI, and visual acceptance gates; this task does not claim to close those gates.
