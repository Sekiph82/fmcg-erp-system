# User Manual Workspace

This folder is the working area for the FMCG ERP user manual workflow.

## Current Artifact

- `MANUAL_AUDIT.md` is the static repository audit used before screenshot capture and final manual generation.
- `SCREENSHOT_AUTOMATION_AUDIT.md` records the pre-implementation screenshot tooling audit.
- `screenshots/` contains the Playwright screenshot capture README, route manifest, and capture index.

The audit inventories:

- frontend pages and routes from `frontend/src/app`
- sidebar/navigation entries from `frontend/src/components/nav-config.tsx`
- visible button/action labels discoverable from static frontend code
- backend API endpoints from `backend/app/api/v1/endpoints`
- module completeness signals
- workflow/status enums
- route permission markers
- mock, stub, placeholder, TODO, and development-only markers

## How To Use The Audit

Use `MANUAL_AUDIT.md` as the source map for the next documentation steps:

1. Build screenshot automation from the frontend route inventory.
2. Capture screenshots and action metadata into `docs/user-manual/screenshots`.
3. Generate the final user manual from the audit, screenshot index, existing docs, and current code.

The final user manual must not claim a feature is complete unless the audit and runtime screenshots support that claim.

## Known Limits

`MANUAL_AUDIT.md` is generated from static code inspection. It cannot prove:

- whether every page loads successfully at runtime
- whether every button works with live backend data
- whether a backend endpoint is truly connected to a frontend action
- whether permissions are enforced in services or middleware not visible from route decorators
- whether generated or dynamic UI actions appear after interaction

When the audit says `Not clearly discoverable`, keep that language in the final manual until browser or runtime verification confirms the behavior.

## Verification

The audit has a focused regression test:

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_manual_audit_docs.py -v
```

This test verifies required audit sections, inventory depth, and uncertainty language.

The screenshot automation contract has a focused regression test:

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/test_screenshot_automation_docs.py -v
```

This test verifies the package script, Playwright dependency, read-only capture script contract, route manifest shape, screenshot index, and screenshot README.

## Screenshot Capture Command

After the ERP is running, set credentials and run:

```powershell
$env:MANUAL_TEST_BASE_URL = "http://localhost:3000"
$env:MANUAL_TEST_USERNAME = "<username>"
$env:MANUAL_TEST_PASSWORD = "<password>"
cd frontend
npm run manual:screenshots
```

Screenshots and capture metadata are stored under `docs/user-manual/screenshots/`.
