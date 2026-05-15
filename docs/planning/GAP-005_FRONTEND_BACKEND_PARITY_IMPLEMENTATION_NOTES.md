# GAP-005 Frontend / Backend Parity Implementation Notes

## Implemented Scope

GAP-005 added a source-level API parity baseline and checker.

Implemented files:

- `frontend/scripts/api-parity-manifest.mjs`
- `frontend/scripts/check-api-parity.mjs`
- `frontend/package.json` script: `check:api-parity`
- `docs/testing/API_PARITY.md`

The checker:

- scans dashboard `.tsx` pages
- detects raw `/api/v1/` usage
- validates manifest frontend route paths
- validates manifest frontend client files when specified
- supports strict mode with `--strict`

## Current Baseline

The current baseline intentionally records existing technical debt:

- 35 manifest entries
- 753 dashboard pages scanned
- 51 known raw API pages
- 0 uncovered raw API pages

Known raw API usage is not considered fixed. It is explicitly tracked so future work can prevent new drift while converting legacy pages incrementally.

## Skipped Subtasks

GAP-005C, GAP-005D, and GAP-005E were skipped because no database migration, ORM model, or runtime API schema is required.

GAP-005G, GAP-005H, and GAP-005I were skipped because the implemented parity check does not require a runtime endpoint, visible UI, or ERP permission.

## Next Cleanup Direction

Convert high-risk raw API pages into shared API clients first:

1. notification center / notifications
2. IoT
3. QMS
4. quality certificates and consumer complaints
5. NPD
6. finance VAT/eTIMS

Each conversion should reduce the manifest allowlist instead of expanding it.

