# M44 gate — Advanced Marketing Hub (2026-11-26)

Scope: M44.S01.T001–T014 (commits 97ca9fa..46fd7f2, plus the gate fixes in this commit).

The gate ran on:
- a disposable `postgres:16-alpine` container, `m44-gate-pg`, on 127.0.0.1:25432 with trust auth;
- synthetic POVU data only.

The owner's dev DB (localhost:5432) was not used. No provider keys were set and `PROVIDER_EGRESS=local`.

## 1. Migrations

| Check | Result |
|---|---|
| Empty → head (`20261125_0074`) | PASS |
| `0074` → downgrade to `0073` | PASS: the 6 sampled M44 tables are gone |
| `0073` → upgrade to head again | PASS: 16 of 16 M44 tables created by the migration SQL; campaign columns present |

Notes on the migration:
- 0074 has no data backfill.
- The reviewer checked that the SQL in 0074 matches the ORM models: column names and types, nullability, and the unique-constraint names used by `ON CONFLICT`.

## 2. Backend tests

- **DB-gated tests:** M43 + M44, 24 files, each on its own copy of the head template (`run_m44_db_tests.sh`). Result: **24/24 files PASS** (`02_db_tests.txt`).
- **Re-runs after the review fixes:**
  - all 9 M44 files: 9/9 PASS (`02_db_tests_rerun.txt`);
  - the 5 touched files, including M43 teams/views: 5/5 PASS (`02_db_tests_rerun2.txt`).
- **Skips removed:** two `test_m44_s01_t012_governance_db.py` tests used to skip when the template had no customer segment. They now create their own segment and run.
- **Full backend suite:** 1786 passed, 457 skipped, 0 failed (`02_backend_suite.txt`). The skips are other milestones' DB-gated or provider-gated tests.

## 3. Frontend

- tsc: exit 0 (`03_tsc.txt`, `03_tsc_rerun.txt`).
- eslint: 0 errors. There are 67 warnings, all pre-existing (none in M44 files) (`03_eslint.txt`).
- `next build`: exit 0 (`04_build.txt`, and `04_build_rerun.txt` after the fixes).

## 4. Browser walkthrough

See `05_browser_walkthrough.md`; screenshots are in `screenshots/`.

## 5. Independent review

See `06_independent_review.md`. Verdict: ACCEPT_WITH_FIXES. Every high and medium finding is fixed and has a regression test.

## Result

**M44 gate: PASS.** Rows M44.S01.T001–T014 are marked [x].

Activation-only items remain in M47. These are the real Meta, Google Ads, LinkedIn and TikTok apps, their reviews and tokens, the Slack workspace, the mail relay signing keys, and `SOCIAL_PUBLISHING_ENABLED`.
