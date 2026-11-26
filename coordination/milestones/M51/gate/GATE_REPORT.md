# M51 gate: Digital Experience Pro and full localization (2026-11-27)

## Candidate and environment
- **Final candidate:** `a142ca2`.
  - The full DB run and the no-DB suite ran on `787c968`. Its backend and `frontend/src` trees are identical to `a142ca2` (`git diff --stat 787c968 a142ca2 -- backend frontend/src` is empty). `a142ca2` only drops an accidentally committed build directory (`frontend/.next-m49walk`, now in `.gitignore`).
  - Migrations ran on `f448098`. `backend/alembic` and `backend/app/models` are unchanged from there to `a142ca2`.
- **Database:** disposable `postgres:16-alpine` (`m49-gate-pg`), template `m51_tmpl` (empty → head 20261201_0081 plus a synthetic POVU seed). The owner's dev DB was never used.
- **Services:** local Mailpit, Mosquitto, ClamAV and Redis, all removed after the gate.
- **Providers:** simulators only (`PROVIDER_EGRESS=local`). No paid or live provider call.

## 1. Migrations (`01_migrations.txt`)
- Empty → 0081 creates 22 tables.
- A seeded copy with evidence rows went 0081 → 0080 → head twice: 13 archives, then 26. The evidence row was kept in the archive, and the seed rows were kept.

## 2. Backend
- **Full DB-gated inventory** (`02_db_tests_full.txt`, `02_db_tests_full_report.md`): **269/269 files PASS**. Each file ran on its own fresh DB with the services.
  - One skip, `test_m51_s01_t010_storage` S3 case: it needs a local MinIO. It ran and passed against MinIO during T010; that container was removed afterwards.
- **Superseded run** (`02_db_tests_run1_superseded_code_changed.txt`): the first full run was stopped because code changed during the run. It is kept for transparency and was replaced by the run above.
- **No-DB suite** (`02_backend_suite_nodb.txt`): **2069 passed, 0 failed**, 818 skipped. The skips are DB/service flags, covered by the DB run.
  - Two legacy source-text tests were adapted for `tx()`-wrapped navigation labels: gap021 and m48_t006.

## 3. Frontend (`03_frontend.txt`)
- tsc exit 0.
- eslint 0 errors.
- i18n report ok.
- Option-value scanner `[]`.
- `test:i18n`: 5 pass, 0 fail.
- `next build` exit 0. The build directory was deleted.

## 4. Manual browser walkthrough (`05_browser_walkthrough.md`, 6 screenshots)
- Checked: SW CRM, TR SEO & AEO on desktop and mobile, TR media studio, TR login.
- Option values: the select posts English values while the label is Turkish.
- **Defect found and fixed:** CRM pipeline stuck on the loading screen (a bug that predates M51).
- The first TR pass showed untranslated labels. A coverage pass added 1,117 strings: sentence-level and module-level literals are now 0 untranslated.

## 5. Independent review (Opus reviewer, read-only)
- **Review of `3c6b4b6`:** ACCEPT_WITH_FIXES. S1–S4, I1 and C1–C5 were fixed in `31a5074` (T011; `test_m51_s01_t011_review_fixes` 25 passed).
- **Re-review:** four findings, all fixed in `a142ca2`:
  - N1: CMS detach must unpublish;
  - S1: crawler IP validation, IPv6 brackets, WebRTC policy, Playwright only;
  - C1: `put_part` row lock and 409;
  - C2: private-endpoint plain-http guard.
- **Verification of `a142ca2`:** **ACCEPT**. All four CLOSED, with file:line evidence; no new defect of Medium or higher.
- **Low notes from that verification, carried to M52.S01.T004:**
  - an unreachable `raise` in local-mode `check_egress`;
  - `PinnedBackend` matches the allowed host by name only, not by port;
  - `private_only` allows link-local addresses, so it should also refuse 169.254/16 and fe80::/10;
  - the orphaned poster file after a revoke should be deleted.

## 6. Quality
No category scores are assigned. Scoring happens in M52 per `QUALITY_RUBRIC.md`.

## 7. Remaining, honestly
- **Activation only:**
  - a Google Search Console OAuth client and a verified property;
  - CrUX and OpenAI/Stability keys plus a budget (`M51_IMAGE_LIVE_ENABLED`);
  - a real S3 bucket;
  - a real AEO LLM provider;
  - the optional piper voice files.
- **Known limits:**
  - About 379 single-word labels, 140 option labels without a value and 53 skip-list strings are still English. Dynamic backend text and exports/PDFs are not localized. All of this is carried to M52.
  - The SW/TR catalogs are machine-assisted; a native-speaker review is recommended before commissioning.
  - Multipart parts for one upload session go up one at a time, because of the C1 lock.
  - Lab vitals need Playwright installed; without it they show UNAVAILABLE.

## Result
**M51 gate: PASS.**
