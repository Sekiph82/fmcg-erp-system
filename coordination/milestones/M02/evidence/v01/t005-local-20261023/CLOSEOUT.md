# M02.S03.T005 — CSRF and company isolation

**Result:** Focused local runtime verification complete. This evidence does not claim deployment verification or production security acceptance.

## Delivered

- Added origin validation for state-changing API requests in the production FastAPI app. A supplied Origin must match a configured frontend origin; Referer is checked when Origin is absent. CORS preflight requests continue through the configured CORS middleware.
- Added a disposable-PostgreSQL integration test that runs the production app with task-local database dependencies and synthetic user, permission, role, session family, and two companies.
- Verified credentialed CORS preflight behavior, rejection of an attacker-origin form POST without changing the database, acceptance of an allowed-origin POST, company list scoping, access to the assigned company, and denial of the unassigned company.
- The test refuses to write unless `M02_DISPOSABLE_TEST_DATABASE=1` and `DATABASE_URL` points to the exact loopback database matching `M02_DISPOSABLE_TEST_DATABASE_NAME` and the T005 disposable-name pattern.

## Verification evidence

- Focused backend run: `python -m pytest -q tests/test_m02_security_runtime.py tests/test_gap025_multi_company_branch.py tests/test_hardening.py::test_auth_cookie_is_httponly_and_uses_configured_security_flags tests/test_hardening.py::test_clear_auth_cookie_expires_auth_cookie` — **25 passed**, 67 Pydantic deprecation warnings.
- The focused integration run used only loopback PostgreSQL database `fmcg_m02_t005_c5d8a9046fe24ae6b1ec` in task-labeled container `fmcg-m02-s03-t005-c5d8a9046fe24ae6b1ec` (`codex.task=M02.S03.T005`). Migrations completed through `20261023_0014`. No owner or production data was used.
- An additional broader run of `tests/test_m02_security_runtime.py`, `tests/test_gap025_multi_company_branch.py`, and `tests/test_hardening.py` reported 44 passed and 4 failures in unrelated existing `test_hardening.py` cases that patch the removed `app.core.deps.decode_token` symbol or assume router objects expose `.path`. The two directly relevant cookie tests passed in the focused run above.
- Python compilation of the changed middleware, app entry point, and integration test — passed.
- `git diff --check` — passed.
- Independent read-only review found no concrete blocker. The reviewer confirmed override restoration, cleanup on assertion/authentication failures, production-app use, session-family token issuance, and the covered CSRF/company-boundary assertions.

## Limits

- The API was exercised through the production FastAPI app using ASGI transport against the migrated disposable database. This does not verify a deployed Uvicorn/TLS environment or a live browser session.
- Cookie attributes were checked using the production cookie helper; an actual login or refresh HTTP response was not exercised by this test.
- The broad hardening run retains four unrelated failures described above. Those failures have not been changed or represented as passing.
- No GitHub Actions, production deployment, external security audit, or owner acceptance was performed.
