# M21.S04.T001 — Advanced BOM/conversion API contracts

## Findings and changes

The backend already returned the conversion-profile IDs, tolerance/density values, linked packaging BOM ID, and notes, but the frontend response type omitted them. The create form reused the response type, so it also exposed response-only fields as writable input. The package-components GET endpoint had no typed frontend client contract. The conversion endpoint accepted nonpositive quantities at its service boundary, and the list endpoint documentation incorrectly said that an omitted date filters to today even though it returns every active profile.

- Added a dedicated `ConversionProfileCreate` frontend type and made the create form/client use it; completed the response type with the fields in `ConversionProfileOut`.
- Added frontend types and a read-only client method for package-component calculations.
- Matched conversion-profile input precision and bounds to the existing database columns, rejected blank profile names and inconsistent fill-volume/UOM input, and normalized a supplied fill UOM.
- Rejected nonpositive/nonfinite conversion source quantities in both the API query contract and service.
- Corrected the list endpoint description to match its behavior: omitted `as_of_date` returns all active profiles; a supplied date applies the inclusive effective window.

No schema migration was required. Existing profile versions remain explicitly selected by ID; this task adds no automatic version resolver or approval policy.

## Verification evidence

- Backend regression suite: `50 passed, 2 skipped` across M21.S01 profile, density/UOM, package-component, versioning, and M21.S04 contract tests. The skipped cases require task-owned disposable PostgreSQL runs; no database acceptance is claimed for this task.
- Python compilation passed for the changed schema, endpoint, service, and contract test.
- Frontend `npm.cmd run type-check` passed.
- FastAPI OpenAPI generation succeeded and listed create, list, calculate, and package-components operations. It emitted existing warnings in unrelated allergen/webhook routes (deprecated `regex` and duplicate operation ID).
- `git diff --check` passed.
- Independent read-only review found no blocker in request/response parity, DB precision alignment, positive finite quantity handling, or preservation of existing date/version behavior.

## Scope limits

- No production or owner data was accessed, and no schema changes were made.
- Database-backed M21.S01 regression tests were not rerun in a disposable database here; their earlier task logs retain their bounded PostgreSQL evidence.
- Co-product/by-product cost allocation and substitute approval semantics remain pending the owner decisions tracked as Q-M21-S03-T002-COSTING-BASIS and Q-M21-S03-T003-APPROVAL-GOVERNANCE.
