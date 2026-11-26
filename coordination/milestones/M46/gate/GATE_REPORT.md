# M46 gate — Content & Digital Experience Hub (2026-11-26)

- **Scope:** M46.S01.T001–T008. Commits 031e223, fcd3970 and the gate commit.
- **Environment:**
  - a disposable `postgres:16-alpine` container, `m46-gate-pg` (127.0.0.1:25432);
  - synthetic POVU data only;
  - `PROVIDER_EGRESS=local`, no provider keys, no owner dev DB.

## 1. Migrations (`01_migrations.txt`)

- **Empty → head (`20261127_0076`):** PASS.
  - 16 of 16 M46 tables present.
  - `kb_articles.access_list_id` present.
- **0076 downgrade → 0 M46 tables, then upgrade:** PASS (16).
- **Gate fix:** after `cms_pages.live_path` was added, the round trip was repeated on the template DB. PASS.

## 2. Backend

- **DB-gated M46 tests:**
  - `test_m46_s01_content_hub.py`: 7 passed;
  - `test_m46_s01_t008_carryovers.py`: 4 passed;
  - reruns after the review fixes: `02_db_tests_m46_rerun.txt`.
- **Prior-feature regressions touched by M46** (`02_regressions_rerun.txt`), all PASS:
  - M36 customer timeline;
  - M36 knowledge base;
  - M44 web analytics (forget/consent);
  - M45 config bundles.
- **Full backend suite:** 1811 passed, 489 skipped, 0 failed (`02_backend_suite_rerun.txt`).

## 3. Frontend

- **tsc:** exit 0.
- **eslint:** 0 errors, 69 warnings.
  - The 2 new warnings are intentional `<img>` tags for arbitrary https content images (next/image needs a domain allow-list).
- **`next build`:** exit 0. The routes `/site/[key]/[locale]/[[...path]]`, `/site/[key]/[locale]/blog` and `/kb/members` were built.
- **i18n missing-key report** (`03_i18n_report.json`, `npm run test:i18n`): ok.
  - 314 keys × en/sw/tr across 18 customer files.
  - 0 missing, 0 unknown keys, 0 hard-coded formats.

## 4. Browser

See `05_browser_walkthrough.md`; screenshots `01`–`05`.
- Public site with SEO head and JSON-LD.
- Drafts not public.
- Members gate and video at phone width.
- Shop in Swahili and Turkish: 8 tabs each, 0 overflow, 0 missing keys.
- Staff author → approver workflow.
- One defect was fixed: the public-page list in the API client.

## 5. Independent review

See `06_independent_review.md`. Verdict: ACCEPT_WITH_FIXES.
- All high and medium findings are fixed with regression tests.
- The remaining low items go to M47.S01.T006.

## Result

**M46 gate: PASS.** Rows M46.S01.T001–T008 are marked [x].

Activation-only items remain in M47.S02:
- a custom domain, DNS and HTTPS for sites;
- a Google Search Console account;
- answer-engine visibility measurement;
- a real LLM provider budget for the content studio;
- CDN/object storage for media.

Bounded delta:
- Staff (dashboard) screens are still English.
- The i18n framework is in place for them, but T007 acceptance covered the customer-facing screens.
