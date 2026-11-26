# M49 gate: CRM, Advertising & Social Marketing Excellence (2026-11-26)

## Candidate and environment
- **Final candidate:** `64dfe6a`. The full DB run was on `5dde89d`. The re-review fixes in `64dfe6a` (N1–N3: `audience_sync_service`, `crm_outbound_service`, `crm_automation_service`, `approval_inbox_service`) were then re-verified by rerunning every DB file that touches them (see §2).
- **Database:** disposable `postgres:16-alpine` (`m49-gate-pg`, 127.0.0.1:25432). Template `m49_tmpl` is built empty → head 20261129_0079 plus a minimal synthetic POVU seed. The owner's dev DB was never used.
- **Services:** local Mailpit, Mosquitto, ClamAV and Redis containers.
- **Providers:** simulators only, with `PROVIDER_EGRESS=local`.

## 1. Migrations (`01_migrations.txt`)
- **Empty → head:** reaches 0079.
- **Populated (seeded) database, 0079 → 0078 → head:**
  - Evidence tables are archived as `*_archived_0079` and their rows are kept.
  - The new columns are dropped on downgrade and re-added on upgrade (11/11).
  - Seed rows are kept.
- **On the final code:** two downgrade/upgrade rounds on the same database, giving 16 and then 32 archives. The rows are kept and `social_items_reply_archived_0079` is created.
  - The repeated-downgrade index-name collision in the shared `downgrade_archive` was fixed during the gate.

## 2. Backend
- **Full DB-gated inventory** (`02_db_tests_full.txt`, `02_db_tests_full_report.md`): 246 files, each on its own fresh DB, with services. **245 PASS.**
  - The 1 FAIL was `test_m17_s02_t005_mqtt_db`. Cause: the Git-Bash path conversion broke the Mosquitto container's config path, so no broker was running. This is environmental. After restarting the broker with `MSYS_NO_PATHCONV=1` it **PASSES**.
- **Final-candidate rerun** (`02_db_tests_rerun_final_64dfe6a.md`): **24/24 PASS** on `64dfe6a`. Covered:
  - mqtt;
  - all `test_m49_*` files (t001–t013);
  - consent, outbound, audience, approval, automation, dedupe, mailbox and unsubscribe files.
- **No-DB suite** (`02_backend_suite_nodb.txt`, `64dfe6a`): **1915 passed, 0 failed**, 725 skipped. The skips are DB/service flags covered by the DB runner.
  - The no-DB run during the gate found that the public Twilio webhook was not on the PUBLIC_ROUTES split (`test_route_auth_coverage`), and that a legacy fake DB needed adapting for the shared-mailbox check. Both are fixed.

## 3. Frontend (`03_frontend.txt`)
- tsc exit 0.
- eslint: 0 errors.
- i18n report ok.
- `next build` exit 0. The build directory `.next-m49gate` was deleted afterwards.

## 4. Manual browser walkthrough (`05_browser_walkthrough.md`, 9 screenshots)
The walkthrough clicked through the real local app:
- **Marketing Studio:** campaign → brief → over-cap budget → finance 2FA approval in My Approvals → mobile check.
- **Recurring meeting:** across the London DST change; local time is kept.
- **Contact center panel,** plus a signed Twilio webhook.
- **Social:** Facebook multi-photo post, second-editor approval, simulated publish.
- **Studio** pickup of that post by campaign tag.

Five defects (A–E) were found and fixed in T014. Areas not clicked through are listed honestly; they are covered by DB tests and carried to M52, the exhaustive persona acceptance.

## 5. Independent review (Opus reviewer, read-only)
- **Review of `cf26b58`:** ACCEPT_WITH_FIXES, 12 findings: F1 high, F2 medium/high, F3–F6 medium, F7–F12 low. All were fixed in T013 (`5dde89d`).
- **Re-review of the fix diff:**
  - F2–F12 CLOSED; F1 partly closed;
  - new findings: N1 medium, N2 low/medium, N3 low.
  - All fixed in `64dfe6a`, with regression tests: t013 26 passed.
  - N1 root cause: a `once=True` SQLAlchemy listener cannot be re-added for the same function. It is now a persistent per-session listener with a per-commit flag, plus a periodic retry in the CRM automation tick.

## 6. Tasks
- M49.S01.T001–T012 are implemented and evidence-backed.
- T013 covers the review fixes; T014 covers the walkthrough defects.

## 7. Quality
No category scores are assigned at M49. The scoring needs the M52 full inventory and persona acceptance, per `QUALITY_RUBRIC.md`. No score is claimed.

## 8. Remaining, honestly
- **Activation only, owner actions:**
  - real Twilio, OpenAI transcription, Google/Microsoft calendar and mail, Meta, LinkedIn, YouTube, X, TikTok and ad-platform accounts;
  - Google Customer Match ToS acceptance;
  - TikTok guardrail;
  - confirm YouTube project verification status. Private-only stays the default.
- **Not built:** drag-and-drop template improvements in Studio. The existing designer is reused.
- **Known limits:**
  - `mkt_campaigns` has no `company_id`, so Studio analytics filter by company only.
  - Meta ad-set read-back compares the date only.
  - Anyone can create a callback, and the callback list is filtered after `limit(200)`.
  - Live removal of pending audience members retries on the CRM automation tick or Reconcile.

## Result
**M49 gate: PASS.**
