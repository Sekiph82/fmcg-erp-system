# M48 gate: Critical Software Completion and Evidence Reconciliation (2026-11-26)

## Candidate and environment

- **Candidate:** backend frozen at `a79d27b`. The gate commit adds only the T025 frontend localisation fix and one legacy test adaptation, both verified below.
- **Database:** disposable `postgres:16-alpine` (`m48-gate-pg`, 127.0.0.1:25432). Template `m48_tmpl` is built empty → head 20261128_0078, plus a minimal synthetic POVU seed (`make_template.sh`).
- **Test services:** local Mailpit, Mosquitto and ClamAV containers.
- **Providers:** provider simulators only, with `PROVIDER_EGRESS=local`. The owner's dev DB was never used.

## 1. Migrations (`01_migrations.txt`)

- **Fresh database:** empty → 0078; all 10 core M48 tables are present.
- **0078 downgrade and re-upgrade:** both work.
  - Evidence tables (card payments and refunds, e-sign envelopes and webhook events, ad mutations and approvals, send approvals, mail webhook tokens) are archived as `*_archived_0078` with their rows kept, never dropped.
- **Older downgrades:**
  - A populated database (0078 → 0077 → head) keeps its rows and gains all 5 new columns.
  - Legacy downgrade to 20261029_0038 → head works; this was the T016 fix to 0043.
  - Evidence-table downgrades 0041–0055 archive instead of dropping (T023 F3); checked by downgrading to 0040 and upgrading back.

## 2. Backend

- **Full DB-gated inventory, every file on its own fresh DB** (`02_db_tests_final.txt`, `run_all_db_tests.py`): 233 files, 232 PASS on the first run.
  - The one failure, `test_m47_s01_t002_integrated_flow`, assumed form consent becomes SUBSCRIBED at once. The intended T022 double opt-in made it PENDING. The test now opens and confirms the e-mailed link → PASS (5 passed, db_results_20261126_150318). **Final result: 233/233.**
  - The run includes the services Mailpit (SMTP), MQTT and ClamAV, so there are no SERVICE_REQUIRED skips. The legacy-prep files (M25.S02.T003/T004, M31.S02.T002) ran too.
- **Earlier full runs:**
  - `02_db_tests_run1_moving_code.txt`: 224/229, run while fixes were landing.
  - `02_db_tests_run2_partial_105of229_superseded.txt`: stopped when a schema change landed.
  - Every failure in them was diagnosed and fixed: stale legacy tests m36_s03_t001 and m41_s01, the T021 approval defect, a ClamAV env format error, and code that was changing during the run.
- **Full no-DB suite:** 1893 passed, 606 skipped, 0 failed. Every skip is a DB_FLAG skip covered by the DB runner; see `SKIP_INVENTORY.md`.

## 3. Frontend

- tsc exit 0.
- eslint 0 errors (69 pre-existing warnings).
- i18n missing-key report ok.
- `next build` exit 0.

## 4. Manual browser walkthrough

See `05_browser_walkthrough.md`: 38 screenshots under `screenshots/` and per-step click logs.

**Real local app:** :3248 frontend, :8048 backend and :8765 simulators, with separate synthetic personas. Flows covered:
- **Ads:** Meta full lifecycle (draft → validate → approve → submit paused → budget v2 → resume → pause), plus Google, LinkedIn (Development-tier refusal, then simulated Standard) and TikTok.
- **Social:** TikTok organic publishing — creator options, consent, two-editor approval, PROCESSING → PUBLISHED only on PUBLISH_COMPLETE.
- **Warehouse:** Snowflake writer — wizard, independent approval, dry run, sync, idempotent watermark.
- **Card payments:** Pesapal sandbox — setup, public pay page, partial payment, test settlement never booked.
- **E-signature:** Adobe Sign — readiness, send, COMPLETED, labelled "not certified".
- **Access:** viewer is read-only.
- **Viewport and locales:** mobile 375 px, EN/SW/TR on public pages.

**Defects found during the walkthrough and fixed:**
- T020: provider minimum budgets.
- Card setup UI lacked a simulator URL field.
- The pay-page card label was not localized.
- T025: consent-confirm and unsubscribe pages were English-only.

## 5. Independent reviews (`06_independent_review.md`, T015 reports)

1. **Review of candidate 933ffaf:** ACCEPT_WITH_FIXES, 8 findings (2 high), all fixed.
2. **Re-review of the fixes:** all 8 CLOSED; 2 new findings and 1 note, all fixed.
3. **Independent M36 CRM security, privacy and migration audit:** ACCEPT_WITH_FIXES, 11 findings, fixed in T022/T023.
4. **Independent M38 persona review:** ACCEPT_WITH_FIXES; gaps fixed in T024; stub count corrected.

## 6. Task results

- M48.S00.T001–T002 and M48.S01.T001–T025 are evidence-backed.
  - Defects found by the gate's own checks became tasks T013–T025 (excluding T015) and are fixed with regression tests.
- **T011** ([v] reconciliation, `V_RECONCILIATION.md`):
  - The 93 historical [v] rows marked NEEDS_M48_GATE_RETEST are covered by the full 233-file DB regression above (all PASS).
  - The 5 remediation rows were closed by T013/T014/T015.
  - Rows needing a real account stay [D].

## 7. Quality rubric

Category scores are not assigned at M48. `QUALITY_RUBRIC.md` defines the criteria, and scoring needs the full feature inventory delivered by M49–M52. No score is claimed.

## 8. Remaining, honestly

- **Activation only:** real ad, social, e-sign, payment and warehouse accounts. The owner must raise the TikTok guardrail (default 50) before real TikTok use.
- **Carried forward:**
  - CBK rate fetch outside the egress guard → M52.S01.T004.
  - Per-van checks on van admin, report and AI routes → M52.S01.T006.
  - Email-designer single-send UI not clicked through (needs a published design) → M52 persona walkthrough.
  - Frozen historic forward DDL for 0041–0055 is not rewritten; downgrades archive instead.

## Result

**M48 gate: PASS.**
