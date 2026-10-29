# M27.S04.T003 — UI/E2E acceptance

## Outcome

Added a Quality Gates workspace tab that lists versioned gate definitions and append-only evaluation history, filters audit events by outcome, and shows actor IDs. Users with `quality.view` can review permitted audit history; definition details and controls require `quality.view_all` or `quality.gate_configure`, matching the existing QMS API permission behavior. Configuration users can create the first definition version, close an open effective period, and create the next sequential version with an inclusive, non-overlapping effective date. The form offers only active mandatory blocking QC templates with release requirements and specification parameters, matching backend gate-definition rules.

## Changed Files

- `frontend/src/app/dashboard/quality/page.tsx`
- `frontend/src/components/quality/QualityGateWorkspace.tsx`
- `frontend/src/lib/quality-gates.ts`
- `frontend/e2e/m27-quality-gates.mocked.spec.ts`
- `coordination/sessions/M27.S04.T003/CODEX_LOG_V01.md`

## Verification Evidence

- Targeted ESLint on the changed frontend files — passed.
- `npm run type-check` — passed.
- `npx playwright test e2e/m27-quality-gates.mocked.spec.ts --project=chromium --no-deps --retries=0` — **4 passed**. Coverage includes definition/history display and filtering, first-version creation with required QC template linkage, closing and creating a sequential version, and permission-separated audit versus definition access. API responses are synthetic route mocks.
- Independent read-only review confirmed API/UI permission alignment, actor display, and non-overlapping sequential version dates; no remaining issue.
- `git diff --check` — passed.

## Limits

The E2E suite mocks the API and does not claim browser acceptance against a live backend, deployed system, production factory, or real QC data. No production data or external actor records were used.

No GitHub Actions were dispatched.
