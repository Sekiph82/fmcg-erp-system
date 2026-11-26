# M45 gate — AI Agent & Customer Data Hub (2026-11-26)

- **Scope:** M45.S01.T001–T024. Commits cf1468b..a6408e4, plus the gate fixes in this commit.
- **Gate environment:**
  - A disposable `postgres:16-alpine` container, `m45-gate-pg`, on 127.0.0.1:25432.
  - A local S3-compatible simulator (`tests/provider_sim/s3_app.py`) and a local OIDC provider (`tests/provider_sim/oidc_app.py`).
  - Synthetic POVU data only.
- **Not used:** the owner's dev DB, and any provider key. `PROVIDER_EGRESS=local`.

## 1. Migrations (`01_migrations.txt`)

| Check | Result |
|---|---|
| Empty → head (`20261126_0075`) | PASS |
| 0075 → downgrade to 0074 | PASS: M45 tables and columns removed |
| 0074 → upgrade to head again | PASS: 48 of 48 declared tables and 3 of 3 added columns present |

Notes:
- 0075 builds its tables from the ORM definitions (checkfirst), so the models and the migration cannot drift apart.
- The enum value `SALES_DOCUMENT` stays on downgrade, because PostgreSQL cannot drop enum values.

## 2. Backend

- **DB-gated tests, M43 + M44 + M45:** 42 of 42 files PASS (`02_db_tests.txt`).
- **After the review fixes:**
  - every M45 file passes, together with the M44 messaging regression (`02_db_tests_rerun.txt`, `02_db_tests_rerun2.txt`);
  - the M36 live-chat regression passes (`02_m36_chat_regression.txt`).
- **Full backend suite:** 1807 passed, 482 skipped, 0 failed (`02_backend_suite_rerun.txt`). The skips are DB- or provider-gated tests of other milestones.
- **Two-database tests:** the config bundle round trip (T018) and the warehouse export to a second PostgreSQL (T020) run on a second disposable database, created by the runner.

## 3. Frontend

- tsc: exit 0 (`03_tsc.txt`, `03_tsc_rerun.txt`).
- eslint: 0 errors. There are 67 warnings, all pre-existing. The two intentional full-page reloads on identity change are documented.
- `next build`: exit 0 (`04_build.txt`, `04_build_rerun.txt`).

## 4. Browser

See `05_browser_walkthrough.md`; screenshots 01–07 are in `screenshots/`. One routing defect was found and fixed in the gate.

## 5. Independent review

See `06_independent_review.md`. Verdict: ACCEPT_WITH_FIXES.
- All medium findings are fixed with regression tests.
- Low items 13 (pending-attempt timeout) and 15 (per-step daily ledger) go to M46.

## Result

**M45 gate: PASS.** Rows M45.S01.T001–T024 are marked [x].

Activation-only items remain in M47:
- real LLM provider use for agents;
- enrichment and intent data providers;
- Outlook and Gmail host publishing and admin consent;
- a real OIDC IdP, plus SAML once a maintained library is available;
- Daraja credentials and a card provider;
- DocuSign or Adobe Sign;
- Snowflake and BigQuery;
- a real S3 or MinIO bucket;
- an OCR engine.
