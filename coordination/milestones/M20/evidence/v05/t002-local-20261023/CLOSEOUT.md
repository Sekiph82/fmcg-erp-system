# M20.S05.T002 local closeout — 2026-10-23

## Scope

Frontend planning-board, capacity, campaign, and what-if loading/error/empty/accessibility behavior and user permissions, per `CODEX_M20_MASTER_PROMPT_V04.md` § M20.S05. No remote CI or GitHub Actions were run.

## Changes

- Added accessible loading and error feedback to the four MPS planning views, including errors from their mutations.
- Connected MPS actions to the signed-in user's existing `mps.calculate`, `mps.ai`, `mps.approve`, `mps.release`, `mps.edit`, and `mps.simulate` permissions.
- Added synthetic Playwright coverage for loading, empty results, API denial, mutation-control visibility for a view-only user, and screen-reader error announcements.
- Made the PostgreSQL-backed scenario browser test start with empty browser storage so it authenticates only against its task-owned disposable database.

## Verification

- `npm run type-check` — PASS, exit 0.
- `npm run build` — PASS, exit 0; Next.js generated 699/699 static pages. Existing warnings: package-lock is outside the repository, React 18 support is deprecated in Next.js 16, and the middleware convention is deprecated.
- `E2E_BASE_URL=http://127.0.0.1:3017 E2E_SKIP_WEBSERVER=1 npx playwright test e2e/m20-mps-views.spec.ts --project=chromium --no-deps --workers=1 --retries=0` — PASS, 12/12. These UI states use synthetic responses.
- Fresh PostgreSQL 16 run — PASS. Created a task-owned disposable database named `fmcg_m20_t002_f9cb88acb25a4ffd9f456fa6caf21891` in a new container bound only to `127.0.0.1:55436`; Alembic upgraded it through `20261022_0011`. Seeded only synthetic `M20-OPS-PLAN-` planning data and a disposable admin. Ran `e2e/m20-scenario-backend-roundtrip.spec.ts` with `M20_DISPOSABLE_TEST_DATABASE=1` and the exact database name — PASS, 1/1. Browser observed plan/line/scenario reads at HTTP 200, scenario creation at HTTP 201, and the saved 100.0% service-level / zero-delay KPIs after reload. The screenshot is `m20-scenario-backend-roundtrip.png` beside this file.
- Independent read-only review of the four UI pages, the 12-case UI suite, and isolated browser-storage change — no actionable issues.

## Cleanup and limits

Stopped the task-owned backend/frontend processes and removed the exact disposable PostgreSQL container after the run. No database password was used. PostgreSQL trusted connections were available only through the container's loopback-published port during the test. The test created scenario history only in this disposable database.

These results establish local implementation and execution evidence for T002. They do not self-approve M20, replace the independent M20 audit, or establish remote CI status.
