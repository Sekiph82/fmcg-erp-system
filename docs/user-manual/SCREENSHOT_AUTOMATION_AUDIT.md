# Screenshot Automation Audit

## Purpose

This audit records the current repository state before implementing the Playwright screenshot capture workflow for the FMCG ERP user manual.

## Current State

| Area | Status | Evidence | Notes |
|---|---|---|---|
| Manual audit source | Existing | `docs/user-manual/MANUAL_AUDIT.md` | Contains `754` frontend pages and `618` nav items that can seed route discovery. |
| Screenshot output folder | Missing | `docs/user-manual/screenshots` not found | Must be created by the screenshot automation implementation task. |
| Screenshot route manifest | Missing | `docs/user-manual/screenshots/routes.json` not found | Should be generated from nav config and app routes, then manually adjustable. |
| Screenshot index | Missing | `docs/user-manual/screenshots/screenshots-index.json` not found | Should record captured, failed, and skipped routes. |
| Screenshot README | Missing | `docs/user-manual/screenshots/README.md` not found | Should explain credentials, startup, reruns, troubleshooting, and route maintenance. |
| Playwright package declaration | Missing from package.json | `frontend/package.json` has no `@playwright/test` dependency and no screenshot script | `frontend/package-lock.json` references optional Playwright metadata, but `node_modules/@playwright/test` is not installed. |
| Screenshot capture script | Missing | No `frontend/scripts` folder and no capture script found | Recommended path: `frontend/scripts/capture-user-manual-screenshots.ts`. |
| Package script | Missing | `frontend/package.json` only has `dev`, `build`, `start`, `lint`, and `type-check` | Recommended script: `manual:screenshots`. |
| Login credentials handling | Missing | No manual screenshot env vars found | Must use `MANUAL_TEST_BASE_URL`, `MANUAL_TEST_USERNAME`, and `MANUAL_TEST_PASSWORD`; do not hardcode secrets. |
| Safe read-only behavior | Missing | No screenshot crawler exists | The future crawler must not create, edit, delete, approve, reject, submit, send, pay, recall, or mutate business data. |

## Route Sources Available

The screenshot crawler should discover or seed routes from:

- `docs/user-manual/MANUAL_AUDIT.md`
- `frontend/src/components/nav-config.tsx`
- `frontend/src/app/**/page.tsx`
- `frontend/src/lib/modules.ts`
- runtime sidebar links after login, if the app is running

## Required Future Implementation

The implementation task should add:

- `docs/user-manual/screenshots/`
- `docs/user-manual/screenshots/README.md`
- `docs/user-manual/screenshots/routes.json`
- `docs/user-manual/screenshots/screenshots-index.json`
- `frontend/scripts/capture-user-manual-screenshots.ts`
- a `manual:screenshots` package script in `frontend/package.json`
- Playwright as a frontend development dependency if it is still absent

## Acceptance Notes For Future Crawler

The screenshot crawler should:

1. Require credentials through environment variables.
2. Fail fast with clear instructions if credentials are missing.
3. Fail fast if login fails.
4. Continue route capture after individual page failures.
5. Store each route status as `captured`, `failed`, or `skipped`.
6. Extract visible read-only actions where possible.
7. Avoid all mutating actions.
8. Write relative screenshot paths into `screenshots-index.json`.

## Blockers

- Playwright is not currently installed in `frontend/node_modules`.
- The app must be running before screenshots can be captured.
- Test credentials are required for the future screenshot run.
- Demo data may be needed for detail/edit/modal screenshots, but the crawler should not create data.

