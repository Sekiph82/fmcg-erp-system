# User Manual Screenshots

Auto-captured screenshots for the FMCG ERP user manual.

## Setup

Set environment variables before running:

```bash
export MANUAL_TEST_BASE_URL=http://localhost:3000
export MANUAL_TEST_USERNAME=admin@example.com
export MANUAL_TEST_PASSWORD=yourpassword
```

Then run from the frontend directory:

```bash
npm run manual:screenshots
```

## Read-Only Safety Rules

The capture script is **read-only** — it navigates and screenshots only.
It must never approve, reject, delete, submit forms, create records, send payments, run recalls, or mutate any data.

## Output

- `screenshots-index.json` — index of all captured screenshots (empty until first run)
- `routes.json` — manifest of routes to capture
- Per-module subdirectories with PNG screenshots

## Status

No screenshot captured for this module yet. Run `npm run manual:screenshots` after configuring credentials.
