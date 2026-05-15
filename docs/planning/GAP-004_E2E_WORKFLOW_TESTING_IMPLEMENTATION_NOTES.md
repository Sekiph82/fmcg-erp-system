# GAP-004 End-to-End Workflow Testing Implementation Notes

## Implemented Scope

GAP-004 now provides a safe E2E testing foundation without adding production-only shortcuts or destructive test reset behavior.

Implemented pieces:

- deterministic backend E2E fixture/persona helpers under `backend/tests/e2e`
- backend seed-contract tests for E2E role expectations
- Playwright browser configuration under `frontend/playwright.config.ts`
- credential-aware browser auth helpers under `frontend/e2e/helpers`
- public auth smoke tests
- authenticated shell and route smoke scaffolding
- critical workflow page smoke tests for Inventory, Production, Quality, Finance, Procurement, and Sales
- workflow-control tests for key operational screens
- minimal stable selectors for E2E-relevant pages
- E2E runbook at `docs/testing/E2E.md`
- role expectation document at `docs/planning/GAP-004_E2E_ROLE_EXPECTATIONS.md`

## Intentional Skips

No application database migration, production ORM model, or production API schema change was needed for this testing foundation.

No test-only users or permissions were added. Browser tests use environment-driven credentials and skip authenticated checks when credentials are absent.

## Verification Commands

From `backend`:

```powershell
.\venv\Scripts\python.exe -m pytest tests\e2e -q
```

From `frontend`:

```powershell
npm run type-check
npm run test:e2e -- --list
npm run test:e2e -- --project=chromium
```

No-secret Playwright runs should pass public auth checks and skip authenticated/data-dependent checks.

## Follow-Up Coverage

Future GAP work can increase E2E depth by provisioning safe development users and non-destructive seed records for:

- editable warehouse stock plus view-only warehouse stock
- production orders in draft, released, in-progress, and completed states
- QC lots or inspections that can be approved/released only inside assigned scope
- posted and draft finance records
- sales customers split by region or customer group
- procurement requisitions/orders split by department/category scope

Those fixtures should be idempotent, development-only, and never require database resets.

