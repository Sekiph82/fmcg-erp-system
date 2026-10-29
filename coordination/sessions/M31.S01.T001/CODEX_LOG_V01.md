# M31.S01.T001 — API client/application registry

## Scope and acceptance material

Implemented the exact root `TASKS.md` task: an authenticated, permission-protected registry for API client application metadata. The task row had no separate acceptance link. Reviewed `docs/planning/GAP-016_API_DOCS_DEVELOPER_PORTAL_AUDIT.md`, its implementation notes, and `docs/planning/GAP-006_REAL_INTEGRATIONS_AUDIT.md` as the latest applicable developer-portal/integration audits.

GAP-016 predates the current API-key CRUD implementation: the current `api_portal.py` already has per-user API-key endpoints and corresponding tables. This task adds a distinct application registry and does not duplicate or change key/OAuth credential lifecycle, which remains the next task. The application record contains metadata only; it neither creates credentials nor claims a live external integration.

## Implementation

- Added `ApiClientApplication` and additive Alembic revision `20261029_0042`, with owner-user foreign key/cascade, a per-owner/name/environment uniqueness rule, allowed environments (`development`, `sandbox`, `production`), activity state, and created/updated timestamps.
- Added authenticated API list/create/update operations under `/api/v1/developer/applications`. Reads require `integrations.view`; writes require `integrations.edit`. Records are scoped to their owner, duplicate registrations return a conflict, and another user's record is concealed as not found.
- Added a Developer Portal applications screen for registering metadata and deactivating/reactivating records. It explicitly says the registry does not create credentials or connect to an external partner.
- Migration adoption validates the existing table's columns/types/nullability, timestamp/default values, primary and unique keys, owner foreign key, owner index, and exact canonical environment check expression before accepting a table that the Alembic compatibility patch would otherwise skip. Downgrade takes an `ACCESS EXCLUSIVE` lock and refuses to drop non-empty application data.

## Verification

- Task-owned disposable PostgreSQL runner: `coordination/sessions/M31.S01.T001/run_registry_tests.ps1`.
- Final run: **4 passed**, Alembic `20261029_0042 (head)`. PostgreSQL 16 image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`; database `fmcg_m31_s01_t001_2d7d27df4be44c37a8fb`; random host port bound only to loopback; no password or volume; task-labeled container removed by the runner.
- Tests cover application CRUD, duplicate/environment validation, normal integrations.view/edit grant and denied write, owner isolation, no credential/API-key creation, migration constraints, populated-downgrade refusal, and concurrent writer blocking while the exclusive downgrade lock is held.
- Runner migration probes also verified baseline-schema adoption, actual 0041→0042 table creation, rejection of incompatible existing columns, missing timestamp defaults, and a weakened `OR TRUE` environment constraint. Final migration head was rechecked after the probes.
- Backend Python compile passed. Frontend type-check and targeted ESLint passed. `git diff --check` passed.
- Pytest emitted existing Pydantic/deprecation warnings from unrelated modules; no test failed.

## Limits

- Records and test actors were synthetic. No real partner, credential, company integration, or production access was created or accepted.
- API-key/OAuth lifecycle, scopes/rate limits, event contracts, delivery, webhook signing, and usage analytics remain outside T001.
