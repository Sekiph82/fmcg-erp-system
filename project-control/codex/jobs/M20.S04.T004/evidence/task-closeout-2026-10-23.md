# M20.S04.T004 Closeout

Task: **Compare scenarios using service/cost/capacity KPIs**

## Changes and evidence

- Scenario comparison now calculates deltas from the persisted baseline and candidate snapshots and returns percentage-point service-level change, delayed-line count, material-shortage count and quantity by source UOM, capacity-overload hours, and configured changeover hours.
- Each metric includes units, input completeness/status, and a source description. The result carries deduplicated unknown inputs and an explicit partial-input confidence status.
- Estimated cost remains `null` with `UNKNOWN_NO_APPROVED_CURRENCY_BASIS`; missing CIP duration remains an explicit unknown. No monetary precision or owner data was fabricated.
- The what-if page now displays the shortage, capacity, changeover, cost, and unknown-input results with their units and sources.
- Added PostgreSQL assertions for shortage quantity deltas, units, source, confidence, and cost/CIP unknowns. Independent read-only review found no concrete issue.

## Verification

- Disposable PostgreSQL 16 loopback database: Alembic `upgrade head` succeeded; both task-scoped MPS test files completed with **24 passed, 69 warnings**. The ephemeral database/container was removed after the run and its generated password was not recorded.
- Frontend `npm run type-check` passed.
- Focused ESLint on `src/lib/mps.ts` and `src/app/dashboard/mps/whatif/page.tsx` passed.
- `git diff --check` passed.
- GitHub Actions and remote CI were not run under the M20 quota restriction through 2026-10-30.

## Known limits

- Approved currency/cost basis, CIP duration, minimum-run, and complete live-like permission evidence remain external owner-data/runtime gates. Comparisons expose these gaps instead of guessing.
- This is local implementation evidence and does not claim independent milestone audit acceptance.
