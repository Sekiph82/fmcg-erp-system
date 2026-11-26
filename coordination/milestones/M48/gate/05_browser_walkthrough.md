# M48 gate — manual browser walkthrough (real local app, 2026-11-26)

## Setup

- **Code:** candidate 2efa030, the review fixes included.
- **Backend:** uvicorn :8048 on the disposable DB `m48_walk`, cloned from template `m48_tmpl` (head 0078).
- **Frontend:** `next dev` :3248.
- **Provider simulators** on :8765, mounted on one server (scratchpad `m48_sims.py`):
  - ads (`/ads`), social (`/social`), e-sign (`/esign`), card (`/card`) and warehouse (`/wh`);
  - `PROVIDER_EGRESS=local`, so nothing leaves the machine.
- **Personas:** synthetic and scoped, created by `m48_walk_seed.py`:
  - `walk-mkt`: marketing edit;
  - `walk-appr`: marketing approve only;
  - `walk-admin`: superuser with TOTP 2FA;
  - `walk-dw1` / `walk-dw2`: reports.admin;
  - `walk-rep`: sales, plus esign request;
  - `walk-esadmin`;
  - `walk-fin1` / `walk-fin2`: finance with 2FA;
  - `walk-outsider`.
- **Interaction:** every step below was performed by clicking and typing in the browser pane, not by API calls.

## 1. Ads — Meta campaign lifecycle (T001, plus review fixes 2/4 exercised in the UI)

| # | Persona | Action (click) | Observed result | Screenshot |
|---|---|---|---|---|
| 1 | walk-mkt | Ads reporting → add Meta account 1001 | "Account added", status ACTIVE | — |
| 2 | walk-mkt | Builder → fill wizard → Create paused draft | Refused: "You are not a member of this ad account." (cross-account guard) | 01_ads_nonmember_refused.jpg |
| 3 | walk-admin (2FA) | Daily cap 1000, monthly 25000, members walk-mkt/walk-appr → Save controls | "Controls saved." The account panel lists the reasons it stays SIMULATED. | 02_ads_admin_controls_saved.jpg |
| 4 | walk-mkt | Create with budget 500 | Refused by the guardrail ("above 50.0 … raise ADS_MAX_DAILY_BUDGET only with owner approval") | — |
| 5 | walk-mkt | Budget 40 → Create paused draft | The tree Campaign → Ad set → Creative → Ad appears in DRAFT, SIMULATED; every disabled button shows its reason | 03_ads_meta_tree_draft.jpg |
| 6 | walk-mkt | Validate | "Checked by the platform's validate-only call." | 04_ads_meta_validated.jpg |
| 7 | walk-mkt | Request approval | SUBMIT v1, hash 8c0f05fffabb, PENDING. The requester's own Approve is disabled ("Needs marketing.approve"). | — |
| 8 | walk-appr | Approve | APPROVED walk-mkt → walk-appr. The approver cannot submit ("Needs marketing.edit"). | 05_ads_approver_approved_no_submit_right.jpg |
| 9 | walk-mkt | Submit (paused) | The ledger shows 4 CREATE rows, SIMULATED, SUCCEEDED, provider ids 2381001–2381004. Read-back: campaign and ad set PAUSED, ad IN_PROCESS. Approval USED. | 06_ads_submitted_paused_ledger.jpg |
| 10 | — | Simulator `GET /ads/_control/objects` | Objects exist with status PAUSED and daily_budget 4000 minor units (40 KES). The name is UTF-8 correct (U+2013). | — |
| 11 | walk-mkt | Request resume approval, then edit budget 45 → Edit budget (new version) → Request budget approval | The RESUME v1 approval is automatically SUPERSEDED by budget v2; BUDGET v2 hash 5f5dc2f3381a is PENDING | 07_ads_budget_v2_resume_superseded.jpg |
| 12 | walk-appr | Approve BUDGET v2 | APPROVED | — |
| 13 | walk-mkt | Submit (budget push), then Request resume approval | "sent v2"; ledger row BUDGET SUCCEEDED; RESUME v2 PENDING | — |
| 14 | walk-appr | Approve RESUME v2 | APPROVED | — |
| 15 | walk-mkt | Resume | Campaign, ad set and ad ACTIVE (STATUS rows SUCCEEDED) | 08_ads_resumed_active.jpg |
| 16 | walk-mkt | Pause | Only the top campaign is PAUSED; ledger complete (4 CREATE, 1 BUDGET, 4 STATUS, each with 1 attempt) | 09_ads_paused_full_ledger.jpg |

## 2. Ads — Google, LinkedIn and TikTok (T002–T004)

| # | Persona | Action | Observed result | Screenshot |
|---|---|---|---|---|
| 1 | walk-mkt | Ads reporting → add Google 4445556666, LinkedIn 5001 (USD), TikTok 7000001 | All four accounts listed, ACTIVE | 11_ads_four_accounts.jpg |
| 2 | walk-admin | Set members and caps for each account; Activate live changes on TikTok | "Account activated (live still needs the global switches)". Still SIMULATED, with reasons: egress local, ADS_LIVE_MUTATIONS off | 10_ads_tiktok_activated_still_simulated.jpg |
| 3 | walk-mkt | Google wizard: 3 headlines, 2 descriptions → Create → Validate → Request approval | Budget → Search campaign → Ad group → RSA; "Checked by the platform's validate-only call"; PENDING | 12_ads_google_validated_pending.jpg |
| 4 | walk-mkt | LinkedIn wizard → Create → Validate → Request approval | Campaign group → Campaign → Creative; "Passed local checks (no platform validate-only)"; the Development-tier note is shown | 13_ads_linkedin_local_checks_pending.jpg |
| 5 | walk-mkt | TikTok wizard → Create → Validate → Request approval | Campaign → Ad group → Ad; PENDING | 14_ads_tiktok_pending.jpg |
| 6 | walk-appr | Approve all three | APPROVED | — |
| 7 | walk-mkt | Google Submit (paused) | 4 CREATE rows SUCCEEDED, with resource names customers/4445556666/…; campaign, ad group and ad PAUSED | 15_ads_google_submitted_paused.jpg |
| 8 | walk-mkt | LinkedIn Submit (Development tier, the default) | Refused: "campaign writes need Standard tier access". Nothing was created and the approval stays usable | 16_ads_linkedin_dev_tier_refused.jpg |
| 9 | walk-mkt | TikTok Submit | Provider simulator rejected campaign/create, 40002 (daily budget below the TikTok minimum). Shown as FAILED in the UI and ledger; nothing created. **Defect: local checks did not catch the minimum. Recorded as M48.S01.T020.** | 17_ads_tiktok_min_budget_rejected.jpg |
| 10 | walk-mkt | Backend restarted with `LINKEDIN_ADS_ACCESS_TIER=standard` (simulated Standard tier, labelled as such) → Submit again | Campaign group 1014 and campaign 1015 in DRAFT (STOPPED); creative urn:li:sponsoredCreative:1016; no duplicate | 18_ads_linkedin_standard_tier_created.jpg |

## 3. Social — TikTok organic publish state machine (T005)

| # | Persona | Action | Observed result | Screenshot |
|---|---|---|---|---|
| 1 | walk-mkt | Channels → add TikTok channel | "publishes by API" | — |
| 2 | walk-mkt | New post (video, verified-domain URL) → Save draft | Draft v1, SIMULATED, "TikTok options · not set (required)" | — |
| 3 | walk-mkt | Load creator options from TikTok | The unaudited app offers only "Only me (private)"; Stitch is locked off by the creator; save stays disabled until privacy and consent are given | 19_social_tiktok_creator_options_self_only.jpg |
| 4 | walk-mkt | Choose SELF_ONLY, tick consent → Save TikTok options → Request approval | pending v1, "consent by walk-mkt" | 20_social_tiktok_pending_approval.jpg |
| 5 | walk-mkt | Approve own post | Refused: "A second editor must approve." | — |
| 6 | walk-mkt2 (second synthetic editor) | Approve → Submit now | "Submitted — the network is processing; it is not live until confirmed." publish_id is shown as "a submission, not yet a live post" (PROCESSING_DOWNLOAD) | 21_social_tiktok_processing_not_live.jpg |
| 7 | walk-mkt2 | Refresh status (simulator configured with 2 processing polls) | Still "processing — not live yet" after the first refresh. Second refresh: "published (confirmed by the network)", PUBLISH_COMPLETE, with an honest note that there is no public post id (private post) | 22_social_tiktok_published_confirmed.jpg |

## 4. Warehouse — Snowflake writer (T007, plus review fix 5)

| # | Persona | Action | Observed result | Screenshot |
|---|---|---|---|---|
| 1 | walk-dw1 | Add target: SNOWFLAKE, account POVU-DEMO, ERP_LOADER, LOAD_WH/POVU_DW/ERP, simulator URL, synthetic simulator key | "Target added — register this public key fingerprint SHA256:…". Status configured; "credential set by walk-dw1"; "Sends to: http://127.0.0.1:8765/wh/snowflake". The key is write-only and encrypted. | — |
| 2 | walk-dw1 | Approve own target | Refused: "An independent administrator must approve: you created this target or set its credential." | — |
| 3 | walk-dw1 | Test connection | "Connection OK (simulated): role ERP_LOADER, warehouse LOAD_WH, database POVU_DW" (key-pair JWT checked by the simulator) | — |
| 4 | walk-dw1 | Add job customers → Dry run | Plan of SQL API v2 statements: schema and table IF NOT EXISTS, TRANSIENT staging, bound `?` inserts, BEGIN TRANSACTION/MERGE/COMMIT, drop staging. No data sent. | 23_dw_snowflake_dry_run_plan.jpg |
| 5 | walk-dw1 | Sync now | Runs: one scheduled run of 4 rows (SIMULATED), then a manual run of 0 rows. The watermark is idempotent; nothing was re-sent. | 24_dw_snowflake_sync_runs.jpg |
| 6 | walk-dw2 | Approve | "Target approved for live sync to … (still needs the owner's runtime switch)"; approved by walk-dw2, credential set by walk-dw1 | 25_dw_independent_approval.jpg |

## 5. Card payments — Pesapal (T010, plus review fixes 1/3)

| # | Persona | Action | Observed result | Screenshot |
|---|---|---|---|---|
| 1 | walk-fin1 (2FA) | Invoice → Payment links → Set up provider | **Gap found and fixed during the gate:** the UI had no API URL field, so a local simulator could not be configured from the browser (the backend already allowed it when egress is local). Added "API URL override (optional; local simulator only, never in live egress)" in PaymentLinks.tsx. | — |
| 2 | walk-fin1 | Sandbox + simulator key/secret + URL → Save (encrypted) → Register IPN URL | "Card payments (Pesapal): simulated · sandbox — card payments are test payments and never reach the ledger" | — |
| 3 | public payer (no login) | /pay/<token> → amount 2000 (partial) + e-mail → Pay by card | Page shows "Card: simulated"; the browser is redirected to the provider's hosted page (the simulator's synthetic host `pesapal-sim.test` is not browsable, so the payer's result is set through the simulator control `/_sim/pay`, delayed 1 poll) | 26_card_public_pay_page.jpg |
| 4 | walk-fin1 | Refresh status ×2 | First refresh: PENDING. Then: COMPLETED, 2000 KES, "test settled". Reconciliation shows no collection and no ledger entry (sandbox money is never booked), plus the credit note | 27_card_completed_test_settled.jpg |

## 6. E-signature — Adobe Acrobat Sign (T009, plus review fix 7)

| # | Persona | Action | Observed result | Screenshot |
|---|---|---|---|---|
| 1 | walk-esadmin | E-sign → DocuSign / Adobe Sign tab | Readiness: built-in signer "local evidence, not provider-certified"; DocuSign and Adobe "not ready", with missing fields listed | 28_esign_provider_readiness.jpg |
| 2 | walk-esadmin | Adobe: client id, simulator API base, client secret, refresh token → Save | "Adobe Acrobat Sign: ready (SIMULATED)"; secrets shown only as "(set)" | — |
| 3 | walk-rep | Quotes → Share → Signature via provider → Adobe, signer name and e-mail, 14 days → Send for signature | SENT (SIMULATED); snapshot SHA-256 shown; timeline CLAIMED "Ledger claim before the provider call" → SENT; the send button is now disabled ("Already out for signature") | 29_esign_adobe_sent_claim_timeline.jpg |
| 4 | simulator control | outcome complete, then tick | — | — |
| 5 | walk-rep | Refresh / reconcile | COMPLETED; signed and evidence SHA-256 hashes; "Simulated provider evidence — not certified"; "ERP: Quotation accepted from the signed simulated Adobe Acrobat Sign copy"; downloads for snapshot, signed document and evidence | 30_esign_completed_not_certified.jpg |

## 7. Review-fix and defect checks in the UI

| # | Persona | Action | Observed result | Screenshot |
|---|---|---|---|---|
| 1 | walk-mkt | TikTok wizard at 40 KES → Create (after the T020 fix) | Refused before approval: "Daily budget 40 KES is below the minimum. TikTok minimum campaign daily budget: 50 (TikTok documents USD 50; applied as 50 KES because the local-currency minimum is not verified here)". The wizard shows the minimum and the global guardrail; the default budget is 50. | 31_ads_tiktok_min_budget_refused_before_approval.jpg |
| 2 | walk-outsider (marketing.view) | Open the campaign builder | Read only: Create paused draft and Save controls are disabled; "Admins only." | 32_ads_viewer_read_only.jpg |

## Not clicked through in the browser (covered by DB tests; see the gate report)

- **T006** brand-context draft preview: the walk DB has no prospect rows. Covered by test_m48_s01_t006 (6 passed).
- **T018** inventory transfer idempotency form and **T013/T014** scan flows: the walk DB has no stock. Covered by DB tests (9 passed).
- **T008** BigQuery wizard: the same writer pattern as Snowflake. Covered by test_m48_s01_t008 (DB).
- **Social** FAILED and cancel paths: covered by test_m48_s01_t005 (11 passed).

## 8. Mobile (375×812 browser viewport; not a physical device) and locales

| # | Page | Observed result | Screenshot |
|---|---|---|---|
| 1 | /pay/<token>?lang=sw | Layout fits, no horizontal scroll, Swahili labels. **Defect found:** the card mode was shown as raw English "simulated". **Fixed:** it is now mapped to the localized provider labels. | 33_mobile_pay_sw_before_fix.jpg |
| 2 | /pay/<token>?lang=tr after the fix | "Kart: simülasyon (gerçek para yok)"; "Kartla öde" | 35_mobile_pay_tr_after_fix.jpg |
| 3 | /dashboard/marketing/ads/campaigns (walk-outsider) | scrollWidth 375 = viewport 375, so no horizontal overflow; the SIMULATED reasons wrap | 34_mobile_ads_builder.jpg |

Staff page bodies remain English by design; full EN/SW/TR coverage of staff pages is M51.S01.T008.
