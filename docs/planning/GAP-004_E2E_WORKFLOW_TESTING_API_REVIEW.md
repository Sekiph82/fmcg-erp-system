# GAP-004 End-to-End Workflow Testing API Review

## Task

`GAP-004G: Add or update API endpoints: End-to-End Workflow Completion Testing`

## Decision

No production API endpoint changes are required for this GAP-004 slice.

The goal of GAP-004 is to build an end-to-end workflow testing foundation, not to add test-only production routes. Existing production API routes already cover the first workflow-test contracts documented in `docs/planning/GAP-004_E2E_WORKFLOW_TESTING_SCHEMA_DESIGN.md`.

## Verified API Surface

Route registration was checked inside the development backend container with the same Docker environment used for local startup.

| Contract Area | Existing Route Coverage |
|---|---:|
| Auth login/logout/me and 2FA | 16 routes |
| Module manifest and permission coverage | 2 routes |
| Inventory and serial/lot stock surfaces | 27 routes |
| Procurement and suggestions surfaces | 64 routes |
| Production, advanced production, costing, and AI surfaces | 128 routes |
| Quality inspections and parameters | 17 routes |
| Finance, journal, posting, reversal, and accounting controls | 80 routes |

Representative routes verified:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/modules/manifest`
- `GET /api/v1/modules/permissions/coverage`
- `GET /api/v1/quality/inspections/`
- `POST /api/v1/quality/inspections/`
- `GET /api/v1/finance/journal/`
- `POST /api/v1/finance/journal/`
- `POST /api/v1/finance/journal/{entry_id}/post`
- `POST /api/v1/finance/journal/{entry_id}/reverse`

## Notes

The local Python virtual environment route import still reports missing optional packages such as `pyotp` and `dateutil`. The Docker backend environment registers the relevant routes successfully, so the GAP-004G decision is based on the actual development service environment.

Those local-venv dependency differences should be cleaned up in a separate environment/dependency hardening task if local non-Docker route imports are expected to be authoritative.

## Result

`GAP-004G` is skipped by design.

Reason:

- existing production API endpoints are sufficient for the planned E2E workflow tests
- adding test-only production endpoints would increase attack surface and architecture drift
- the next meaningful task is frontend/browser workflow setup under `GAP-004H`

