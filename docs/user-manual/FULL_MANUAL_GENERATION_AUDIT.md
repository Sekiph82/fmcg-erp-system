# Full Manual Generation Audit

## Purpose

This audit records whether the repository is ready to generate the complete FMCG ERP user manual.

## Current Inputs

| Input | Status | Evidence | Notes |
|---|---|---|---|
| Static manual audit | Existing | `docs/user-manual/MANUAL_AUDIT.md` | Contains `754` frontend pages, `618` navigation items, `2718` backend endpoints, and mock/stub inventory. |
| Screenshot route manifest | Existing | `docs/user-manual/screenshots/routes.json` | Contains routes generated from the sidebar/navigation configuration. |
| Screenshot capture index | Existing but empty | `docs/user-manual/screenshots/screenshots-index.json` | Currently `[]`; no captured screenshots are available yet. |
| Screenshot files | Missing | `docs/user-manual/screenshots/**/*.png` not present | Requires running `npm run manual:screenshots` after starting the ERP and setting credentials. |
| Existing legacy manual docs | Existing | `docs/USER_MANUAL_*.md` | Useful context, but final manual must still be based on current code and the new audit. |
| User manual workspace index | Existing | `docs/user-manual/INDEX.md` | Currently a minimal screenshot-library placeholder. |

## Readiness Assessment

| Area | Readiness | Notes |
|---|---|---|
| Module/page inventory | Ready | `MANUAL_AUDIT.md` is available and tested. |
| Button/action inventory | Ready for first draft | Static extraction exists, but dynamic menus still need screenshot/browser verification. |
| Backend endpoint inventory | Ready for first draft | Endpoint inventory exists; frontend connection certainty remains partial for many endpoints. |
| Permission inventory | Partial | Static scan flags route-level permission markers, but runtime and service-level enforcement still need review. |
| Screenshot references | Not ready | No captured screenshots exist yet; final manual must not reference screenshots until capture has been run. |
| Final chapter generation | Not ready for screenshot-rich manual | It can be drafted without screenshots, but the planning document explicitly recommends running screenshot capture before final manual generation. |

## Required Before Final Manual Generation

1. Start the ERP locally with `start-dev.bat` or Docker Compose.
2. Set:
   - `MANUAL_TEST_BASE_URL`
   - `MANUAL_TEST_USERNAME`
   - `MANUAL_TEST_PASSWORD`
3. Run:

   ```powershell
   cd frontend
   npm run manual:screenshots
   ```

4. Review `docs/user-manual/screenshots/screenshots-index.json`.
5. Confirm enough core routes have `status: "captured"` for useful manual screenshots.
6. Only then generate the final manual chapters.

## If Manual Generation Proceeds Before Screenshots

If the user explicitly asks to generate the manual before screenshot capture, the manual must:

- state `No screenshot captured for this module yet.`
- avoid image references to missing files
- mark uncertain frontend/backend behavior as `Not clearly discoverable from current code`
- mark mock/stub/development-only features honestly
- use `MANUAL_AUDIT.md` and existing docs as the primary evidence

## Recommended Next Task

Run the screenshot capture against the live ERP before generating the full manual. If screenshots cannot be captured yet, mark full manual generation as `NEEDS_USER_REVIEW` or produce a screenshot-free draft only with explicit caveats.

