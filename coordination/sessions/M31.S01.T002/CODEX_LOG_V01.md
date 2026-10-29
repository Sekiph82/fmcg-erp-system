# M31.S01.T002 — API key/OAuth credential lifecycle

## Scope

Implemented the lifecycle of developer API-key credentials and OAuth client-secret records for registered applications. The work is software-only and uses synthetic test data. It does not connect to a partner, enable API-key authentication, or implement OAuth token issuance. Existing ERP API authentication remains cookie-based. Scope and rate-limit policy remain for M31.S01.T003.

## Changes

- Linked newly issued API keys to an active application owned by the signed-in user while preserving legacy unlinked key rows. Added one-time issue, atomic rotate, revoke, and owner-scoped listing. Only a high-entropy key hash is stored.
- Added per-application OAuth client-secret records with one-time issue, atomic rotate, revoke, expiry, and owner-scoped listing. Only a high-entropy secret hash is stored; response/list schemas never expose the hash.
- Required `integrations.view` for credential reads and `integrations.edit` for credential changes. Credential issue and rotation lock the owning application row before writing; application deactivation uses the same lock order and revokes linked active credentials in the same transaction. Reactivation does not restore them.
- Rejected past expiry values. Legacy API-key expiry timestamps are interpreted as UTC and serialized with an explicit `+00:00` offset so the browser compares the same instant.
- Added migration `20261029_0043`. It validates the API-key link and exact OAuth secret-table shape/defaults/constraints when adopting existing schemas. Downgrade refuses to delete OAuth records or application links.
- Updated the developer UI for application-linked key creation, issue-once secret display, rotation/revocation and clear limitations. Expired credentials direct the user to issue a replacement instead of showing a failing rotate action.

## Verification

- Task-owned disposable PostgreSQL runner: `coordination/sessions/M31.S01.T002/run_credential_lifecycle_tests.ps1`.
- PostgreSQL `postgres:16-alpine`, image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`; database/container suffix `a9d17a3297c94f918016`; host port was bound only to `127.0.0.1`, with no volume mount. Runner verified container labels and removed it. No password was configured or emitted.
- Result: 2 passed, 72 warnings in the test process. Warnings are pre-existing repository-wide Pydantic/regex and SQLAlchemy `utcnow()` deprecations.
- Covered guard rejection for wrong task/non-loopback databases; owner isolation; read/edit permissions; API key and OAuth hash-only persistence; one-time response/list behavior; create/rotate/revoke; expiry rejection/UTC serialization; inactive-application issuance/rotation rejection; application-deactivation revocation; and downgrade refusal while credential data exists.
- Runner also verified empty downgrade to `20261029_0042`, fail-closed rejection of an incompatible pre-existing OAuth-secret table, and clean migration back to `20261029_0043` head.
- Backend `py_compile`, frontend `npm run type-check`, targeted ESLint, and `git diff --check` passed.
- Independent read-only reviewer found and rechecked race/expiry issues; final review reported no remaining blockers. Reviewer did not run tests.

## Limitations

These records are management metadata for later API/OAuth protocol work. API keys and client secrets are not accepted by API routes as authentication credentials, and no external OAuth provider/token endpoint exists in this task. There is no invented default expiry, live partner, or production-usage claim.

## Next task

Selected `M31.S01.T003 — Scope/rate-limit policy`, the direct next dependency in the partner API governance sprint. This task defines credential permissions and rate policy that T002 deliberately leaves unchanged.
