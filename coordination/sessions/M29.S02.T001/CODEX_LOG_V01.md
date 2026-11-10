# M29.S02.T001 — Calibration asset/instrument registry

## Outcome

Extended the existing QMS `InstrumentCalibration` register rather than creating a parallel calibration model. Instruments can now link optionally to a maintenance asset. No facility instruments or calibration evidence were preloaded.

## Changes

- Added an optional `asset_id` relationship to maintenance assets with `ON DELETE SET NULL` and an index.
- Added migration `20261108_0021`; it checks existing calibration intervals before adding the positive-interval constraint and reports invalid rows without silently changing them.
- Replaced untyped calibration create/update bodies with validated schemas and quality view/create/edit permission checks.
- Calibration state is derived from recorded dates. A missing date is returned as `NOT_VERIFIED`, without changing existing rows. Future last-calibration dates and non-positive intervals are rejected. Only `OUT_OF_SERVICE` may be manually set; users cannot assert `CURRENT`.
- Added a standalone registry UI with optional asset linking and a QMS navigation entry. The page explicitly states that instrument registration does not create a calibration event or certificate.
- Updated the route bypass so `/dashboard/qms/calibration` opens this page instead of redirecting to the general QMS workspace.

## Validation evidence

- Python `py_compile` passed for the changed model, schema, QMS endpoint, model exports, and migration modules.
- Imports of the calibration model, schemas, and QMS router passed.
- Alembic reports `20261108_0021` as the current migration head; the migration was not applied to a database.
- Focused ESLint passed for the QMS API client, calibration registry page, QMS dashboard page, middleware, and route redirect map.
- Scoped `git diff --check` passed.
- Independent read-only review found no remaining blocker after fixes for manually asserting calibration status, future dates, and filtering by derived `NOT_VERIFIED` status. No tests were run.

## Deferred verification

Per the M29 milestone test batching decision, database-backed migration and calibration tests remain for M29.S04. Existing database rows were not changed by this task.
