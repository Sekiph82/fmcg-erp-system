# M21.S01.T004 — Version/effective-date conversion profiles

## Result

Implemented versioned conversion profile families using `(profile_code, version_no)` identity, inclusive effective date windows, API validation/filtering, calculation-time checks, and frontend creation/display of profile versions and dates. The existing profile ID remains explicit for calculations; no automatic version resolver or approval policy was introduced.

## Verification evidence

- Disposable PostgreSQL 16 run: `10 passed in 4.59s` for `backend/tests/test_m21_s01_t004_profile_versions_db.py`.
- Migration state: `20261028_0018`, applied after `20261028_0017`.
- Disposable database: `fmcg_m21_s01_t004_6a35f1af7be546dab27752aa`; synthetic profile-version data only, loopback-bound ephemeral port, no volume mounts.
- Task-labelled disposable container cleanup: verified; no container remained for label `codex.task=M21.S01.T004`.
- Focused unit suite: `31 passed in 5.23s` across M21.S01.T001–T004 tests.
- Frontend: `npm.cmd run type-check` passed (`tsc --noEmit`).
- Python compilation: passed for modified M21 backend modules, migration, and tests.
- `git diff --check`: passed.
- Independent read-only review: no blocking issues found in migration safety, version uniqueness, inclusive dates, API/UI behavior, or calculation eligibility.

## Scope and limits

The database test used only the temporary task database above; no production or owner data was accessed. The downgrade refuses to collapse multiple versions sharing one profile code. Concurrent duplicate inserts still rely on the database uniqueness constraint and may surface as a database conflict rather than the pre-check's HTTP 409 response; this was reviewed as non-blocking for this task.
