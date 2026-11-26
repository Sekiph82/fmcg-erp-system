# M47 final software gate — parity-plus integrated acceptance (2026-11-26)

**Scope:**
- M47.S01.T001–T011:
  - re-audit;
  - integrated FMCG flow;
  - surface/security audit;
  - final comparison report;
  - carry-overs;
  - the T007–T011 depth tasks from the v3 re-audit.
- Regression of every M43–M46 DB-gated test file.

**Code:**
- Commits 0a0cfa2 → 3077323 → ee79b2d, plus the gate commit.

**Environment:**
- Disposable `postgres:16-alpine` (`m46-gate-pg`, 127.0.0.1:25432) with a head template at migration `20261127_0077`.
- Local provider simulators (Slack, ad lists, calendars, M-Pesa monkeypatch).
- `PROVIDER_EGRESS=local`, no provider keys, synthetic POVU data only.
- The owner's dev DB was not used.

## 1. Migrations (`01_migrations.txt`)

- **Empty → head 0077:** PASS. 20 of 20 new M47 tables, the cms_media columns and all M46 tables are present.
- **0077 downgrade → upgrade:** PASS.
  - 0 M47 tables after the downgrade; 20 again after the upgrade.
  - The gate added `web_identities.verified_at` and the Slack route webhook column type. The round trip was re-run on the template after each change.

## 2. Backend

- **First full DB run** (`02_db_tests.txt`): 50 of 54 files passed.
  - All 4 failures were the in-progress review fix: a new column was not yet in the migration.
- **After the review fixes** (`02_db_tests_rerun.txt`): 55 of 55 files PASS.
- **Final run on the gate code** (`02_db_tests_final.txt`): 54 of 55 files passed.
  - The one failure (`test_m46_s01_content_hub`) was a flaky assertion: it searched the whole response for the bare substring "42", and random page/site ids sometimes contain it. The rows themselves were empty, so nothing leaked.
  - The assertion now looks for the quoted value. Three consecutive runs on fresh DBs: 7 passed each time (`02_content_hub_flake_reruns.txt`).
- **Full backend suite, final gate code:** 1841 passed, 537 skipped, 0 failed (`02_backend_suite_final.txt`).
- **Integrated FMCG scenario** (`tests/test_m47_s01_t002_integrated_flow.py`), with every step asserted:
  - lead and deal: web lead → scoring/routing → sequence → quote with discount approval and CPQ level → e-sign → SO;
  - production and delivery: production, QC, lot release → pick, dispatch, POD;
  - money: invoice with GL → M-Pesa payment link → AR cleared;
  - side channels: loyalty/NPS, portal and field orders, SAFETY complaint → recall → trace;
  - attribution and a rule-based copilot.

## 3. Frontend

- **tsc:** exit 0.
- **eslint:** 0 errors. Warnings are pre-existing, plus 2 intentional `<img>` tags for arbitrary https content.
- **`next build`:** exit 0.
- **i18n missing-key report:** ok. 24 files checked; the common, portal, public, docs and staff catalogs are complete in EN/SW/TR.

## 4. Browser

See `05_browser_walkthrough.md`.
- Staff login and dashboard in Swahili.
- Report datasets.
- Helpdesk pipelines.
- CRM platform settings.
- All M47 API calls answered 200.
- The M46 walkthrough (public site, members, video at 375 px, shop SW/TR) is in `../M46/gate/`.

## 5. Security

**Surface audit:** M47.S01.T003, `../T003/T003_AUDIT.md`. 16 defects fixed with tests.

**Independent final review** (`06_independent_review.md`):
- Verdict ACCEPT_WITH_FIXES.
- All high, medium and low findings were fixed with regression tests. That covers findings 1–8 and 12–15, and also:
  - 9: DMARC trusts only our Authentication-Results;
  - 10: 2FA attempt counter row lock;
  - 11: Slack route webhooks encrypted at rest;
  - 14: workflow enqueue pages through all records;
  - 16: public video rate limit.
  - Tests: `test_m47_s01_t005_review_fixes.py` and `test_m47_s01_t005_followups.py`.
- **Bounded:**
  - Website visitors can verify their e-mail link only by signing in to the portal; the e-mailed one-time link is not built.
  - Unverified visitors get no form shortening, which is the safe default.

## Result

**M47 final software gate: PASS.** Rows M47.S01.T001–T011 are marked [x].

Remaining items are commissioning only, M47.S02.T001–T010 (NOT_DUE):
- domain/HTTPS;
- mailboxes/OAuth;
- voice;
- ad and social accounts;
- online store;
- payments/eTIMS/signature;
- real master data;
- licensed data and AI endpoints;
- commissioning UAT/performance/restore drill;
- library installs (SAML, Parquet, OCR).
